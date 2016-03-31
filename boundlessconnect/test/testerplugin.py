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
import unittest
import json

from PyQt4.QtCore import QSettings

from qgis.utils import active_plugins
from pyplugin_installer.installer import QgsPluginInstaller
from pyplugin_installer.installer_data import reposGroup, plugins

from boundlessconnect.boundlessconnect_plugin import BoundlessConnectPlugin
from boundlessconnect.plugins import boundlessRepo
from boundlessconnect import utils

testPath = os.path.dirname(__file__)

installedPlugins = []

def functionalTests():
    try:
        from qgistester.test import Test
    except:
        return []


    openPluginManagerTest = Test('Verify that Boundless Connect can start Plugin Manager')
    openPluginManagerTest.addStep('Check that OpenGeo Explorer listed in Plugin Manager as well as plugins from QGIS repository',
                                prestep=lambda: _openPluginManager(False), isVerifyStep=True)
    openPluginManagerTest.setIssueUrl("https://issues.boundlessgeo.com:8443/browse/QGIS-325")

    openPluginManagerBoundlessOnlyTest = Test('Verify that Boundless Connect can start Plugin Manager only with Boundless plugins')
    openPluginManagerBoundlessOnlyTest.addStep('Check that Plugin manager is open and contains only Boundless plugins',
                                prestep=lambda: _openPluginManager(True), isVerifyStep=True)
    openPluginManagerBoundlessOnlyTest.setIssueUrl("https://issues.boundlessgeo.com:8443/browse/QGIS-325")

    return [openPluginManagerTest, openPluginManagerBoundlessOnlyTest]


class BoundlessConnectTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        global installedPlugins
        installedPlugins[:] = []
        for key in plugins.all():
            if plugins.all()[key]['zip_repository'] == boundlessRepo[0] or \
                    'boundlessgeo' in plugins.all()[key]['code_repository'] and\
                    plugins.all()[key]['installed']:
                installedPlugins.append(key)

    def testBoundlessRepoAdded(self):
        """Test that Boundless repository added to QGIS"""
        settings = QSettings()
        settings.beginGroup(reposGroup)
        self.assertTrue(boundlessRepo[0] in settings.childGroups())
        settings.endGroup()

        settings.beginGroup(reposGroup + '/' + boundlessRepo[0])
        url = settings.value('url', '', unicode)
        self.assertEqual(url, boundlessRepo[1])
        settings.endGroup()

    def testInstallFromZip(self):
        """Test plugin installation from ZIP package"""
        pluginPath = os.path.join(testPath, 'data', 'connecttest.zip')
        result = utils.installFromZipFile(pluginPath)
        self.assertIsNone(result), 'Error installing plugin: {}'.format(result)
        self.assertTrue('connecttest' in active_plugins), 'Plugin not activated'

    def testIsBoundlessCheck(self):
        with open(os.path.join(testPath, 'data', "samplepluginsdict.json")) as f:    
            pluginsDict = json.load(f)
        count = len([key for key in pluginsDict if utils.isBoundlessPlugin(pluginsDict[key])])
        self.assertEqual(8, count)

    def testInstallAll(self):
        """Test that Connect installs all Boundless plugins"""
        utils.installAllPlugins()

        total = 0
        installed = 0
        for key in plugins.all():
            if utils.isBoundlessPlugin(plugins.all()[key]):
                total += 1
                if plugins.all()[key]['installed']:
                    installed += 1

        assert (total == installed), 'Number of installed Boundless plugins does not match number of available Boundless plugins'



    @classmethod
    def tearDownClass(cls):
        """Remove installed HelloWorld plugin"""
        installer = QgsPluginInstaller()
        if 'connecttest' in active_plugins:
            installer.uninstallPlugin('connecttest', quiet=True)

        global installedPlugins
        for key in plugins.all():
            if plugins.all()[key]['zip_repository'] == boundlessRepo[0] or \
                    'boundlessgeo' in plugins.all()[key]['code_repository'] and \
                    key not in installedPlugins:
                installer.uninstallPlugin(key, quiet=True)


def unitTests():
    connectSuite = unittest.makeSuite(BoundlessConnectTests, 'test')
    _tests = []
    _tests.extend(connectSuite)

    return _tests


def _openPluginManager(boundlessOnly):
    utils.showPluginManager(boundlessOnly)


def _installAllPlugins():
    utils.installAllPlugins()
