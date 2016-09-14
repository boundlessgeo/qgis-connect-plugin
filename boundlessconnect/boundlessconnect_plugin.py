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

__author__ = 'Alexander Bruy'
__date__ = 'February 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from PyQt4.QtCore import (QCoreApplication,
                          QSettings,
                          QLocale,
                          QTranslator,
                          QFileInfo)
from PyQt4.QtGui import (QMessageBox,
                         QAction,
                         QIcon,
                         QFileDialog,
                         QPushButton)

from qgis.gui import QgsMessageBar, QgsMessageBarItem

from pyplugin_installer.installer_data import (repositories,
                                               plugins)

from boundlessconnect.gui.connectdialog import ConnectDialog
from boundlessconnect import utils

pluginPath = os.path.dirname(__file__)


class BoundlessConnectPlugin:
    def __init__(self, iface):
        self.iface = iface

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

        self.iface.initializationCompleted.connect(self.startFirstRunWizard)

    def initGui(self):
        self.actionRunWizard = QAction(
            self.tr('Boundless Connect Login'), self.iface.mainWindow())
        self.actionRunWizard.setIcon(
            QIcon(os.path.join(pluginPath, 'icons', 'connect.svg')))
        self.actionRunWizard.setWhatsThis(
            self.tr('Login to Boundless Connect'))
        self.actionRunWizard.setObjectName('actionRunWizard')

        self.actionPluginFromZip = QAction(
            self.tr('Install plugin from ZIP'), self.iface.mainWindow())
        self.actionPluginFromZip.setIcon(
            QIcon(os.path.join(pluginPath, 'icons', 'plugin.svg')))
        self.actionPluginFromZip.setWhatsThis(
            self.tr('Install plugin from ZIP file stored on disk'))
        self.actionPluginFromZip.setObjectName('actionPluginFromZip')

        self.actionRunWizard.triggered.connect(self.runWizardAndProcessResults)
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

        # Add Boundless plugin repository to list of the available
        # plugin repositories if it is not presented here
        #utils.addBoundlessRepository()

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


        try:
            from boundlessconnect.tests import testerplugin
            from qgistester.tests import removeTestModule
            removeTestModule(testerplugin, 'Boundless Connect')
        except Exception as e:
            pass

    def startFirstRunWizard(self):
        settings = QSettings('Boundless', 'BoundlessConnect')
        version = utils.connectVersion()
        firstRun = settings.value('firstRun' + version, True, bool)
        settings.setValue('firstRun' + version, False)

        if firstRun:
            self.runWizardAndProcessResults()

    def installPlugin(self):
        settings = QSettings('Boundless', 'BoundlessConnect')
        lastDirectory = settings.value('lastPluginDirectory', '.')

        fileName = QFileDialog.getOpenFileName(self.iface.mainWindow(),
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

    def runWizardAndProcessResults(self):
        dlg = ConnectDialog()
        if dlg.exec_():
            utils.showPluginManager(True)

            utils.installFromStandardPath()

            self._showMessage(
                self.tr('Boundless Connect is done configuring your QGIS.'),
                QgsMessageBar.SUCCESS)

    def checkingDone(self):
        updateNeeded, allInstalled = utils.checkPluginsStatus()

        res = utils.upgradeConnect()
        if res != '':
            self._showMessage(res)
            return

        if allInstalled and not updateNeeded:
            self._showMessage(self.tr('You are up to date with Boundless plugins'))
        elif updateNeeded:
            self.btnUpdate = QPushButton(self.tr('Update'))
            self.btnUpdate.clicked.connect(utils.upgradeInstalledPlugins)
            self.btnUpdate.clicked.connect(self.iface.messageBar().popWidget)

            updateMsg = QgsMessageBarItem(self.tr('Update plugins'),
                                          self.tr('Some Boundless plugins need '
                                                  'to be updated. Update them now?'),
                                          self.btnUpdate,
                                          QgsMessageBar.INFO,
                                          0,
                                          self.iface.messageBar()
                                          )
            self.iface.messageBar().pushItem(updateMsg)

    def _showMessage(self, message, level=QgsMessageBar.INFO):
        self.iface.messageBar().pushMessage(
            message, level, self.iface.messageTimeout())

    def tr(self, text):
        return QCoreApplication.translate('Boundless Connect', text)
