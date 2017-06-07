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
                                 QNetworkReply
                                )
from qgis.PyQt.QtWebKitWidgets import QWebPage

from qgis.core import QgsAuthManager, QgsAuthMethodConfig, QgsNetworkAccessManager
from qgis.gui import QgsMessageBar

from pyplugin_installer.installer_data import reposGroup

from qgiscommons.oauth2 import (oauth2_supported,
                                setup_oauth
                               )

from boundlessconnect.plugins import boundlessRepoName, authEndpointUrl
from boundlessconnect import utils

pluginPath = os.path.split(os.path.dirname(__file__))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'connectdockwidget.ui'))

OFFLINE_HELP_URL = os.path.join(pluginPath, 'docs', 'html', 'index.html')
OAUTH_TOKEN_URL = "https://api.test.boundlessgeo.io/v1/token/oauth/"

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
        btnOk.setText('Login')

        # setup tab bar
        self.tabsContent.addTab('Knowledge')
        self.tabsContent.addTab('Data')
        self.tabsContent.addTab('Plugins')
        self.tabsContent.setDocumentMode(True)
        self.tabsContent.setDrawBase(False)
        self._toggleCategoriesSelector(True)
        self.tabsContent.setCurrentIndex(0)
        self.tabsContent.currentChanged.connect(self.tabChanged)

        self.buttonBox.helpRequested.connect(self.showHelp)
        self.buttonBox.accepted.connect(self.logIn)
        self.btnSignOut.clicked.connect(self.showLogin)

        self.labelLevel.linkActivated.connect(self.showLogin)
        self.leSearch.returnPressed.connect(self.search)
        self.leSearch.setIcon(QIcon(os.path.join(pluginPath, 'icons', 'search.svg')))
        self.leSearch.setPlaceholderText("Search text")
        self.btnSearch.clicked.connect(self.search)

        self.webView.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.webView.settings().setUserStyleSheetUrl(QUrl("file://" +
            os.path.join(pluginPath, "resources", "connect.css").replace("\\", "/")))
        self.webView.linkClicked.connect(self.linkClicked)

        content = {}
        self.cmbContentType.addItem("All", "ALL")
        for cat, cls in connect.categories.items():
            self.cmbContentType.addItem(cls[1], cat)
        self.cmbContentType.setCheckedItems(["All"])

        settings = QSettings()
        settings.beginGroup(reposGroup)
        self.authId = settings.value(boundlessRepoName + '/authcfg', '')
        settings.endGroup()
        if self.authId not in QgsAuthManager.instance().configIds():
            self.authId = ''
            utils.setRepositoryAuth(self.authId)

        self.showLogin()

    def showEvent(self, event):
        if self.authId != '' and self.askForAuth and not self.loggedIn:
            authConfig = QgsAuthMethodConfig()
            if self.authId in QgsAuthManager.instance().configIds():
                QgsAuthManager.instance().loadAuthenticationConfig(self.authId, authConfig, True)
                username = authConfig.config('username')
                password = authConfig.config('password')
            else:
                self.authId = ''
                utils.setRepositoryAuth(self.authId)
                self._showMessage('Could not find Connect credentials in the database.',
                                  QgsMessageBar.WARNING)
                username = ''
                password = ''

            self.connectWidget.setLogin(username)
            self.connectWidget.setPassword(password)

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
        self.connectWidget.setLogin("")
        self.connectWidget.setPassword("")

    def showHelp(self):
        webbrowser.open(OFFLINE_HELP_URL)

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
        if self.connectWidget.login().strip() == "" or self.connectWidget.password().strip() == "":
            execute(connect.loadPlugins)
            self.stackedWidget.setCurrentIndex(1)
            self.roles = ["open"]
            self.labelLevel.setVisible(False)
            self.btnSignOut.setText("Go to login")
            self.loggedIn = True
            return

        self.request = QNetworkRequest(QUrl(authEndpointUrl))
        #httpAuth = base64.encodestring('{}:{}'.format(self.connectWidget.login().strip(), self.connectWidget.password().strip()))[:-1]
        httpAuth = base64.b64encode(b"%s:%s" % (self.connectWidget.login().strip(), self.connectWidget.password().strip())).decode("ascii")
        self.request.setRawHeader('Authorization', 'Basic {}'.format(httpAuth))
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.reply = QgsNetworkAccessManager.instance().get(self.request)
        self.reply.finished.connect(self.requestFinished)

    def search(self, page=0):
        if self.tabsContent.currentIndex() == 0:
            cat = ','.join(self.cmbContentType.selectedData(Qt.UserRole))
            self._search(cat, page)
        elif self.tabsContent.currentIndex() == 1:
            self._findBasemap()
        elif self.tabsContent.currentIndex() == 2:
            self_search("PLUG", page)

    def _search(self, category, page=0):
        text = self.leSearch.text().strip()
        if text:
            self.searchPage = page
            try:
                results = execute(lambda: connect.search(text, category, self.searchPage))
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
                    self._showMessage("No search matching the entered text was found.",
                                      QgsMessageBar.WARNING)
                    self.webView.setVisible(False)
            except Exception as e:
                self._showMessage("There has been a problem performing the search:\n{}".format(str(e.args[0])),
                                  QgsMessageBar.WARNING)

    def _findBasemap(self):
        text = self.leSearch.text().strip()
        if text:
            try:
                results = execute(lambda: connect.searchBasemaps(text))
                if results:
                    html = "<ul>"
                    for r in results:
                        html += "<li>%s</li>" % r.asHtmlEntry(self.roles)
                    html += "</ul>"
                    self.webView.setHtml(html)
                    self.webView.setVisible(True)
                else:
                    self._showMessage("No search matching the entered text was found.",
                                      QgsMessageBar.WARNING)
                    self.webView.setVisible(False)
            except Exception as e:
                self._showMessage("There has been a problem performing the search:\n{}".format(str(e.args[0])),
                                  QgsMessageBar.WARNING)

    def requestFinished(self):
        QApplication.restoreOverrideCursor()
        reply = self.sender()
        visible = True
        if reply.error() != QNetworkReply.NoError:
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 401:
                msg = 'Your credentials seem invalid.\n' \
                      'You will be able to access only open content.\n' \
                      'Do you want to save credentials anyway?'
            else:
                msg = 'An error occurred when validating your ' \
                      'credentials. Server responded:\n{}.\n' \
                      'You will be able to access only open content.\n' \
                      'Do you want to save credentials anyway?'.format(reply.errorString())
            ret = QMessageBox.warning(self, 'Error!', msg,
                                      QMessageBox.Yes | QMessageBox.No,
                                      QMessageBox.No)
            if ret == QMessageBox.Yes:
                self.saveOrUpdateAuthId()
            visible = False
            self.roles = ["open"]
            self.btnSignOut.setText("Go to login")
        else:
            self.btnSignOut.setText("Logout")
            self.saveOrUpdateAuthId()
            self.roles = json.loads(str(reply.readAll()))

        execute(connect.loadPlugins)
        self.stackedWidget.setCurrentIndex(1)
        self.labelLevel.setVisible(visible)
        self.labelLevel.setText("Logged in as: <b>%s</b>" % self.connectWidget.login())

        self.loggedIn = True

    def saveOrUpdateAuthId(self):
        if self.authId == '':
            authConfig = QgsAuthMethodConfig('Basic')
            self.authId = QgsAuthManager.instance().uniqueConfigId()
            authConfig.setId(self.authId)
            authConfig.setConfig('username', self.connectWidget.login().strip())
            authConfig.setConfig('password', self.connectWidget.password().strip())
            authConfig.setName('Boundless Connect Portal')

            settings = QSettings('Boundless', 'BoundlessConnect')
            authConfig.setUri(settings.value('repoUrl', ''))

            if QgsAuthManager.instance().storeAuthenticationConfig(authConfig):
                utils.setRepositoryAuth(self.authId)
            else:
                self._showMessage('Unable to save credentials.', QgsMessageBar.WARNING)
        else:
            authConfig = QgsAuthMethodConfig()
            QgsAuthManager.instance().loadAuthenticationConfig(self.authId, authConfig, True)
            authConfig.setConfig('username', self.connectWidget.login().strip())
            authConfig.setConfig('password', self.connectWidget.password().strip())
            QgsAuthManager.instance().updateAuthenticationConfig(authConfig)

        # also setup OAuth2 configuration if possible
        if oauth2_supported():
            setup_oauth(self.connectWidget.login().strip(), self.connectWidget.password().strip(), OAUTH_TOKEN_URL)

    def tabChanged(self, index):
        if index == 0:
            self._toggleCategoriesSelector(True)
            cat = ','.join(self.cmbContentType.selectedData(Qt.UserRole))
            self._search(cat)
        elif index == 1:
            self._toggleCategoriesSelector(False)
            self._findBasemap()
        elif index == 2:
            self._toggleCategoriesSelector(False)
            self._search("PLUG")

    def _toggleCategoriesSelector(self, visible):
        self.lblCategorySearch.setVisible(visible)
        self.cmbContentType.setVisible(visible)

    def _showMessage(self, message, level=QgsMessageBar.INFO):
        iface.messageBar().pushMessage(
            message, level, iface.messageTimeout())


_widget = None

def getConnectDockWidget():
    global _widget
    if _widget is None:
        _widget = ConnectDockWidget()
    return _widget
