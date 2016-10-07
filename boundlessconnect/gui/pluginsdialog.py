# -*- coding: utf-8 -*-

"""
***************************************************************************
    pluginsdialog.py
    ---------------------
    Date                 : October 2016
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
__date__ = 'October 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from PyQt4 import uic
from PyQt4.QtCore import Qt
from PyQt4.QtGui import (QIcon,
                         QPushButton,
                         QListWidgetItem,
                         QDialogButtonBox,
                         QDialog,
                         QDesktopServices
                        )
from PyQt4.QtNetwork import (QNetworkRequest,
                             QNetworkReply,
                             QNetworkAccessManager
                            )
from PyQt4.QtWebKit import QWebPage

import pyplugin_installer
from pyplugin_installer.installer_data import plugins

from boundlessconnect import utils

pluginPath = os.path.split(os.path.dirname(__file__))[0]
WIDGET, BASE = uic.loadUiType(
    os.path.join(pluginPath, 'ui', 'pluginsdialogbase.ui'))


class PluginsDialog(BASE, WIDGET):
    def __init__(self, parent=None):
        super(PluginsDialog, self).__init__(parent)
        self.setupUi(self)

        self.setWindowIcon(QIcon(os.path.join(pluginPath, 'icons', 'connect.svg')))

        self.btnInstall = QPushButton(self.tr('Install plugin'))
        self.btnInstall.clicked.connect(self.installPlugin)
        self.buttonBox.addButton(self.btnInstall, QDialogButtonBox.ActionRole)

        self.lstPlugins.currentItemChanged.connect(self.showPluginDetails)

        self.webView.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.webView.linkClicked.connect(self.openLink)

        self.loadPlugins()

    def loadPlugins(self):
        installer = pyplugin_installer.instance()
        installer.fetchAvailablePlugins(True)

        for plugin in plugins.all():
            if utils.isBoundlessPlugin(plugins.all()[plugin]) and plugin not in ['boundlessconnect']:
                item = QListWidgetItem(plugins.all()[plugin]['name'])
                item.setData(Qt.UserRole, plugin)
                self.lstPlugins.addItem(item)

    def showPluginDetails(self, current, previous):
        pluginId = current.data(Qt.UserRole)
        plugin = plugins.all()[pluginId]

        html = '<style>body, table {padding:0px; margin:0px; font-family:verdana; font-size: 1.1em;}</style>'
        html += '<body>'
        html += '<table cellspacing="4" width="100%"><tr><td>'
        html += '<img src="file://{}" style="float:right;max-width:64px;max-height:64px;">'.format(os.path.join(pluginPath, 'icons', 'desktop.png'))
        html += '<h1>{}</h1>'.format(plugin['name'])
        html += '<h3>{}</h3>'.format(plugin['description'])

        if plugin['about'] != '':
            html += plugin['about'].replace('\n', '<br/>')

        html += '<br/><br/>'

        if plugin['category'] != '':
            html += '{}: {} <br/>'.format(self.tr('Category'), plugin['category'])

        if plugin['tags'] != '':
            html += '{}: {} <br/>'.format(self.tr('Tags'), plugin['tags'])

        if plugin['homepage'] != '' or plugin['tracker'] != '' or plugin['code_repository'] != '':
            html += self.tr('More info:')

            if plugin['homepage'] != '':
                html += '<a href="{}">{}</a> &nbsp;'.format(plugin['homepage'], self.tr('homepage') )

            if plugin['tracker'] != '':
                html += '<a href="{}">{}</a> &nbsp;'.format(plugin['tracker'], self.tr('bug_tracker') )

            if plugin['code_repository'] != '':
                html += '<a href="{}">{}</a> &nbsp;'.format(plugin['code_repository'], self.tr('code_repository') )

            html += '<br/>'

        html += '<br/>'

        if plugin['author_email'] != '':
            html += '{}: <a href="mailto:{}">{}</a>'.format(self.tr('Author'), plugin['author_email'], plugin['author_name'])
            html += '<br/><br/>'
        elif plugin['author_name'] != '':
            html += '{}: {}'.format(self.tr('Author'), plugin['author_name'])
            html += '<br/><br/>'

        if plugin['version_installed'] != '':
            ver = plugin['version_installed']
            if ver == '-1':
                ver = '?'

            html += self.tr('Installed version: {} (in {})<br/>'.format(ver, plugin['library']))

        if plugin['version_available'] != '':
            html += self.tr('Available version: {} (in {})<br/>'.format(plugin['version_available'], plugin['zip_repository']))

        if plugin['changelog'] != '':
            html += '<br/>'
            changelog = self.tr('Changelog:<br/>{} <br/>'.format(plugin['changelog']))
            html += changelog.replace('\n', '<br/>')

        html += '</td></tr></table>'
        html += '</body>'

        self.webView.setHtml(html)

        if plugin['status'] == 'upgradeable':
            self.btnInstall.setText(self.tr('Upgrade plugin'))
        elif plugin['status'] in ['not installed', 'new']:
            self.btnInstall.setText(self.tr('Install plugin'))
        else:
            self.btnInstall.setText(self.tr('Reinstall plugin'))

    def installPlugin(self):
        plugin = self.lstPlugins.currentItem().data(Qt.UserRole)

        installer = pyplugin_installer.instance()
        installer.installPlugin(plugin)

    def openLink(self, url):
        QDesktopServices.openUrl(url)

    def reject(self):
        QDialog.reject(self)
