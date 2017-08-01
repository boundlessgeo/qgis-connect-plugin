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

from qgis.PyQt.QtCore import QSettings, Qt
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon

from qgis.gui import QgsMessageBar, QgsMessageBarItem

from pyplugin_installer.installer_data import (repositories,
                                               plugins)
from qgiscommons.gui import (askForFiles,
                                addHelpMenu,
                                removeHelpMenu,
                                addAboutMenu,
                                removeAboutMenu)
from qgiscommons.gui.settings import (readSettings,
                                      addSettingsMenu,
                                      removeSettingsMenu)

from boundlessconnect.gui.connectdockwidget import getConnectDockWidget
from boundlessconnect import utils

pluginPath = os.path.dirname(__file__)


class BoundlessConnectPlugin(object):
    def __init__(self, iface):
        self.iface = iface

        try:
            from boundlessconnect.tests import testerplugin
            from qgistester.tests import addTestModule
            addTestModule(testerplugin, 'Boundless Connect')
        except Exception as e:
            pass

        self.dockWidget = None
        readSettings()

        self.iface.initializationCompleted.connect(self.checkFirstRun)

    def initGui(self):
        self.dockWidget = getConnectDockWidget()
        self.iface.addDockWidget(Qt.RightDockWidgetArea, self.dockWidget)
        self.dockWidget.hide()

        utils.setRepositoryUrl()

        self.actionRunWizard = self.dockWidget.toggleViewAction()
        self.actionRunWizard.setText('Boundless Connect')
        self.actionRunWizard.setIcon(
            QIcon(os.path.join(pluginPath, 'icons', 'connect.svg')))
        self.actionRunWizard.setWhatsThis('Boundless Connect')
        self.actionRunWizard.setObjectName('actionRunWizard')

        # If Boundless repository is a directory, add menu entry
        # to start modified Plugin Manager which works with local repositories
        if utils.isRepositoryInDirectory():
            self.actionPluginManager = QAction(
                'Manage plugins (local folder)', self.iface.mainWindow())
            self.actionPluginManager.setIcon(
                QIcon(os.path.join(pluginPath, 'icons', 'plugin.svg')))
            self.actionPluginManager.setWhatsThis(
                'Manage and install plugins from local repository')
            self.actionPluginManager.setObjectName('actionPluginManager')

            self.iface.addPluginToMenu(
                'Boundless Connect', self.actionPluginManager)

            self.actionPluginManager.triggered.connect(self.pluginManagerLocal)

        actions = self.iface.mainWindow().menuBar().actions()
        for action in actions:
            if action.menu().objectName() == 'mPluginMenu':
                menuPlugin = action.menu()
                separator = menuPlugin.actions()[1]
                menuPlugin.insertAction(separator, self.actionRunWizard)
                if utils.isRepositoryInDirectory():
                    menuPlugin.insertAction(separator, self.actionPluginManager)

        addSettingsMenu('Boundless Connect')
        addHelpMenu('Boundless Connect')
        addAboutMenu('Boundless Connect')

        # Enable check for updates if it is not enabled
        utils.addCheckForUpdates()

        try:
            from lessons import addLessonsFolder, addGroup
            folder = os.path.join(os.path.dirname(__file__), "_lessons")
            addLessonsFolder(folder, "boundlessconnect")
            group_description = os.path.join(folder, "group.md")
            addGroup("Boundless Connect plugin", group_description)
        except:
            pass

    def unload(self):
        actions = self.iface.mainWindow().menuBar().actions()
        for action in actions:
            if action.menu().objectName() == 'mPluginMenu':
                menuPlugin = action.menu()
                menuPlugin.removeAction(self.actionRunWizard)
                if utils.isRepositoryInDirectory():
                    menuPlugin.removeAction(self.actionPluginManager)

        removeSettingsMenu('Boundless Connect')
        removeHelpMenu('Boundless Connect')
        removeAboutMenu('Boundless Connect')

        self.dockWidget.hide()

        try:
            from boundlessconnect.tests import testerplugin
            from qgistester.tests import removeTestModule
            removeTestModule(testerplugin, 'Boundless Connect')
        except Exception as e:
            pass

        try:
            from lessons import removeLessonsFolder
            folder = os.path.join(pluginPath, '_lessons')
            removeLessonsFolder(folder)
        except:
            pass

    def checkFirstRun(self):
        settings = QSettings()
        firstRun = settings.value('boundlessconnect/firstRun', True, bool)
        settings.setValue('boundlessconnect/firstRun', False)

        if self.dockWidget is None:
            self.dockWidget = getConnectDockWidget()

        if firstRun:
            self.dockWidget.show()
            utils.installFromStandardPath()

        self.dockWidget.askForAuth = True

    def installPlugin(self):
        fileName = askForFiles(self.iface.mainWindow(),
                               'Open file',
                               exts='zip')

        if fileName is None:
            return

        result = utils.installFromZipFile(fileName)
        if result is None:
            self._showMessage('Plugin installed successfully',
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
