# -*- coding: utf-8 -*-

"""
***************************************************************************
    connectdialog.py
    ---------------------
    Date                 : February 2016
    Copyright            : (C) 2016 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""


__author__ = 'Alexander Bruy'
__date__ = 'February 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import base64

from qgis.utils import iface

from boundlessconnect import connect
from boundlessconnect.connect import ConnectContent
from boundlessconnect.gui.executor import execute
from requests.exceptions import RequestException

from PyQt4 import uic, QtWebKit, QtCore
from PyQt4.QtCore import QUrl, QSettings, Qt
from PyQt4.QtGui import (QIcon,
                         QDesktopServices,
                         QDialogButtonBox,
                         QMessageBox)
from PyQt4.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkAccessManager,\
    QNetworkProxyFactory, QNetworkProxy

from qgis.core import QgsAuthManager, QgsAuthMethodConfig

from pyplugin_installer.installer_data import reposGroup

from boundlessconnect import utils
from boundlessconnect.plugins import boundlessRepoName, authEndpointUrl

pluginPath = os.path.split(os.path.dirname(__file__))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'connectdockwidget.ui'))

HELP_URL = "https://connect.boundlessgeo.com/docs/desktop/plugins/connect/usage.html#first-run-wizard"

class ConnectDockWidget(BASE, WIDGET):

    def __init__(self, parent=None):
        super(ConnectDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(QIcon(os.path.join(pluginPath, 'icons', 'connect.svg')))
        self.svgLogo.load(os.path.join(pluginPath, 'icons', 'connect-logo.svg'))

        btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
        btnOk.setText(self.tr('Login'))

        self.buttonBox.helpRequested.connect(self.showHelp)
        self.buttonBox.accepted.connect(self.logIn)
        self.btnSearch.clicked.connect(self.search)
        self.btnSignOut.clicked.connect(self.showLogin)
        self.searchWidget.setVisible(False)

        self.labelLevel.linkActivated.connect(self.showLogin)

        self.webView.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateAllLinks)
        self.webView.settings().setUserStyleSheetUrl(QtCore.QUrl("file://" +
            os.path.join(os.path.dirname(__file__), "search.css").replace("\\", "/")))
        self.webView.linkClicked.connect(self.linkClicked)

        self.showLogin()

        settings = QSettings()
        settings.beginGroup(reposGroup)
        self.authId = settings.value(boundlessRepoName + '/authcfg', '', unicode)
        settings.endGroup()

        if self.authId != '':
            authConfig = QgsAuthMethodConfig()
            QgsAuthManager.instance().loadAuthenticationConfig(self.authId, authConfig, True)
            username = authConfig.config('username')
            password = authConfig.config('password')
            self.leLogin.setText(username)
            self.lePassword.setText(password)

    def showLogin(self):
        self.authWidget.setVisible(True)
        self.searchWidget.setVisible(False)
        self.webView.setHtml("")
        self.leSearch.setText("")
        self.webView.setVisible(False)
        self.leLogin.setText("")
        self.lePassword.setText("")

    def showHelp(self):
        if not QDesktopServices.openUrl(QUrl(HELP_URL)):
            QMessageBox.warning(self, self.tr('Error'), self.tr('Can not open help URL in browser'))

    def linkClicked(self, url):
        name = url.toString()
        content = self.searchResults[name]
        if content.canInstall(self.level):
            execute(content.open)
        else:
            pass
            #TODO

    def logIn(self):
        utils.addBoundlessRepository()
        if self.leLogin.text() == '' or self.lePassword.text() == '':
            execute(connect.loadPlugins)
            self.authWidget.setVisible(False)
            self.searchWidget.setVisible(True)
            self.labelLevel.setText("Subscription Level: <b>Open</b>")
            self.level = ["open"]
            return

        self.request = QNetworkRequest(QUrl(authEndpointUrl))
        httpAuth = base64.encodestring('{}:{}'.format(self.leLogin.text(), self.lePassword.text()))[:-1]
        self.request.setRawHeader('Authorization', 'Basic {}'.format(httpAuth))
        self.manager = QNetworkAccessManager()
        self.setProxy()
        self.reply = self.manager.get(self.request)
        self.reply.finished.connect(self.requestFinished)

    def search(self):
        text = self.leSearch.text().strip()
        if text:
            try:
                results = execute(lambda: connect.search(text))
                if results:
                    self.searchResults = {r.url:r for r in results}
                    html = "<ul>"
                    for r in results:
                        html += "<li>%s</li>" % r.asHtmlEntry(self.level)
                    html += "</ul>"
                    self.webView.setHtml(html)
                    self.webView.setVisible(True)
            except RequestException, e:
                    QMessageBox.warning(self, "Search",
                        u"There has been a problem performing the search:\n" + unicode(e.args[0]),
                        QMessageBox.Ok)

    def requestFinished(self):
        reply = self.sender()
        if reply.error() != QNetworkReply.NoError:
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 401:
                msg = self.tr('Your credentials seem invalid. Do you want '
                              'to save them anyway?')
            else:
                msg = self.tr('An error occured when validating your '
                              'credentials. Server responded:\n{}.\n'
                              'Do you want to save them anyway?'.format(reply.errorString()))
            ret = QMessageBox.warning(self, self.tr('Error!'), msg,
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
            if ret == QMessageBox.Yes:
                self.saveOrUpdateAuthId()
            self.level = ["open"]
        else:
            self.level = connect.getUserRoles(self.authid)
            self.saveOrUpdateAuthId()

        execute(connect.loadPlugins)
        self.authWidget.setVisible(False)
        self.searchWidget.setVisible(True)
        self.labelLevel.setText("Subscription Level: <b>%s</b>" % connect.LEVELS[connect._LEVELS.index(self.level[0])])

    def saveOrUpdateAuthId(self):
        if self.authId == '':
            authConfig = QgsAuthMethodConfig('Basic')
            self.authId = QgsAuthManager.instance().uniqueConfigId()
            authConfig.setId(self.authId)
            authConfig.setConfig('username', self.leLogin.text())
            authConfig.setConfig('password', self.lePassword.text())
            authConfig.setName('Boundless Connect Portal')

            settings = QSettings('Boundless', 'BoundlessConnect')
            authConfig.setUri(settings.value('repoUrl', '', unicode))

            if QgsAuthManager.instance().storeAuthenticationConfig(authConfig):
                utils.setRepositoryAuth(self.authId)
            else:
                QMessageBox.information(self, self.tr('Error!'), self.tr('Unable to save credentials'))
        else:
            authConfig = QgsAuthMethodConfig()
            QgsAuthManager.instance().loadAuthenticationConfig(self.authId, authConfig, True)
            authConfig.setConfig('username', self.leLogin.text())
            authConfig.setConfig('password', self.lePassword.text())
            QgsAuthManager.instance().updateAuthenticationConfig(authConfig)

    def setProxy(self):
        proxy = None
        settings = QSettings()
        if settings.value('proxy/proxyEnabled', False):
            proxyHost = settings.value('proxy/proxyHost', '')
            try:
                proxyPort = int(settings.value('proxy/proxyPort', '0'))
            except:
                proxyPort = 0
            proxyUser = settings.value('proxy/proxyUser', '')
            proxyPassword = settings.value('proxy/proxyPassword', '')
            proxyTypeString = settings.value('proxy/proxyType', '')

            if proxyTypeString == 'DefaultProxy':
                QNetworkProxyFactory.setUseSystemConfiguration(True)
                proxies = QNetworkProxyFactory.systemProxyForQuery()
                if len(proxies) > 0:
                    proxy = proxies[0]
            else:
                proxyType = QNetworkProxy.DefaultProxy
                if proxyTypeString == 'Socks5Proxy':
                    proxyType = QNetworkProxy.Socks5Proxy
                elif proxyTypeString == 'HttpProxy':
                    proxyType = QNetworkProxy.HttpProxy
                elif proxyTypeString == 'HttpCachingProxy':
                    proxyType = QNetworkProxy.HttpCachingProxy
                elif proxyTypeString == 'FtpCachingProxy':
                    proxyType = QNetworkProxy.FtpCachingProxy

                proxy = QNetworkProxy(proxyType, proxyHost, proxyPort,
                                      proxyUser, proxyPassword)
            self.manager.setProxy(proxy)


_widget = None

def getConnectDockWidget():
    global _widget
    if _widget is None:
        _widget = ConnectDockWidget()
    return _widget