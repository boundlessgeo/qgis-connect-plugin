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
from boundlessconnect.gui.connectdockwidget import getConnectDockWidget
from boundlessconnect.connect import search, ConnectPlugin, loadPlugins

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

    invalidCredentialsTest = Test('Check Connect plugin recognize invalid credentials')
    invalidCredentialsTest.addStep('Enter invalid Connect credentials and accept dialog by pressing "Login" button. '
                                   'Check that Connect shows error message complaining about invalid credentials.'
                                   'Close error message by pressing "No" button.',
                        prestep=lambda: _startConectPlugin(), isVerifyStep=True)
  
    repeatedLoginTest = Test("Check repeated logging")
    repeatedLoginTest.addStep('Accept dialog by pressing "Login" button',
                        prestep=lambda: _startConectPlugin())
    repeatedLoginTest.addStep('Check that your subscription level is "Open"',
                        isVerifyStep=True)
    repeatedLoginTest.addStep('Click on the "log out" button')
    repeatedLoginTest.addStep('Login with valid credentials"')
    repeatedLoginTest.addStep('Check that your subscription level corresponds to the used credentials')

    emptySearchTest = Test("Check empty search")
    emptySearchTest.addStep('Accept dialog by pressing "Login" button',
                        prestep=lambda: _startConectPlugin())
    emptySearchTest.addStep('Click the "Search" button leaving the search text box empty. Verify that no results are shown and no error is thrown')
    
    searchTest = Test("Check normal search")
    searchTest.addStep('Accept dialog by pressing "Login" button',
                        prestep=lambda: _startConectPlugin())
    searchTest.addStep('Type "MIL" in the search box and click the "Search" button. Verify that two results are shown: 1 plugin and 1 documentation item')
    
    return [invalidCredentialsTest, searchTest, emptySearchTest, repeatedLoginTest]


class SearchApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        loadPlugins()

    def testPluginsSearchResultsCorrectlyRetrieved(self):
        results = search("MIL-STD-2525")
        self.assertEqual(1, len(results))
        self.assertTrue(isinstance(results[0], ConnectPlugin))

    def testNonPluginsSearchResultsCorrectlyRetrieved(self):
        results = search("MIL-STD-2525")
        self.assertEqual(2, len(results))
        self.assertTrue(isinstance(results[1], ConnectPlugin))
        self.assertTrue(isinstance(results[0], ConnectDocumentation))

    def testEmptySearch(self):
        results = search("")
        self.assertEqual(0, len(results))


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
    apiSuite = unittest.makeSuite(SearchApiTests, 'test')
    _tests = []
    _tests.extend(connectSuite)
    _tests.extend(apiSuite)

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
    dock = getConnectDockWidget()
    iface.addDockWidget(Qt.RightDockWidgetArea, dock)
    dock.show()
    dock.showLogin()


def suite():
    suite = unittest.TestSuite()
    suite.addTests(unittest.makeSuite(BoundlessConnectTests, 'test'))
    return suite


def run_tests():
    unittest.TextTestRunner(verbosity=3, stream=sys.stdout).run(suite())
