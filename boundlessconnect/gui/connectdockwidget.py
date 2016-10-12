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
from boundlessconnect import connect
from boundlessconnect.connect import ConnectContent
from boundlessconnect.gui.executor import execute
from collections import defaultdict
from requests.exceptions import RequestException

from PyQt4 import uic
from PyQt4.QtCore import QUrl, QSettings, Qt
from PyQt4.QtGui import (QIcon,
                         QDesktopServices,
                         QDialogButtonBox,
                         QMessageBox
                        , QTreeWidgetItem)
from PyQt4.QtNetwork import QNetworkRequest, QNetworkReply, QNetworkAccessManager

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

        self.buttonBox.helpRequested.connect(self.showHelp)
        self.buttonBox.accepted.connect(self.accept)
        self.btnSearch.clicked.connect(self.search)
        self.btnInstall.clicked.connect(self.install)
        self.searchWidget.setVisible(False)

        self.resultsTree.currentItemChanged.connect(self.itemChanged)

    def itemChanged(self):
        self.btnInstall.setEnabled(False)
        current = self.resultsTree.currentItem()
        if current:
            if isinstance(current.data(0, Qt.UserRole), ConnectContent):
                content = current.data(0, Qt.UserRole)
                self.webView.setHtml(content.description)
                self.btnInstall.setEnabled(True)
            else:
                self.webView.setHtml(current.child(0).data(0, Qt.UserRole).categoryDescription())


    def showHelp(self):
        if not QDesktopServices.openUrl(QUrl(HELP_URL)):
            QMessageBox.warning(self, self.tr('Error'), self.tr('Can not open help URL in browser'))

    def install(self):
        content = self.resultsTree.currentItem().data(0, Qt.UserRole)
        execute(content.open)

    def resetWebView(self):
        self.webView.setHtml("<h2>Select an element to show its description</h2>")

    def accept(self):
        utils.addBoundlessRepository()
        if self.leLogin.text() == '' or self.lePassword.text() == '':
            execute(connect.loadPlugins)
            self.authWidget.setVisible(False)
            self.searchWidget.setVisible(True)
            self.labelLogged.setText("Logged as: <b>Not logged</b>")
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
                self.resultsTree.clear()
                if results:
                    resultsByGroups = defaultdict(list)
                    for r in results:
                        resultsByGroups[r.typeName()].append(r)
                    for group, items in resultsByGroups.iteritems():
                        icon = items[0].icon()
                        treeItem = QTreeWidgetItem()
                        treeItem.setText(0, group)
                        treeItem.setIcon(0, icon)
                        for item in items:
                            treeSubItem = QTreeWidgetItem()
                            treeSubItem.setText(0, item.name)
                            treeSubItem.setData(0, Qt.UserRole, item)
                            treeSubItem.setIcon(0, icon)
                            treeItem.addChild(treeSubItem)
                        self.resultsTree.addTopLevelItem(treeItem)
                        treeItem.setExpanded(True)
                    self.resetWebView()
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
        else:
            self.saveOrUpdateAuthId()
            execute(connect.loadPlugins)
            self.authWidget.setVisible(False)
            self.searchWidget.setVisible(True)
            print "yes"
            self.labelLogged.setText("Logged as: <b>%s</b>" % self.leLogin.text())

    def saveOrUpdateAuthId(self):
        if self.authId == '':
            authConfig = QgsAuthMethodConfig('Basic')
            authId = QgsAuthManager.instance().uniqueConfigId()
            authConfig.setId(authId)
            authConfig.setConfig('username', self.leLogin.text())
            authConfig.setConfig('password', self.lePassword.text())
            authConfig.setName('Boundless Connect Portal')

            settings = QSettings('Boundless', 'BoundlessConnect')
            authConfig.setUri(settings.value('repoUrl', '', unicode))

            if QgsAuthManager.instance().storeAuthenticationConfig(authConfig):
                utils.setRepositoryAuth(authId)
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
            proxyPort = int(settings.value('proxy/proxyPort', '0'))
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

