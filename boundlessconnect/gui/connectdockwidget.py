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
import shutil
import base64
import webbrowser
from datetime import datetime

from qgis.PyQt import uic
from qgis.PyQt.QtCore import QUrl, Qt
from qgis.PyQt.QtGui import QIcon, QCursor, QPixmap
from qgis.PyQt.QtWidgets import QApplication, QDialogButtonBox, QMessageBox
from qgis.PyQt.QtNetwork import (QNetworkRequest,
                                 QNetworkReply
                                )
from qgis.PyQt.QtWebKitWidgets import QWebPage

from qgis.core import QgsAuthManager, QgsAuthMethodConfig, QgsNetworkAccessManager
from qgis.gui import QgsMessageBar
from qgis.utils import iface

try:
    from qgis.core import QgsSettings as QSettings
except ImportError:
    from qgis.PyQt.QtCore import QSettings


from pyplugin_installer.installer_data import reposGroup

from qgiscommons2.network.oauth2 import (oauth2_supported,
                                setup_oauth,
                                get_oauth_authcfg
                               )
from qgiscommons2.gui.settings import pluginSetting, setPluginSetting

from boundlessconnect.connect import ConnectContent
from boundlessconnect.gui.executor import execute
from boundlessconnect.plugins import boundlessRepoName, authEndpointUrl
from boundlessconnect import connect
from boundlessconnect import utils
from boundlessconnect import basemaputils

pluginPath = os.path.split(os.path.dirname(__file__))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'connectdockwidget.ui'))


