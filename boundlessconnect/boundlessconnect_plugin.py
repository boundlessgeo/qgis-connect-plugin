# -*- coding: utf-8 -*-

"""
***************************************************************************
    boundlessconnect_plugin.py
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

import site
import os

site.addsitedir(os.path.abspath(os.path.dirname(__file__) + '/ext-libs'))

from builtins import object

__author__ = 'Alexander Bruy'
__date__ = 'February 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.PyQt.QtCore import QCoreApplication, QSettings, QLocale, QTranslator, QFileInfo, Qt
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QPushButton
from qgis.PyQt.QtGui import QIcon

from qgis.gui import QgsMessageBar, QgsMessageBarItem

from pyplugin_installer.installer_data import (repositories,
                                               plugins)

from boundlessconnect.gui.connectdockwidget import getConnectDockWidget
from boundlessconnect import utils

pluginPath = os.path.dirname(__file__)


class BoundlessConnectPlugin(object):
    def __init__(self, iface):
        self.iface = iface
        self.dockWidget = None

        try:
            from boundlessconnect.tests import testerplugin
            from qgistester.tests import addTestModule
            addTestModule(testerplugin, 'Boundless Connect')
        except Exception as e:
            pass

        overrideLocale = QSettings().value('locale/overrideFlag', False, bool)
        if not overrideLocale:
            locale = QLocale.system().name()[:2]
        else:
            locale = QSettings().value('locale/userLocale', '')

        qmPath = '{}/i18n/boundlessconnect_{}.qm'.format(pluginPath, locale)

        if os.path.exists(qmPath):
            self.translator = QTranslator()
            self.translator.load(qmPath)
            QCoreApplication.installTranslator(self.translator)

        self.iface.initializationCompleted.connect(self.checkFirstRun)

    def initGui(self):
        self.dockWidget = getConnectDockWidget()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget)
        self.dockWidget.hide()

        utils.setRepositoryUrl()

        self.actionRunWizard = self.dockWidget.toggleViewAction()
        self.actionRunWizard.setText(self.tr('Boundless Connect'))
        self.actionRunWizard.setIcon(
            QIcon(os.path.join(pluginPath, 'icons', 'connect.svg')))
        self.actionRunWizard.setWhatsThis(
            self.tr('Boundless Connect'))
        self.actionRunWizard.setObjectName('actionRunWizard')

        self.actionPluginFromZip = QAction(
            self.tr('Install plugin from ZIP'), self.iface.mainWindow())
        self.actionPluginFromZip.setIcon(
            QIcon(os.path.join(pluginPath, 'icons', 'plugin.svg')))
        self.actionPluginFromZip.setWhatsThis(
            self.tr('Install plugin from ZIP file stored on disk'))
        self.actionPluginFromZip.setObjectName('actionPluginFromZip')

        self.actionPluginFromZip.triggered.connect(self.installPlugin)

        # If Boundless repository is a directory, add menu entry
        # to start modified Plugin Manager which works with local repositories
        if utils.isRepositoryInDirectory():
            self.actionPluginManager = QAction(
                self.tr('Manage plugins (local folder)'), self.iface.mainWindow())
            self.actionPluginManager.setIcon(
                QIcon(os.path.join(pluginPath, 'icons', 'plugin.svg')))
            self.actionPluginManager.setWhatsThis(
                self.tr('Manage and install plugins from local repository'))
            self.actionPluginManager.setObjectName('actionPluginManager')

            self.iface.addPluginToMenu(
                self.tr('Boundless Connect'), self.actionPluginManager)

            self.actionPluginManager.triggered.connect(self.pluginManagerLocal)

        actions = self.iface.mainWindow().menuBar().actions()
        for action in actions:
            if action.menu().objectName() == 'mPluginMenu':
                menuPlugin = action.menu()
                separator = menuPlugin.actions()[1]
                menuPlugin.insertAction(separator, self.actionRunWizard)
                menuPlugin.insertAction(separator, self.actionPluginFromZip)
                if utils.isRepositoryInDirectory():
                    menuPlugin.insertAction(separator, self.actionPluginManager)

        # Enable check for updates if it is not enabled
        utils.addCheckForUpdates()

    def unload(self):
        actions = self.iface.mainWindow().menuBar().actions()
        for action in actions:
            if action.menu().objectName() == 'mPluginMenu':
                menuPlugin = action.menu()
                menuPlugin.removeAction(self.actionRunWizard)
                menuPlugin.removeAction(self.actionPluginFromZip)
                if utils.isRepositoryInDirectory():
                    menuPlugin.removeAction(self.actionPluginManager)

        self.dockWidget.hide()

        try:
            from boundlessconnect.tests import testerplugin
            from qgistester.tests import removeTestModule
            removeTestModule(testerplugin, 'Boundless Connect')
        except Exception as e:
            pass

    def checkFirstRun(self):
        settings = QSettings('Boundless', 'BoundlessConnect')
        firstRun = settings.value('firstRun', True, bool)
        settings.setValue('firstRun', False)

        if firstRun:
            self.dockWidget.show()
            utils.installFromStandardPath()

        self.dockWidget.askForAuth = True

    def installPlugin(self):
        settings = QSettings('Boundless', 'BoundlessConnect')
        lastDirectory = settings.value('lastPluginDirectory', '.')

        fileName, __, __ = QFileDialog.getOpenFileName(self.iface.mainWindow(),
                                               self.tr('Open file'),
                                               lastDirectory,
                                               self.tr('Plugin packages (*.zip *.ZIP)'))

        if fileName == '':
            return

        result = utils.installFromZipFile(fileName)
        if result is None:
            self._showMessage(self.tr('Plugin installed successfully'),
                              QgsMessageBar.SUCCESS)
        else:
            self._showMessage(result, QgsMessageBar.WARNING)

        settings.setValue('lastPluginDirectory',
            QFileInfo(fileName).absoluteDir().absolutePath())

    def pluginManagerLocal(self):
        utils.showPluginManager(False)

    def _showMessage(self, message, level=QgsMessageBar.INFO):
        self.iface.messageBar().pushMessage(
            message, level, self.iface.messageTimeout())

    def tr(self, text):
        return QCoreApplication.translate('Boundless Connect', text)
