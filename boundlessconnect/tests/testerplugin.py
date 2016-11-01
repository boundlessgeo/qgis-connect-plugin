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
                                   'Close error message by pressing "No" button.'
                                   'Check that the "Level:" label is not found at the bottom of the Connect panel.',
                        prestep=lambda: _startConectPlugin(), isVerifyStep=True)

    repeatedLoginTest = Test("Check repeated logging")
    repeatedLoginTest.addStep('Accept dialog by pressing "Login" button without entering any credentials',
                        prestep=lambda: _startConectPlugin())
    repeatedLoginTest.addStep('Check that your subscription level is "Open"',
                        isVerifyStep=True)
    repeatedLoginTest.addStep('Click on the "Sign out" button')
    repeatedLoginTest.addStep('Login with valid credentials"')
    repeatedLoginTest.addStep('Check that your subscription level corresponds to the used credentials')

    emptySearchTest = Test("Check empty search")
    emptySearchTest.addStep('Accept dialog by pressing "Login" button without entering any credentials',
                        prestep=lambda: _startConectPlugin())
    emptySearchTest.addStep('Leave search box empty and press Enter. Verify that no results are shown and no error is thrown')

    searchTest = Test("Check normal search")
    searchTest.addStep('Accept dialog by pressing "Login" button without entering any credentials',
                        prestep=lambda: _startConectPlugin())
    searchTest.addStep('Type "MIL-STD-2525" in the search box and press Enter. Verify that one plugin result is shown',
                       isVerifyStep=True)
    searchTest.addStep('Type "gdal" in the search box and press Enter. Verify that a list of results is shown and pagination links ("next") are shown as well.',
                       isVerifyStep=True)
    searchTest.addStep('Verify that pagination links work')

    rolesDisplayTest = Test("Check roles display")
    rolesDisplayTest.addStep('Accept dialog by pressing "Login" button without entering any credentials',
                        prestep=lambda: _startConectPlugin())
    rolesDisplayTest.addStep('Type "MIL-STD-2525" in the search box and press Enter. Verify that one plugin result is shown and is not available (red)',
                       isVerifyStep=True)
    rolesDisplayTest.addStep('Click on "MIL-STD-2525" and verify it opens a browser where the user can subscribe to Boundless Connect',
                       isVerifyStep=True)
    rolesDisplayTest.addStep('Click on the "Sign out" button')
    rolesDisplayTest.addStep('Login with credentials for Desktop Enterprise"')
    rolesDisplayTest.addStep('Type "MIL-STD-2525" in the search box and press Enter. Verify that one plugin result is shown and is available (green)',
                       isVerifyStep=True)
    rolesDisplayTest.addStep('Click on "MIL-STD-2525" and verify it install the plugins or tells you that it is already installed',
                       isVerifyStep=True)

    wrongSearchTest = Test("Check wrong search")
    wrongSearchTest.addStep('Accept dialog by pressing "Login" button without entering any credentials',
                        prestep=lambda: _startConectPlugin())
    wrongSearchTest.addStep('Type "wrongsearch" in the search box and press Enter. Verify that a warning is displayed.',
                       isVerifyStep=True)

    helpTest = Test("Help test")
    helpTest.addStep('Click on "Help" button and verify help is correctly open in a browser.',
                        prestep=lambda: _startConectPlugin())

    toggleVisibilityTest = Test("Check visibility toggling")
    toggleVisibilityTest.addStep('Close Connect dock.',
                                 prestep=lambda: _startConectPlugin())
    toggleVisibilityTest.addStep('Open dock from menu "Plugins -> Boundless Connect". Verify that dock opened with active login screen.',
                                 isVerifyStep=True)
    toggleVisibilityTest.addStep('Close Connect dock.')
    toggleVisibilityTest.addStep('Right-click on QGIS toolbar and check "Boundless Connect" panel. Verify that dock opened with active login screen.',
                                 isVerifyStep=True)
    toggleVisibilityTest.addStep('Login by pressing "Login" (without entering credentials) button and then close dock.')
    toggleVisibilityTest.addStep('Open dock from menu "Plugins -> Boundless Connect". Verify that dock opened with active search screen.',
                                 isVerifyStep=True)
    toggleVisibilityTest.addStep('Close dock.')
    toggleVisibilityTest.addStep('Right-click on QGIS toolbar and check "Boundless Connect" panel. Verify that dock opened with active search screen.',
                                 isVerifyStep=True)

    return [invalidCredentialsTest, searchTest, emptySearchTest, repeatedLoginTest, wrongSearchTest, rolesDisplayTest, toggleVisibilityTest]


class SearchApiTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        loadPlugins()

    def testPluginsSearchResultsCorrectlyRetrieved(self):
        """Check that plugins search results correctly retrieved"""
        results = search("MIL-STD-2525")
        self.assertEqual(1, len(results))
        self.assertTrue(isinstance(results[0], ConnectPlugin))

    def testNonPluginsSearchResultsCorrectlyRetrieved(self):
        """Check that non-plugins search results correctly retrieved"""
        results = search("gdal")
        self.assertEqual(20, len(results))
        results2 = search("gdal", 1)
        self.assertEqual(20, len(results))
        self.assertNotEqual(results, results2)

    def testEmptySearch(self):
        "Check that empty search string returns empty results"
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
