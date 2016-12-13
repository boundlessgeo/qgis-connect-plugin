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
from builtins import str

__author__ = 'Alexander Bruy'
__date__ = 'February 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import json
import base64
import webbrowser

from qgis.utils import iface

from boundlessconnect import connect
from boundlessconnect.connect import ConnectContent
from boundlessconnect.gui.executor import execute

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QUrl, QSettings, Qt
from qgis.PyQt.QtGui import QIcon, QCursor
from qgis.PyQt.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from qgis.PyQt.QtNetwork import (QNetworkRequest,
                                 QNetworkReply,
                                 QNetworkAccessManager,
                                 QNetworkProxyFactory,
                                 QNetworkProxy
                                )
from qgis.PyQt.QtWebKitWidgets import QWebPage

from qgis.core import QgsAuthManager, QgsAuthMethodConfig

from pyplugin_installer.installer_data import reposGroup

from boundlessconnect import utils
from boundlessconnect.plugins import boundlessRepoName, authEndpointUrl

pluginPath = os.path.split(os.path.dirname(__file__))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'connectdockwidget.ui'))

HELP_URL = "https://connect.boundlessgeo.com/docs/desktop/plugins/connect/usage.html"

class ConnectDockWidget(BASE, WIDGET):

    def __init__(self, parent=None, visible=False):
        super(ConnectDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.loggedIn = False
        self.askForAuth = False

        self.setVisible(visible)

        self.setWindowIcon(QIcon(os.path.join(pluginPath, 'icons', 'connect.svg')))
        self.svgLogo.load(os.path.join(pluginPath, 'icons', 'connect-logo.svg'))

        btnOk = self.buttonBox.button(QDialogButtonBox.Ok)
        btnOk.setText(self.tr('Login'))

        self.buttonBox.helpRequested.connect(self.showHelp)
        self.buttonBox.accepted.connect(self.logIn)
        self.btnSignOut.clicked.connect(self.showLogin)

        self.labelLevel.linkActivated.connect(self.showLogin)
        self.leSearch.returnPressed.connect(self.search)
        self.leSearch.setIcon(QIcon(os.path.join(pluginPath, 'icons', 'search.svg')))
        self.leSearch.setPlaceholderText("Search text")
        self.btnSearch.clicked.connect(self.search)

        self.leLogin.setIcon(QIcon(os.path.join(pluginPath, 'icons', 'envelope.svg')))
        self.leLogin.setPlaceholderText("Email")

        self.webView.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.webView.settings().setUserStyleSheetUrl(QUrl("file://" +
            os.path.join(os.path.dirname(__file__), "search.css").replace("\\", "/")))
        self.webView.linkClicked.connect(self.linkClicked)

        settings = QSettings()
        settings.beginGroup(reposGroup)
        self.authId = settings.value(boundlessRepoName + '/authcfg', '')
        settings.endGroup()

        self.showLogin()

    def showEvent(self, event):
        if self.authId != '' and self.askForAuth and not self.loggedIn:
            authConfig = QgsAuthMethodConfig()
            QgsAuthManager.instance().loadAuthenticationConfig(self.authId, authConfig, True)
            username = authConfig.config('username')
            password = authConfig.config('password')
            self.leLogin.setText(username)
            self.lePassword.setText(password)

        BASE.showEvent(self, event)

    def keyPressEvent(self, event):
        if self.stackedWidget.currentIndex() == 0:
            if event.key() in [Qt.Key_Return, Qt.Key_Enter]:
                self.logIn()

        BASE.keyPressEvent(self, event)

    def showLogin(self):
        self.stackedWidget.setCurrentIndex(0)
        self.webView.setVisible(False)
        self.webView.setHtml("")
        self.leSearch.setText("")
        self.leLogin.setText("")
        self.lePassword.setText("")

    def showHelp(self):
        webbrowser.open(HELP_URL)

    def linkClicked(self, url):
        name = url.toString()
        if name == "next":
            self.search(self.searchPage + 1)
        elif name == "previous":
            self.search(self.searchPage - 1)
        else:
            content = self.searchResults[name]
            content.open(self.roles)

    def logIn(self):
        utils.addBoundlessRepository()
        if self.leLogin.text().strip() == '' or self.lePassword.text().strip() == '':
            execute(connect.loadPlugins)
            self.stackedWidget.setCurrentIndex(1)
            self.roles = ["open"]
            self.labelLevel.setVisible(False)
            self.btnSignOut.setText(self.tr("Go to login"))
            self.loggedIn = True
            return

        self.request = QNetworkRequest(QUrl(authEndpointUrl))
        httpAuth = base64.encodestring('{}:{}'.format(self.leLogin.text().strip(), self.lePassword.text().strip()))[:-1]
        self.request.setRawHeader('Authorization', 'Basic {}'.format(httpAuth))
        self.manager = QNetworkAccessManager()
        self.setProxy()
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.reply = self.manager.get(self.request)
        self.reply.finished.connect(self.requestFinished)

    def search(self, page=0):
        text = self.leSearch.text().strip()
        if text:
            self.searchPage = page
            try:
                results = execute(lambda: connect.search(text, page=self.searchPage))
                if results:
                    self.searchResults = {r.url:r for r in results}
                    html = "<ul>"
                    for r in results:
                        html += "<li>%s</li>" % r.asHtmlEntry(self.roles)
                    html += "</ul>"
                    if len(results) == connect.RESULTS_PER_PAGE:
                        if self.searchPage == 0:
                            html += "<a class='pagination' href='next'>Next</a>"
                        else:
                            html += "<a class='pagination' href='previous'>Previous</a><a class='pagination' href='next'>Next</a>"
                    self.webView.setHtml(html)
                    self.webView.setVisible(True)
                else:
                    QMessageBox.warning(iface.mainWindow(), "Search", "No search matching the entered text was found.")
                    self.webView.setVisible(False)
            except Exception as e:
                QMessageBox.warning(self, "Search",
                    u"There has been a problem performing the search:\n" + str(e.args[0]),
                    QMessageBox.Ok)

    def requestFinished(self):
        QApplication.restoreOverrideCursor()
        reply = self.sender()
        visible = True
        if reply.error() != QNetworkReply.NoError:
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 401:
                msg = self.tr('Your credentials seem invalid. \n'
                              'You will be able to access only open content.\n'
                              'Do you want to save credentials anyway?')
            else:
                msg = self.tr('An error occurred when validating your '
                              'credentials. Server responded:\n{}.\n'
                              'You will be able to access only open content.\n'
                              'Do you want to save credentials anyway?'.format(reply.errorString()))
            ret = QMessageBox.warning(self, self.tr('Error!'), msg,
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
            if ret == QMessageBox.Yes:
                self.saveOrUpdateAuthId()
            visible = False
            self.roles = ["open"]
            self.btnSignOut.setText(self.tr("Go to login"))
        else:
            self.btnSignOut.setText(self.tr("Logout"))
            self.saveOrUpdateAuthId()
            self.roles = json.loads(str(reply.readAll()))

        execute(connect.loadPlugins)
        self.stackedWidget.setCurrentIndex(1)
        self.labelLevel.setVisible(visible)
        self.labelLevel.setText("Logged in as: <b>%s</b>" % self.leLogin.text())

        self.loggedIn = True

    def saveOrUpdateAuthId(self):
        if self.authId == '':
            authConfig = QgsAuthMethodConfig('Basic')
            self.authId = QgsAuthManager.instance().uniqueConfigId()
            authConfig.setId(self.authId)
            authConfig.setConfig('username', self.leLogin.text().strip())
            authConfig.setConfig('password', self.lePassword.text().strip())
            authConfig.setName('Boundless Connect Portal')

            settings = QSettings('Boundless', 'BoundlessConnect')
            authConfig.setUri(settings.value('repoUrl', ''))

            if QgsAuthManager.instance().storeAuthenticationConfig(authConfig):
                utils.setRepositoryAuth(self.authId)
            else:
                QMessageBox.information(self, self.tr('Error!'), self.tr('Unable to save credentials'))
        else:
            authConfig = QgsAuthMethodConfig()
            QgsAuthManager.instance().loadAuthenticationConfig(self.authId, authConfig, True)
            authConfig.setConfig('username', self.leLogin.text().strip())
            authConfig.setConfig('password', self.lePassword.text().strip())
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