class ConnectDockWidget(BASE, WIDGET):

    def __init__(self, parent=None, visible=False):
        super(ConnectDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.loggedIn = False
        self.token = None

        self.progressBar.hide()

        self.setVisible(visible)

        self.setWindowIcon(QIcon(os.path.join(pluginPath, 'icons', 'connect.svg')))
        self.svgLogo.load(os.path.join(pluginPath, 'icons', 'connect-logo.svg'))

        self.lblSmallLogo.setPixmap(QPixmap(os.path.join(pluginPath, 'icons', 'connect.png')))
        self.lblSmallLogo.hide()

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
        self.leSearch.buttonClicked.connect(self.search)
        self.leSearch.returnPressed.connect(self.search)
        self.connectWidget.rememberStateChanged.connect(self.updateSettings)

        self.webView.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        cssFile = os.path.join(pluginPath, "resources", "search.css")
        with open(cssFile) as f:
            content = f.read()

        self.css = content.replace("#PLUGIN_PATH#", QUrl.fromLocalFile(pluginPath).toString())

        self.webView.linkClicked.connect(self.linkClicked)

        for cat, cls in connect.categories.items():
            self.cmbContentType.addItem(cls[1], cat)

        settings = QSettings()
        settings.beginGroup(reposGroup)
        self.authId = settings.value(boundlessRepoName + '/authcfg', '')
        settings.endGroup()
        if self.authId not in QgsAuthManager.instance().configIds():
            self.authId = ''
            utils.setRepositoryAuth(self.authId)

        self._toggleSearchControls(True)
        self.showLogin()

    def showEvent(self, event):
        fillCredentials = pluginSetting("rememberCredentials")
        if self.authId != '' and fillCredentials and not self.loggedIn:
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
        self.tabsContent.setCurrentIndex(0)
        self.svgLogo.show()
        self.lblSmallLogo.hide()
        connect.resetToken()
        self.token = None

        fillCredentials = pluginSetting("rememberCredentials")
        if fillCredentials:
            self.connectWidget.setRemember(Qt.Checked)

            username = ""
            password = ""
            if self.authId != "":
                authConfig = QgsAuthMethodConfig()
                if self.authId in QgsAuthManager.instance().configIds():
                    QgsAuthManager.instance().loadAuthenticationConfig(self.authId, authConfig, True)
                    username = authConfig.config("username")
                    password = authConfig.config("password")
                self.connectWidget.setLogin(username)
                self.connectWidget.setPassword(password)
        else:
            self.connectWidget.setRemember(Qt.Unchecked)
            self.connectWidget.setLogin("")
            self.connectWidget.setPassword("")

    def showHelp(self):
        webbrowser.open_new("file://{}".format(os.path.join(pluginPath, "docs", "html", "index.html")))

    def linkClicked(self, url):
        name = url.toString()
        if name == "next":
            self.search(self.searchPage + 1)
        elif name == "previous":
            self.search(self.searchPage - 1)
        elif name.startswith("canvas"):
            content = self.searchResults[name]
            content.addToCanvas(self.roles)
        elif name.startswith("project"):
            content = self.searchResults[name]
            content.addToDefaultProject(self.roles)
        else:
            content = self.searchResults[name]
            content.open(self.roles)

    def logIn(self):
        if self.connectWidget.login().strip() == "" or self.connectWidget.password().strip() == "":
            self._showMessage("Please enter valid Connect credentials "
                              "to use plugin.")
            return

        setPluginSetting("rememberCredentials", self.connectWidget.remember())

        utils.addBoundlessRepository()

        self.request = QNetworkRequest(QUrl(authEndpointUrl))
        httpAuth = base64.b64encode(b"%s:%s" % (self.connectWidget.login().strip(), self.connectWidget.password().strip())).decode("ascii")
        self.request.setRawHeader('Authorization', 'Basic {}'.format(httpAuth))
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        self.token = connect.getToken(self.connectWidget.login().strip(), self.connectWidget.password().strip())
        if self.token is None:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, "Error!", "Can not get token. Please check you credentials and endpoint URL in plugin settings.")
            return
        self.reply = QgsNetworkAccessManager.instance().get(self.request)
        self.reply.finished.connect(self.requestFinished)

    def search(self, page=0):
        if self.tabsContent.currentIndex() == 0:
            categories = self.cmbContentType.selectedData(Qt.UserRole)
            if len(categories) == 0:
                categories = list(connect.categories.keys())
            cat = ','.join(categories)
            self._findContent(cat, page)
        elif self.tabsContent.currentIndex() == 1:
            if oauth2_supported():
                self._findBasemaps()
        elif self.tabsContent.currentIndex() == 2:
            self._findPlugins()

        self.svgLogo.hide()
        self.lblSmallLogo.show()

    def _getSearchHtml(self, body):
        html = '''<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
                              <html>
                              <head>
                              <style>
                              {}
                              </style>
                              </head>
                              <body>
                              {}
                              </body>
                              </html>'''.format(self.css, body)
        return html

    def _findContent(self, category, page=0):
        if self.token is None:
            self._showMessage("Seems you have no Connect token. Login with valid Connect credentials and try again.",
                              QgsMessageBar.WARNING)
            return

        text = self.leSearch.text().strip()
        self.searchPage = page
        try:
            self._toggleSearchProgress()
            results = execute(lambda: connect.search(text, category, self.searchPage, self.token))
            if results:
                self.searchResults = {r.url:r for r in results}
                body = "<ul>"
                for r in results:
                    body += "<li>%s</li>" % r.asHtmlEntry(self.roles)
                body += "</ul>"

                if len(results) == connect.RESULTS_PER_PAGE:
                    if self.searchPage == 0:
                        body += "<div class='pagination'><div class='next'><a href='next'>Next</a></div></div>"
                    else:
                        body += "<div class='pagination'><div class='prev'><a href='previous'>Prev</a></div><div class='next'><a href='next'>Next</a></div></div>"
                else:
                    if self.searchPage != 0:
                        body += "<div class='pagination'><div class='prev'><a href='previous'>Prev</a></div></div>"
            else:
                body = ""

            self.webView.setHtml(self._getSearchHtml(body))
            self.webView.setVisible(True)
            self._toggleSearchProgress(False)
        except Exception as e:
            self._toggleSearchProgress(False)
            self.webView.setHtml("")
            self._showMessage("There has been a problem performing the search:\n{}".format(str(e.args[0])),
                              QgsMessageBar.WARNING)

    def _findPlugins(self):
        if self.token is None:
            self._showMessage("Seems you have no Connect token. Login with valid Connect credentials and try again.",
                              QgsMessageBar.WARNING)
            return

        text = self.leSearch.text().strip()
        try:
            self._toggleSearchProgress()
            results = execute(lambda: connect.findAll(text, "PLUG", self.token))
            body = "<h1>{} results</h1><hr/>".format(len(results))
            if results:
                self.searchResults = {r.url:r for r in results}
                body += "<ul>"
                for r in results:
                    body += "<li>%s</li>" % r.asHtmlEntry(self.roles)
                body += "</ul>"

            self.webView.setHtml(self._getSearchHtml(body))
            self.webView.setVisible(True)
            self._toggleSearchProgress(False)
        except Exception as e:
            self._toggleSearchProgress(False)
            self.webView.setHtml("")
            self._showMessage("There has been a problem performing the search:\n{}".format(str(e.args[0])),
                              QgsMessageBar.WARNING)

    def _findBasemaps(self):
        if self.token is None:
            self._showMessage("Seems you have no Connect token. Login with valid Connect credentials and try again.",
                              QgsMessageBar.WARNING)
            return

        text = self.leSearch.text().strip()
        try:
            results = execute(lambda: connect.searchBasemaps(text, self.token))
            body = "<h1>{} results</h1><hr/>".format(len(results))
            if results:
                self.searchResults = {"canvas"+r.url:r for r in results}
                self.searchResults.update({"project"+r.url:r for r in results})
                body += "<ul>"
                for r in results:
                    body += "<li>%s</li>" % r.asHtmlEntry(self.roles)
                body += "</ul>"
            self.webView.setHtml(self._getSearchHtml(body))
            self.webView.setVisible(True)
        except Exception as e:
            self._toggleSearchProgress(False)
            self.webView.setHtml("")
            self._showMessage("There has been a problem performing the search:\n{}".format(str(e.args[0])),
                              QgsMessageBar.WARNING)

    def requestFinished(self):
        QApplication.restoreOverrideCursor()
        reply = self.sender()
        visible = True
        if reply.error() != QNetworkReply.NoError:
            if reply.attribute(QNetworkRequest.HttpStatusCodeAttribute) == 401:
                msg = 'Your credentials seem invalid.\n' \
                      'You will not be able to access any content.\n' \
                      'Please enter valid Connect credentials to use plugin.'
            else:
                msg = 'An error occurred when validating your ' \
                      'credentials. Server responded:\n{}.\n' \
                      'You will not be able to access any content.\n' \
                      'Please enter valid Connect credentials to use plugin'.format(reply.errorString())
            QMessageBox.warning(self, 'Error!', msg)
            return
        else:
            self.btnSignOut.setText("Logout")
            self.saveOrUpdateAuthId()
            self.roles = json.loads(str(reply.readAll()))

            # if this is first login ask if user wants to have basemap
            settings = QSettings()
            firstLogin = settings.value('boundlessconnect/firstLogin', True, bool)
            if firstLogin:
                settings.setValue('boundlessconnect/firstLogin', False)
                if oauth2_supported() and basemaputils.canAccessBasemap(self.roles):
                    ret = QMessageBox.question(self,
                                               self.tr('Base Maps'),
                                               self.tr('Would you like to add Boundless basemap '
                                                       'to your default project? This option can '
                                                       'be disabled at any time in the settings.'),
                                               QMessageBox.Yes | QMessageBox.No,
                                               QMessageBox.No)
                    if ret == QMessageBox.Yes:
                        if self.token is None:
                            self._showMessage("Seems you have no Connect token. Login with valid Connect credentials and try again.",
                                              QgsMessageBar.WARNING)
                            return

                        if self.installBaseMap():
                            pass

        execute(connect.loadPlugins)
        self.stackedWidget.setCurrentIndex(1)
        self.labelLevel.setVisible(visible)
        self.labelLevel.setText("Logged in as: <b>%s</b>" % self.connectWidget.login())

        self.loggedIn = True

        cat = ",".join(list(connect.categories.keys()))
        self._findContent(cat)

    def saveOrUpdateAuthId(self):
        if self.authId == '':
            authConfig = QgsAuthMethodConfig('Basic')
            self.authId = QgsAuthManager.instance().uniqueConfigId()
            authConfig.setId(self.authId)
            authConfig.setConfig('username', self.connectWidget.login().strip())
            authConfig.setConfig('password', self.connectWidget.password().strip())
            authConfig.setName('Boundless Connect Portal')

            authConfig.setUri(pluginSetting('repoUrl'))

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
            endpointUrl = "{}/token/oauth?version={}".format(pluginSetting("connectEndpoint"), pluginSetting("apiVersion"))
            setup_oauth(self.connectWidget.login().strip(), self.connectWidget.password().strip(), endpointUrl)

    def tabChanged(self, index):
        if index == 0:
            self._toggleCategoriesSelector(True)
            self._toggleSearchControls(True)
            self.webView.setHtml("")
            categories = self.cmbContentType.selectedData(Qt.UserRole)
            if len(categories) == 0:
                categories = list(connect.categories.keys())
            cat = ','.join(categories)
            self._findContent(cat)
        elif index == 1:
            self._toggleCategoriesSelector(False)
            self._toggleSearchControls(oauth2_supported())
            self.webView.setHtml("")
            if oauth2_supported():
                self._findBasemaps()
        elif index == 2:
            self._toggleCategoriesSelector(False)
            self._toggleSearchControls(True)
            self.webView.setHtml("")
            self._findPlugins()

    def _toggleCategoriesSelector(self, visible):
        self.lblCategorySearch.setVisible(visible)
        self.cmbContentType.setVisible(visible)

    def _toggleSearchControls(self, enabled):
        self.leSearch.setEnabled(enabled)
        self.lblOAuthWarning.setVisible(not enabled)

    def installBaseMap(self):
        authcfg = get_oauth_authcfg()
        if authcfg is None:
            self._showMessage('Could not find a valid authentication configuration!',
                              QgsMessageBar.WARNING)
            return False

        authId = authcfg.id()
        mapBoxStreets = basemaputils.getMapBoxStreetsMap(self.token)

        if os.path.isfile(basemaputils.defaultProjectPath()):
            # default project already exists, make a backup copy
            backup = basemaputils.defaultProjectPath().replace(
                '.qgs', '-%s.qgs' % datetime.now().strftime('%Y-%m-%d-%H_%M_%S'))
            shutil.copy2(basemaputils.defaultProjectPath(), backup)
            self._showMessage("A backup copy of the previous default project "
                              "has been saved to {}".format(backup))

            msgBox = QMessageBox()
            msgBox.setIcon(QMessageBox.Question)
            msgBox.setText("A default project already exists.  Do you "
                           "wish to add the Boundless basemap to your "
                           "existing default project or create a new "
                           "default project?")
            btnAdd = msgBox.addButton("Add", QMessageBox.ActionRole)
            btnCreateNew = msgBox.addButton("Create New", QMessageBox.ActionRole)
            msgBox.exec_()
            if msgBox.clickedButton() == btnAdd:
                if not basemaputils.addToDefaultProject([mapBoxStreets], ["Mapbox Streets"], authId):
                    self._showMessage("Could not update default project with basemap!",
                                      QgsMessageBar.WARNING)
                    return False
            elif msgBox.clickedButton() == btnCreateNew:
                template = basemaputils.PROJECT_DEFAULT_TEMPLATE

                prj = basemaputils.createDefaultProject([mapBoxStreets], ["Mapbox Streets"],
                                                        template, authId)
                if prj is None or prj == '':
                    self._showMessage("Could not create a valid default project from the template '{}'!".format(template),
                                      QgsMessageBar.WARNING)
                    return False

                if not basemaputils.writeDefaultProject(prj):
                    self._showMessage("Could not write the default project on disk!",
                                      QgsMessageBar.WARNING)
                    return False
        else:
            # no default project, create one
            template = basemaputils.PROJECT_DEFAULT_TEMPLATE

            prj = basemaputils.createDefaultProject([mapBoxStreets], ["Mapbox Streets"],
                                               template, authId)
            if prj is None or prj == '':
                self._showMessage("Could not create a valid default project from the template '{}'!".format(template),
                                  QgsMessageBar.WARNING)
                return False

            if not basemaputils.writeDefaultProject(prj):
                self._showMessage("Could not write the default project on disk!",
                                  QgsMessageBar.WARNING)
                return False

        self._showMessage("Basemap added to the default project.")
        return True

    def updateSettings(self, state):
        if state == Qt.Checked:
            setPluginSetting("rememberCredentials", True)
        else:
            setPluginSetting("rememberCredentials", False)

    def _toggleSearchProgress(self, show=True):
        if show:
            self.progressBar.setRange(0, 0)
            self.progressBar.show()
        else:
            self.progressBar.setRange(0, 100)
            self.progressBar.reset()
            self.progressBar.hide()

    def _showMessage(self, message, level=QgsMessageBar.INFO):
        iface.messageBar().pushMessage(
            message, level, iface.messageTimeout())


_widget = None

def getConnectDockWidget():
    global _widget
    if _widget is None:
        _widget = ConnectDockWidget()
    return _widget
