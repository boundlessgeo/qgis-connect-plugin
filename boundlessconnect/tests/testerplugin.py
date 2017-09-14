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
from future import standard_library
standard_library.install_aliases()

__author__ = 'Alexander Bruy'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import re
import os
import sys
import json
import unittest
import tempfile

try:
    from configparser import ConfigParser
except:
    from ConfigParser import ConfigParser

from qgis.PyQt.QtCore import Qt, QFileInfo

from qgis.core import QgsApplication, QgsProject
from qgis.utils import home_plugin_path, unloadPlugin, iface
from qgis import utils as qgsutils

from pyplugin_installer.installer import QgsPluginInstaller
from pyplugin_installer.installer_data import reposGroup, plugins, removeDir

from qgiscommons2.network.oauth2 import oauth2_supported
from qgiscommons2.settings import pluginSetting, setPluginSetting

from boundlessconnect.gui.connectdockwidget import getConnectDockWidget
from boundlessconnect.connect import search, ConnectPlugin, loadPlugins

from boundlessconnect.plugins import boundlessRepoName, repoUrlFile
from boundlessconnect import utils
from boundlessconnect import basemaputils

testPath = os.path.dirname(__file__)

dock = None
originalVersion = None
installedPlugins = []

def functionalTests():
    try:
        from qgistester.test import Test
    except:
        return []

    emptyCredentialsTest = Test('Check Connect plugin recognize empty credentials')
    emptyCredentialsTest.addStep('Press "Login" button without entering any credentials. '
                                 'Check that Connect shows error message complaining about empty credentials.'
                                 'Close error message by pressing "Ok" button.'
                                 'Check that the Connect panel shows login page.',
                                 prestep=lambda: _startConectPlugin(),
                                 isVerifyStep=True)

    invalidCredentialsTest = Test('Check Connect plugin recognize invalid credentials')
    invalidCredentialsTest.addStep('Enter invalid Connect credentials and accept dialog by pressing "Login" button. '
                                   'Check that dialog asking for credentials is shown and close it by pressing "Cancel" button. '
                                   'Check that Connect shows error message complaining about invalid credentials. '
                                   'Close error message by pressing "Ok" button. '
                                   'Check that the Connect panel shows login page.',
                                   prestep=lambda: _startConectPlugin(),
                                   isVerifyStep=True)

    invalidEndpointTest = Test('Check login with wrong endpoint')
    invalidEndpointTest.addStep('Open plugin settings from "PLugins -> Boundless Connect -> Plugin Settings" menu. '
                                'Enter "https://dummy.com" as Connect endpoint and close dialog by pressing OK.')
    invalidEndpointTest.addStep('Enter valid Connect credentials and press "Login" button. Verify that error '
                                'message about token is shown and login page is active.',
                                prestep=lambda: _startConectPlugin(),
                                isVerifyStep=True)

    repeatedLoginTest = Test("Check repeated logging")
    repeatedLoginTest.addStep('Enter valid Connect credentials, check "Remember me" '
                              'checkbox and press "Login" button.',
                              prestep=lambda: _startConectPlugin())
    repeatedLoginTest.addStep('Check that label with your login info '
                              'is shown in the lower part of the Connect panel.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Click on the "Logout" button')
    repeatedLoginTest.addStep('Verify that login and password fields are '
                              'filled with login and password you used at '
                              'the previous login and "Remember me" checkbox '
                              'is checked.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Enter another another valid credentials and '
                              'keep "Remember me" checkbox checked. Press '
                              '"Login" button.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Check that in the lower part of Connect '
                              'plugin, correct login name is displayed.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Click on the "Logout" button')
    repeatedLoginTest.addStep('Verify that login and password fields are '
                              'filled with login and password you used at '
                              'the previous login and "Remember me" checkbox '
                              'is checked.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Close Connect dock.')
    repeatedLoginTest.addStep('Open Connect dock from "Plugins -> Boundless Connect" '
                              'menu. Verify that login and password fields are '
                              'filled with login and password you used at '
                              'the previous login',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Uncheck "Remember me" checkbox and press '
                              '"Login" button.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Check that in the lower part of Connect '
                              'plugin, correct login name is displayed.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Click on the "Logout" button')
    repeatedLoginTest.addStep('Verify that login and password fields are '
                              'empty and "Remember me" checkbox is unchecked.',
                              isVerifyStep=True)
    repeatedLoginTest.addStep('Close Connect dock.')
    repeatedLoginTest.addStep('Open Connect dock from "Plugins -> Boundless Connect" '
                              'menu. Verify that login and password fields are '
                              'empty and "Remember me" checkbox is unchecked.',
                              isVerifyStep=True)

    emptySearchTest = Test("Check empty search")
    emptySearchTest.addStep('Enter valid Connect credentials and press "Login" button.',
                            prestep=lambda: _startConectPlugin())
    emptySearchTest.addStep('Verify that "Knowledge" tab is shown, '
                            'populated with content and no error is thrown',
                            isVerifyStep=True)
    emptySearchTest.addStep('Switch to the "Data" tab. Verify that '
                            'some results are shown and no error is thrown',
                            isVerifyStep=True)
    emptySearchTest.addStep('Switch to the "Plugins" tab. Verify that '
                            'some results are shown and no error is thrown',
                            isVerifyStep=True)
    emptySearchTest.addStep('Type "mapbox" in the search box and Switch '
                            'to the "Knowledge" tab. Verify that some '
                            'results are shown and no error is thrown',
                            isVerifyStep=True)
    emptySearchTest.addStep('Switch to the "Plugins" tab. Verify that no '
                            'results are shown and no error is thrown',
                            isVerifyStep=True)
    emptySearchTest.addStep('Clear search field and switch to the "Data" '
                            'tab. Verify that some results are shown and '
                            'no error is thrown',
                            isVerifyStep=True)

    searchTest = Test("Check normal search")
    searchTest.addStep('Enter valid Connect credentials and press "Login" button.',
                       prestep=lambda: _startConectPlugin())
    searchTest.addStep('Verify that "Knowledge" tab is shown, '
                       'populated with content and no error is thrown',
                       isVerifyStep=True)
    searchTest.addStep('Type "gdal" in the search box and press Enter. '
                       'Verify that a list of results is shown.',
                       isVerifyStep=True)
    searchTest.addStep('Type "lesson" in the search box and switch '
                       'to the "Plugins" tab. Verify that one plugin result is shown.',
                       isVerifyStep=True)
    searchTest.addStep('Type "mapbox" in the search box and switch '
                       'to the "Data" tab. Verify that a list of results is shown.',
                       isVerifyStep=True)

    paginationTest = Test("Check normal search")
    paginationTest.addStep('Enter valid Connect credentials and press "Login" button.',
                           prestep=lambda: _startConectPlugin())
    paginationTest.addStep('Verify that "Knowledge" tab is shown, '
                           'populated with content and no error is thrown',
                           isVerifyStep=True)
    paginationTest.addStep('Type "geogig" in the search box and press Enter. '
                           'Verify that a list of results is shown and there is'
                           'a "Next" button at the bottom',
                           isVerifyStep=True)
    paginationTest.addStep('Click on the "Next" button. Verify that new '
                           'results are loaded and at the bottom there are '
                           'two buttons: "Next" and "Previous"',
                           isVerifyStep=True)
    paginationTest.addStep('Continue clicking on the "Next" button until '
                           'last page loaded. Verify that only "Previous" '
                           'is shown at the bottom of the results list',
                            isVerifyStep=True)
    paginationTest.addStep('Click on the "Previous" button. Verify that '
                           'new you returned to the previous page.',
                           isVerifyStep=True)
    paginationTest.addStep('Continue clicking on the "Previous" button until '
                           'first page loaded. Verify that only "Next" '
                           'is shown at the bottom of the results list',
                            isVerifyStep=True)

    wrongSearchTest = Test("Check wrong search")
    wrongSearchTest.addStep('Enter valid Connect credentials and press "Login" button.',
                            prestep=lambda: _startConectPlugin())
    wrongSearchTest.addStep('Verify that "Knowledge" tab is shown, '
                            'populated with content and no error is thrown',
                            isVerifyStep=True)
    wrongSearchTest.addStep('Type "wrongsearch" in the search box and '
                            'press Enter. Verify that a warning is displayed.',
                            isVerifyStep=True)

    categorySearchTest = Test("Check search by categories")
    categorySearchTest.addStep('Enter valid Connect credentials and press "Login" button.',
                               prestep=lambda: _startConectPlugin())
    categorySearchTest.addStep('Verify that "Knowledge" tab is shown, '
                               'populated with content and no error is thrown',
                               isVerifyStep=True)
    categorySearchTest.addStep('Type "MIL-STD-2525" in the search box and '
                               'ensure no category is selected in "Search in" '
                               'combobox. Press Enter. Verify that multiple '
                               'results are shown and they are from '
                               'different categories.',
                               isVerifyStep=True)
    categorySearchTest.addStep('Type "style" in the search box and in '
                               'the "Search in" combobox select "Lesson" '
                               'and deselect any other items. '
                               'Click on the "Search" button again and '
                               'check that only lessons results are shown',
                               isVerifyStep=True)
    categorySearchTest.addStep('In the "Search in" combobox additionaly '
                               'select "Learning". Click on the "Search" '
                               'button again and check that multiple results '
                               'are shown: lesson and learning center content.',
                               isVerifyStep=True)

    pluginSearchTest = Test("Check that plugins search results correctly retrieved")
    pluginSearchTest.addStep('Login with valid Connect credentials',
                             prestep=lambda: _startConectPlugin())
    pluginSearchTest.addStep('Verify that "Knowledge" tab is shown, '
                             'populated with content and no error is thrown',
                             isVerifyStep=True)
    pluginSearchTest.addStep('Switch to the "Plugins" tab, type '
                             '"MIL-STD-2525" in the search field '
                             'and press search button')
    pluginSearchTest.addStep('Verify that single plugin result returned.',
                             isVerifyStep=True)

    rolesDisplayTest = Test("Check roles display")
    rolesDisplayTest.addStep('Enter valid (non-enterprise) Connect credentials and press "Login" button.',
                             prestep=lambda: _startConectPlugin())
    rolesDisplayTest.addStep('Verify that "Knowledge" tab is shown, '
                             'populated with content and no error is thrown',
                             isVerifyStep=True)
    rolesDisplayTest.addStep('Switch to the "Plugin" tab. Type '
                             '"MIL-STD-2525" in the search box and '
                             'press Enter. Verify that one plugin result '
                             'is shown and is not available (orange)',
                             isVerifyStep=True)
    rolesDisplayTest.addStep('Click on "MIL-STD-2525" and verify it '
                             'opens a browser where the user can '
                             'subscribe to Boundless Connect',
                             isVerifyStep=True)
    rolesDisplayTest.addStep('Click on the "Logout" button')
    rolesDisplayTest.addStep('Login with credentials for "Desktop Enterprise"')
    rolesDisplayTest.addStep('Verify that "Knowledge" tab is shown, '
                             'populated with content and no error is thrown',
                             isVerifyStep=True)
    rolesDisplayTest.addStep('Switch to the "Plugin" tab. Type '
                             '"MIL-STD-2525" in the search box and '
                             'press Enter. Verify that one plugin result '
                             'is shown and is available (blue)',
                             isVerifyStep=True)
    rolesDisplayTest.addStep('Click on "MIL-STD-2525" and verify it '
                             'install the plugins or tells you that it '
                             'is already installed',
                             isVerifyStep=True)

    basemapsLoadingTest = Test("Check basemaps loading")
    basemapsLoadingTest.addStep('Login with credentials for "Desktop Enterprise".',
                                prestep=lambda: _startConectPlugin())
    basemapsLoadingTest.addStep('Verify that "Knowledge" tab is shown, '
                                'populated with content and no error is thrown',
                                isVerifyStep=True)
    basemapsLoadingTest.addStep('Type "mapbox" in the search box and '
                                'switch to the "Data" tab. Verify that '
                                'list of the basemaps shown.',
                                isVerifyStep=True)
    basemapsLoadingTest.addStep('Press "ADD TO MAP" button under any '
                                'basemap and verify that basemap added '
                                'to the current project and no error is thrown.',
                                isVerifyStep=True)
    basemapsLoadingTest.addStep('Pan canvas in different directions, '
                                'zoom in and out to ensure that basemap '
                                'is working correctly and no error is thrown.',
                                isVerifyStep=True)
    basemapsLoadingTest.addStep('Press "ADD TO MAP" button under another '
                                'basemap from the search results and '
                                'verify that second basemap added to '
                                'the current project and no error is thrown.',
                                isVerifyStep=True)
    basemapsLoadingTest.addStep('Pan canvas in different directions, '
                                'zoom in and out to ensure that basemap '
                                'is working correctly and no error is thrown.',
                                isVerifyStep=True)
    basemapsLoadingTest.addStep('Change visibility of both basemaps, '
                                'reorder them in the layer tree to '
                                'ensure that they are working correctly '
                                'and no error is thrown.',
                                isVerifyStep=True)

    defaultProjectTest = Test("Check simple default project")
    defaultProjectTest.addStep('Login with credentials for "Desktop Enterprise".',
                                prestep=lambda: _startConectPlugin())
    defaultProjectTest.addStep('Switch to the "Data" tab. Type "mapbox" '
                                'in the search box and press Enter. '
                                'Verify that list of the basemaps shown.',
                                isVerifyStep=True)
    defaultProjectTest.addStep('Press "ADD TO DEFAULT PROJECT" button '
                               'under any basemap and verify that '
                               'message saying it was added to the '
                               'default project shown and no error '
                               'is thrown.',
                                isVerifyStep=True)
    defaultProjectTest.addStep('Press "New project" button at the QGIS '
                               'toolbar and verify new project with '
                               'basemap added by default created.',
                                isVerifyStep=True)
    defaultProjectTest.addStep('Change visibility of basemap, zoom in '
                               'and out, pan acros the map to ensure '
                               'that it works correctly and no error '
                               'is thrown.',
                                isVerifyStep=True)
    defaultProjectTest.addStep('Unset default project',
                               function=lambda: basemaputils.unsetDefaultProject())

    complexDefaultProjectTest = Test("Check complex default project")
    complexDefaultProjectTest.addStep('Login with credentials for "Desktop Enterprise".',
                                      prestep=lambda: _startConectPlugin())
    complexDefaultProjectTest.addStep('Switch to the "Data" tab. Type "mapbox" '
                                      'in the search box and press Enter. '
                                      'Verify that list of the basemaps shown.',
                                      isVerifyStep=True)
    complexDefaultProjectTest.addStep('Press "ADD TO DEFAULT PROJECT" button '
                                      'under any basemap and verify that '
                                      'message saying it was added to the '
                                      'default project shown and no error '
                                      'is thrown.',
                                      isVerifyStep=True)
    complexDefaultProjectTest.addStep('Press "ADD TO DEFAULT PROJECT" button '
                                      'under another basemap and verify that '
                                      'message saying it was added to the '
                                      'default project shown and no error '
                                      'is thrown.',
                                      isVerifyStep=True)
    complexDefaultProjectTest.addStep('Press "New project" button at the QGIS '
                                      'toolbar and verify new project with '
                                      'two basemaps added by default created.',
                                      isVerifyStep=True)
    complexDefaultProjectTest.addStep('Change visibility of basemap, '
                                      'reorder them in layer tree, zoom in '
                                      'and out, pan acros the map to ensure '
                                      'that it works correctly and no error '
                                      'is thrown.',
                                      isVerifyStep=True)
    complexDefaultProjectTest.addStep('Unset default project',
                                      function=lambda: basemaputils.unsetDefaultProject())

    lessonsInstallTest = Test("Check lessons installation")
    lessonsInstallTest.addStep('Login with credentials for "Desktop Enterprise".',
                               prestep=lambda: _startConectPlugin())
    lessonsInstallTest.addStep('Switch to the "Plugins" tab. Type "lessons" '
                               'in the search box and press Enter. '
                               'Verify that single plugin result is '
                               'shown and available for installation '
                               '(button color is blue).',
                               isVerifyStep=True)
    lessonsInstallTest.addStep('Press "INSTALL" button and verify that '
                               'plugin installed, activated and no error '
                               'is thrown.',
                               isVerifyStep=True)
    lessonsInstallTest.addStep('Switch to the "Knowledge" tab, enter '
                               '"lesson" in the search box and select '
                               '"Lessons" from the "Search in" combobox. '
                               'Press Enter to perform search, verify '
                               'that lessons results are shown and no '
                               'available (buttons are blue) and no '
                               'error is thrown.',
                               isVerifyStep=True)
    lessonsInstallTest.addStep('Press "LESSON" button under any lesson '
                               'result and verify that lessons installed, '
                               'activated and no error is thrown.',
                               isVerifyStep=True)

    helpTest = Test("Check Help displaying")
    helpTest.addStep('Click on "Help" button and verify help is '
                     'correctly open in a browser.',
                     prestep=lambda: _startConectPlugin())

    toggleVisibilityTest = Test("Check visibility toggling")
    toggleVisibilityTest.addStep('Close Connect dock.',
                                 prestep=lambda: _startConectPlugin())
    toggleVisibilityTest.addStep('Open dock from menu "Plugins -> Boundless '
                                 'Connect". Verify that dock opened with '
                                 'active login screen.',
                                 isVerifyStep=True)
    toggleVisibilityTest.addStep('Close Connect dock.')
    toggleVisibilityTest.addStep('Right-click on QGIS toolbar and check '
                                 '"Boundless Connect" panel. Verify that '
                                 'dock opened with active login screen.',
                                 isVerifyStep=True)
    toggleVisibilityTest.addStep('Enter valid Connect credentials and press "Login" button and then '
                                 'close dock.')
    toggleVisibilityTest.addStep('Open dock from menu "Plugins -> Boundless '
                                 'Connect". Verify that dock opened with '
                                 'active search screen.',
                                 isVerifyStep=True)
    toggleVisibilityTest.addStep('Close dock.')
    toggleVisibilityTest.addStep('Right-click on QGIS toolbar and check '
                                '"Boundless Connect" panel. Verify that '
                                'dock opened with active search screen.',
                                 isVerifyStep=True)


    return [emptyCredentialsTest, invalidCredentialsTest, repeatedLoginTest,
            invalidEndpointTest, emptySearchTest, searchTest, paginationTest,
            wrongSearchTest, categorySearchTest, pluginSearchTest, rolesDisplayTest,
            basemapsLoadingTest, defaultProjectTest, complexDefaultProjectTest,
            lessonsInstallTest, helpTest, toggleVisibilityTest]


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
        self.assertTrue('connecttest' in qgsutils.active_plugins), 'Plugin not activated'

        unloadPlugin('connecttest')
        result = removeDir(os.path.join(home_plugin_path, 'connecttest'))
        self.assertFalse(result, 'Plugin directory not removed')
        result = utils.installFromZipFile(pluginPath)
        self.assertIsNone(result), 'Error installing plugin: {}'.format(result)
        self.assertTrue('connecttest' in qgsutils.active_plugins), 'Plugin not activated after reinstallation'

    def testIsBoundlessCheck(self):
        """Test that Connect detects Boundless plugins"""
        with open(os.path.join(testPath, 'data', 'samplepluginsdict.json')) as f:
            pluginsDict = json.load(f)
        count = len([key for key in pluginsDict if utils.isBoundlessPlugin(pluginsDict[key])])
        self.assertEqual(8, count)

    def testCustomRepoUrl(self):
        """Test that Connect read custom repository URL and apply it"""
        oldRepoUrl = pluginSetting('repoUrl')
        setPluginSetting('repoUrl', 'test')
        self.assertEqual('test', pluginSetting('repoUrl'))

        fName = os.path.join(QgsApplication.qgisSettingsDirPath(), repoUrlFile)
        with open(fName, 'w') as f:
            f.write('[general]\nrepoUrl=http://dummyurl.com')
        utils.setRepositoryUrl()

        self.assertTrue('http://dummyurl.com', pluginSetting('repoUrl'))
        setPluginSetting('repoUrl', oldRepoUrl)
        if os.path.isfile(fName):
            os.remove(fName)

    @classmethod
    def tearDownClass(cls):
        # Remove installed HelloWorld plugin
        installer = QgsPluginInstaller()
        if 'connecttest' in qgsutils.active_plugins:
            installer.uninstallPlugin('connecttest', quiet=True)

        # Also remove other installed plugins
        global installedPlugins
        for key in plugins.all():
            if key in ['boundlessconnect', 'qgistester']:
                continue
            if utils.isBoundlessPlugin(plugins.all()[key]) and plugins.all()[key]['installed'] and key not in installedPlugins:
                installer.uninstallPlugin(key, quiet=True)


class BasemapsTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.join(os.path.dirname(__file__), 'data')
        cls.local_maps_uri = os.path.join(cls.data_dir, 'basemaps.json')
        cls.tpl_path = os.path.join(
            os.path.dirname(__file__), os.path.pardir, 'resources', 'project_default.qgs.tpl')

    def _standard_id(self, tpl):
        """Change the layer ids to XXXXXXXX and also clear extents"""
        tpl = re.sub(r'id="([^\d]+)[^"]*"', 'id="\g<1>XXXXXXX"', tpl)
        tpl = re.sub(
            r'<item>([^\d]+).*?</item>', '<item>\g<1>XXXXXXX</item>', tpl)
        tpl = re.sub(r'<id>([^\d]+).*?</id>', '<id>\g<1>XXXXXXX</id>', tpl)
        tpl = re.sub(r'authcfg=[a-z0-9]+', 'authcfg=YYYYYY', tpl)
        tpl = re.sub(r'(xmin|ymin|xmax|ymax)>[^<]+<.*', '\g<1>>ZZZZZ</\g<1>>', tpl)
        return tpl

    def test_utils_get_available_maps(self):
        """Check available maps retrieval from local test json file"""
        self.assertTrue(oauth2_supported())
        maps = basemaputils.availableMaps(os.path.join(self.data_dir,
                                                     'basemaps.json'), None)
        names = [m['name'] for m in maps]
        names.sort()
        self.assertEqual(names, [u'Boundless Basemap',
                                 u'Mapbox Dark',
                                 u'Mapbox Light',
                                 u'Mapbox Outdoors',
                                 u'Mapbox Satellite',
                                 u'Mapbox Satellite Streets',
                                 #u'Mapbox Street Vector Tiles',
                                 u'Mapbox Streets',
                                 #u'Mapbox Traffic Vector Tiles',
                                 u'Recent Imagery',
                                 ])

    def test_utils_create_default_auth_project(self):
        """Create the default project with authcfg"""
        self.assertTrue(oauth2_supported())
        visible_maps = ['Mapbox Light', 'Recent Imagery']
        prj = basemaputils.createDefaultProject(
            basemaputils.availableMaps(self.local_maps_uri, None),
            visible_maps,
            self.tpl_path,
            'abc123')
        prj = self._standard_id(prj)
        tmp = tempfile.mktemp('.qgs')
        with open(tmp, "wb+") as f:
            f.write(prj)
        self.assertTrue(QgsProject.instance().read(QFileInfo(tmp)))
        # Re-generate reference:
        #with open(os.path.join(self.data_dir, 'project_default_reference.qgs'), 'wb+') as f:
        #    f.write(prj)
        with open(tmp) as f:
            prj = f.read()
        with open(os.path.join(self.data_dir, 'project_default_reference.qgs')) as f:
            prj2 = f.read()
        self.assertEqual(prj,prj2)

    def test_utils_create_default_project(self):
        """Use a no_auth project template for automated testing of valid project"""
        visible_maps = ['OSM Basemap B']
        prj = basemaputils.createDefaultProject(
            basemaputils.availableMaps(
                os.path.join(self.data_dir, 'basemaps_no_auth.json'), None),
            visible_maps,
            self.tpl_path)
        # Re-generate reference:
        #with open(os.path.join(self.data_dir, 'project_default_no_auth_reference.qgs'), 'wb+') as f:
        #    f.write(self._standard_id(prj))
        prj = self._standard_id(prj)
        tmp = tempfile.mktemp('.qgs')
        with open(tmp, 'wb+') as f:
            f.write(prj)
        self.assertTrue(QgsProject.instance().read(QFileInfo(tmp)))
        with open(tmp) as f:
            prj = f.read()
        with open(os.path.join(self.data_dir, 'project_default_no_auth_reference.qgs')) as f:
            prj2 = f.read()
        self.assertEqual(prj,prj2)


def unitTests():
    connectSuite = unittest.makeSuite(BoundlessConnectTests, 'test')
    basemapsSuite = unittest.makeSuite(BasemapsTest, 'test')
    _tests = []
    _tests.extend(connectSuite)
    _tests.extend(basemapsSuite)

    return _tests


def _openPluginManager(boundlessOnly=False):
    utils.showPluginManager(boundlessOnly)


def _downgradePlugin(pluginName, corePlugin=True):
    if corePlugin:
        metadataPath = os.path.join(QgsApplication.pkgDataPath(), 'python', 'plugins', pluginName, 'metadata.txt')
    else:
        metadataPath = os.path.join(QgsApplication.qgisSettingsDirPath()(), 'python', 'plugins', pluginName, 'metadata.txt')

    cfg = ConfigParser()
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

    cfg = ConfigParser()
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
