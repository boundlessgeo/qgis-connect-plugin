# -*- coding: utf-8 -*-

"""
***************************************************************************
    testerplugin.py
    ---------------------
    Date                 : March 2016
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
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import sys
import json
import unittest
import ConfigParser

from PyQt4.QtCore import Qt, QSettings

from qgis.core import QgsApplication

from qgis.utils import active_plugins, home_plugin_path, unloadPlugin, iface
from pyplugin_installer.installer import QgsPluginInstaller
from pyplugin_installer.installer_data import reposGroup, plugins, removeDir

#from boundlessconnect.gui.connectdialog import ConnectDialog
from boundlessconnect.gui.connectdockwidget import ConnectDockWidget

from boundlessconnect.plugins import boundlessRepoName, repoUrlFile
from boundlessconnect import utils

testPath = os.path.dirname(__file__)

dock = None
originalVersion = None
installedPlugins = []

def functionalTests():
    try:
        from qgistester.test import Test
    except:
        return []

    openPluginManagerBoundlessOnlyTest = Test('Verify that Boundless Connect can start Plugin Manager only with Boundless plugins')
    openPluginManagerBoundlessOnlyTest.addStep('Check that Plugin manager is open and contains only Boundless plugins',
                                prestep=lambda: _openPluginManager(True), isVerifyStep=True)

    invalidCredentialsTest = Test('Check Connect plugin recognize invalid credentials')
    invalidCredentialsTest.addStep('Enter invalid Connect credentials and accept dialog by pressing "Login" button. '
                                   'Check that Connect shows error message complaining about invalid credentials.'
                                   'Close error message by pressing "No" button.',
                        prestep=lambda: _startConectPlugin(), isVerifyStep=True)
    invalidCredentialsTest.addStep('Check that Boundless repo added to Plugin Manager and has no auth config associated with it',
                        prestep=lambda: _openPluginManager(False), isVerifyStep=True)

    connectTest = Test('Check Connect plugin write repo URL and authid')
    connectTest.addStep('Accept dialog by pressing "Login" button',
                        prestep=lambda: _startConectPlugin())
    connectTest.addStep('Check that Boundless repo added to Plugin Manager and has no auth config associated with it',
                        prestep=lambda: _openPluginManager(False), isVerifyStep=True)
    connectTest.addStep('Enter valid Connect credentials and accept dialog by pressing "Login" button',
                        prestep=lambda: _startConectPlugin())
    connectTest.addStep('Check that Boundless repo added to Plugin Manager and has associated auth config',
                        prestep=lambda: _openPluginManager(False), isVerifyStep=True)

    return [connectTest, invalidCredentialsTest, openPluginManagerBoundlessOnlyTest]


class BoundlessConnectTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global installedPlugins
        installedPlugins[:] = []
        for key in plugins.all():
            if utils.isBoundlessPlugin(plugins.all()[key]) and plugins.all()[key]['installed']:
                installedPlugins.append(key)

    def testInstallFromZip(self):
        """Test plugin installation from ZIP package"""
        pluginPath = os.path.join(testPath, 'data', 'connecttest.zip')
        result = utils.installFromZipFile(pluginPath)
        self.assertIsNone(result), 'Error installing plugin: {}'.format(result)
        self.assertTrue('connecttest' in active_plugins), 'Plugin not activated'

        unloadPlugin('connecttest')
        result = removeDir(os.path.join(home_plugin_path, 'connecttest'))
        self.assertFalse(result), 'Plugin directory not removed'
        result = utils.installFromZipFile(pluginPath)
        self.assertIsNone(result), 'Error installing plugin: {}'.format(result)
        self.assertTrue('connecttest' in active_plugins), 'Plugin not activated after reinstallation'

    def testIsBoundlessCheck(self):
        """Test that Connect detects Boundless plugins"""
        with open(os.path.join(testPath, 'data', 'samplepluginsdict.json')) as f:
            pluginsDict = json.load(f)
        count = len([key for key in pluginsDict if utils.isBoundlessPlugin(pluginsDict[key])])
        self.assertEqual(8, count)

    def testCustomRepoUrl(self):
        """Test that Connect read custom repository URL and apply it"""
        settings = QSettings('Boundless', 'BoundlessConnect')
        oldRepoUrl = settings.value('repoUrl', '', unicode)

        settings.setValue('repoUrl', 'test')
        self.assertEqual('test', settings.value('repoUrl'))

        fName = os.path.join(QgsApplication.qgisSettingsDirPath(), repoUrlFile)
        with open(fName, 'w') as f:
            f.write('[general]\nrepoUrl=http://dummyurl.com')
        utils.setRepositoryUrl()

        self.assertTrue('http://dummyurl.com', settings.value('repoUrl', '', unicode))
        settings.setValue('repoUrl', oldRepoUrl)

    @classmethod
    def tearDownClass(cls):
        # Remove installed HelloWorld plugin
        installer = QgsPluginInstaller()
        if 'connecttest' in active_plugins:
            installer.uninstallPlugin('connecttest', quiet=True)

        # Also remove other installed plugins
        global installedPlugins
        for key in plugins.all():
            if key == 'boundlessconnect':
                continue
            if utils.isBoundlessPlugin(plugins.all()[key]) and key not in installedPlugins:
                installer.uninstallPlugin(key, quiet=True)


def unitTests():
    connectSuite = unittest.makeSuite(BoundlessConnectTests, 'test')
    _tests = []
    _tests.extend(connectSuite)

    return _tests


def _openPluginManager(boundlessOnly=False):
    utils.showPluginManager(boundlessOnly)


def _downgradePlugin(pluginName, corePlugin=True):
    if corePlugin:
        metadataPath = os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins', pluginName, 'metadata.txt')
    else:
        metadataPath = os.path.join(QgsApplication.qgisSettingsDirPath()(), 'python', 'plugins', pluginName, 'metadata.txt')

    cfg = ConfigParser.SafeConfigParser()
    cfg.read(metadataPath)
    global originalVersion
    originalVersion = cfg.get('general', 'version')
    cfg.set('general', 'version', '0.0.1')
    with open(metadataPath, 'wb') as f:
        cfg.write(f)


def _restoreVersion(pluginName, corePlugin=True):
    if corePlugin:
        metadataPath = os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins', pluginName, 'metadata.txt')
    else:
        metadataPath = os.path.join(QgsApplication.qgisSettingsDirPath()(), 'python', 'plugins', pluginName, 'metadata.txt')

    cfg = ConfigParser.SafeConfigParser()
    cfg.read(metadataPath)
    global originalVersion
    cfg.set('general', 'version', originalVersion)
    with open(metadataPath, 'wb') as f:
        cfg.write(f)

    originalVersion = None


def _startConectPlugin():
    global dock
    if dock is None:
        dock = ConnectDockWidget()
    iface.addDockWidget(Qt.RightDockWidgetArea, dock)
    dock.show()


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(BoundlessConnectTests, 'test'))
    return suite


def run_tests():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(suite())
