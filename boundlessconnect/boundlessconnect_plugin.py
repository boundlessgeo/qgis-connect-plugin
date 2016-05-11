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

from qgis.core import QGis
from qgis.gui import QgsMessageBar, QgsMessageBarItem

from pyplugin_installer.installer_data import (repositories,
                                               plugins)

from boundlessconnect.gui.firstrunwizard import FirstRunWizard
from boundlessconnect import utils

pluginPath = os.path.dirname(__file__)


class BoundlessConnectPlugin:
    def __init__(self, iface):
        self.iface = iface

        try:
            from boundlessconnect.tests import testerplugin
            from qgistester.tests import addTestModule
            addTestModule(testerplugin, 'Boundless Connect')
        except:
            pass

        self.qgsVersion = unicode(QGis.QGIS_VERSION_INT)

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
        if int(self.qgsVersion) < 20800:
            qgisVersion = '{}.{}.{}'.format(
                self.qgsVersion[0], self.qgsVersion[2], self.qgsVersion[3])
            QMessageBox.warning(
                self.iface.mainWindow(),
                self.tr('Boundless Connect'),
                self.tr('QGIS {} detected.\nThis version of  Boundless '
                        'Connect plugin requires at least QGIS 2.8.0. '
                        'Plugin will not be enabled.'.format(qgisVersion)))
            return None

        self.actionRunWizard = QAction(
            self.tr('First Run wizard'), self.iface.mainWindow())
        self.actionRunWizard.setIcon(
            QIcon(os.path.join(pluginPath, 'icons', 'boundless.png')))
        self.actionRunWizard.setWhatsThis(
            self.tr('Run wizard to perform post-installation setup'))
        self.actionRunWizard.setObjectName('actionRunWizard')

        self.actionPluginFromZip = QAction(
            self.tr('Install plugin from ZIP'), self.iface.mainWindow())
        self.actionPluginFromZip.setIcon(
            QIcon(os.path.join(pluginPath, 'icons', 'plugin.png')))
        self.actionPluginFromZip.setWhatsThis(
            self.tr('Install plugin from ZIP file stored on disk'))
        self.actionPluginFromZip.setObjectName('actionPluginFromZip')

        self.iface.addPluginToMenu(
            self.tr('Boundless Connect'), self.actionRunWizard)
        self.iface.addPluginToMenu(
            self.tr('Boundless Connect'), self.actionPluginFromZip)

        self.actionRunWizard.triggered.connect(self.runWizardAndProcessResults)
        self.actionPluginFromZip.triggered.connect(self.installPlugin)

        # If Boundless repository is a directory, add menu entry
        # to start modified Plugin Manager which works with local repositorys
        if utils.isRepositoryInDirectory():
            self.actionPluginManager = QAction(
                self.tr('Manage plugins (local folder)'), self.iface.mainWindow())
            self.actionPluginManager.setIcon(
                QIcon(os.path.join(pluginPath, 'icons', 'plugin.png')))
            self.actionPluginManager.setWhatsThis(
                self.tr('Manage and install plugins from local repository'))
            self.actionPluginManager.setObjectName('actionPluginManager')

            self.iface.addPluginToMenu(
                self.tr('Boundless Connect'), self.actionPluginManager)

            self.actionPluginManager.triggered.connect(self.pluginManagerLocal)

        # Add Boundless plugin repository to list of the available
        # plugin repositories if it is not presented here
        utils.addBoundlessRepository()

    def unload(self):
        self.iface.removePluginMenu(
            self.tr('Boundless Connect'), self.actionRunWizard)
        self.iface.removePluginMenu(
            self.tr('Boundless Connect'), self.actionPluginFromZip)

        if utils.isRepositoryInDirectory():
            self.iface.removePluginMenu(
                self.tr('Boundless Connect'), self.actionPluginManager)

    def startFirstRunWizard(self):
        settings = QSettings('Boundless', 'BoundlessConnect')
        version = utils.connectVersion()
        firstRun = settings.value('firstRun' + version, True, bool)
        settings.setValue('firstRun' + version, False)

        if not firstRun:
            # check repositories in background
            repositories.load()
            repositories.checkingDone.connect(self.checkingDone)
            for key in repositories.allEnabled():
                repositories.requestFetching(key)
            return

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
        wzrd = FirstRunWizard()
        if wzrd.exec_():
            installAll = wzrd.mPagePlugins.rbAutoInstall.isChecked()

            if installAll:
                utils.installAllPlugins()
            else:
                boundlessOnly = wzrd.mPagePlugins.rbManualInstallBoundless.isChecked()
                utils.showPluginManager(boundlessOnly)

            utils.installFromStandardPath()

            self._showMessage(
                self.tr('Boundless Connect is done configuring your QGIS.'),
                QgsMessageBar.SUCCESS)

    def checkingDone(self):
        updateNeeded, allInstalled = utils.checkPluginsStatus()
        print 'STATUS CHECKED'

        res = utils.upgradeConnect()
        if res != '':
            self._showMessage(res)
            return

        if allInstalled and not updateNeeded:
            self._showMessage(self.tr('You are up to date with Boundless plugins'))
        elif allInstalled and updateNeeded:
            self.btnUpdateAll = QPushButton(self.tr('Update'))
            self.btnUpdateAll.clicked.connect(utils.installAllPlugins)
            self.btnUpdateAll.clicked.connect(self.iface.messageBar().popWidget)

            updateMsg = QgsMessageBarItem(self.tr('Update plugins'),
                                          self.tr('Some of your plugins need '
                                                  'to be updated. Update them '
                                                  'automatically now?'),
                                          self.btnUpdateAll,
                                          QgsMessageBar.INFO,
                                          0,
                                          self.iface.messageBar()
                                          )
            self.iface.messageBar().pushItem(updateMsg)
        elif not allInstalled and updateNeeded:
            self._showMessage(self.tr('Some of your Boundless plugins need to be updated'))

    def _showMessage(self, message, level=QgsMessageBar.INFO):
        self.iface.messageBar().pushMessage(
            message, level, self.iface.messageTimeout())

    def tr(self, text):
        return QCoreApplication.translate('Boundless Connect', text)
