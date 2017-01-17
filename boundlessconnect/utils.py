# -*- coding: utf-8 -*-

"""
***************************************************************************
    utils.py
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
from future import standard_library
standard_library.install_aliases()
from builtins import str
import tempfile
import time

__author__ = 'Alexander Bruy'
__date__ = 'February 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import glob
import shutil
import zipfile
import socket

try:
    from configparser import ConfigParser
except:
    from ConfigParser import ConfigParser

from qgis.PyQt.QtCore import QSettings, QDir, QFile, QCoreApplication

from qgis.core import QgsApplication
from qgis.utils import (iface,
                        loadPlugin,
                        startPlugin,
                        reloadPlugin,
                        unloadPlugin,
                        updateAvailablePlugins,
                        home_plugin_path)

import pyplugin_installer
from pyplugin_installer.qgsplugininstallerinstallingdialog import QgsPluginInstallerInstallingDialog
from pyplugin_installer.installer_data import (reposGroup,
                                               repositories,
                                               plugins,
                                               removeDir)
from pyplugin_installer.version_compare import compareVersions
from pyplugin_installer.unzip import unzip

from boundlessconnect.plugins import (boundlessRepoName,
                                      defaultRepoUrl,
                                      repoUrlFile,
                                      firstRunPluginsPath,
                                      oldPlugins,
                                      localPlugins)

pluginPath = os.path.dirname(__file__)


def addBoundlessRepository():
    """Add Boundless plugin repository to list of the available
       plugin repositories if it is not presented here
    """
    settings = QSettings('Boundless', 'BoundlessConnect')
    repoUrl = settings.value('repoUrl', '')

    if repoUrl == '':
        repoUrl = setRepositoryUrl()

    if isRepositoryInDirectory():
        return

    settings = QSettings()
    settings.beginGroup(reposGroup)
    hasBoundlessRepository = False
    for repo in settings.childGroups():
        url = settings.value(repo + '/url', '')
        if url == repoUrl:
            hasBoundlessRepository = True

    # Boundless repository not found, so we add it to the list
    if not hasBoundlessRepository:
        settings.setValue(boundlessRepoName + '/url', repoUrl)
        settings.setValue(boundlessRepoName + '/authcfg', '')
    settings.endGroup()


def setRepositoryAuth(authConfigId):
    """Add auth to the repository
    """
    settings = QSettings('Boundless', 'BoundlessConnect')
    repoUrl = settings.value('repoUrl', '')

    settings = QSettings()
    settings.beginGroup(reposGroup)
    for repo in settings.childGroups():
        url = settings.value(repo + '/url', '')
        if url == repoUrl:
            settings.setValue(repo + '/authcfg', authConfigId)
    settings.endGroup()


def showPluginManager(boundlessOnly):
    """Show Plugin Manager with all plugins. This includes plugins from
    Official QGIS plugins repository and plugins from Boundless plugins
    repository (local or remote).
    If boundlessOnly=True, it will only show Boundless plugins
    """

    installer = pyplugin_installer.instance()

    initPluginManager(installer, boundlessOnly)
    iface.pluginManagerInterface().showPluginManager(2)
    # Restore repositories, as we don't want to keep local repo in cache
    if repositories is not None:
        repositories.load()


def initPluginManager(installer, boundlessOnly=False):
    """Prepare plugin manager content
    """
    settings = QSettings('Boundless', 'BoundlessConnect')
    repoUrl = settings.value('repoUrl', '')

    repositories.load()

    if installer.statusLabel:
        iface.mainWindow().statusBar().removeWidget(installer.statusLabel)

    # Load plugins from remote repositories and export repositories
    # to Plugin Manager
    installer.fetchAvailablePlugins(True)
    installer.exportRepositoriesToManager()

    # If Boundless repository is a local directory, add plugins
    # from it to Plugin Manager
    if isRepositoryInDirectory():
        repositoryData = {'url': repoUrl,
                          'authcfg': ''
                         }
        repositories.mRepositories.update({boundlessRepoName: repositoryData})

        localPlugins.getAllInstalled()
        localPlugins.load()
        localPlugins.rebuild()

        plugins.mPlugins.update(localPlugins.all())

    if boundlessOnly:
        for pluginName, pluginDesc in list(plugins.mPlugins.items()):
            if not isBoundlessPlugin(pluginDesc):
                del plugins.mPlugins[pluginName]

    # Export all plugins to Plugin Manager
    installer.exportPluginsToManager()
    if installer.statusLabel:
        iface.mainWindow().statusBar().removeWidget(installer.statusLabel)


def installAllPlugins():
    """Install all available plugins from Boundless plugins repository
    """
    settings = QSettings('Boundless', 'BoundlessConnect')
    repoUrl = settings.value('repoUrl', '')

    if isRepositoryInDirectory():
        pluginsDirectory = os.path.abspath(repoUrl)
        installAllFromDirectory(pluginsDirectory)
    else:
        installAllFromRepository()


def installAllFromRepository():
    """Install Boundless plugins from remote repository
    """
    installer = pyplugin_installer.instance()
    initPluginManager(installer)

    errors = []
    pluginsList = plugins.all().copy()
    for plugin in pluginsList:
        if isBoundlessPlugin(pluginsList[plugin]):
            if (pluginsList[plugin]['installed'] and pluginsList[plugin]['deprecated']) or \
                    not pluginsList[plugin]['deprecated'] and \
                    pluginsList[plugin]["zip_repository"] != '':
                dlg = QgsPluginInstallerInstallingDialog(iface.mainWindow(), plugins.all()[plugin])
                dlg.exec_()
                if dlg.result():
                    errors.append(dlg.result())
                else:
                    updateAvailablePlugins()
                    loadPlugin(plugins.all()[plugin]['id'])
                    plugins.getAllInstalled(testLoad=True)
                    plugins.rebuild()
                    if not plugins.all()[plugin]["error"]:
                        if startPlugin(plugins.all()[plugin]['id']):
                            settings = QSettings()
                            settings.setValue('/PythonPlugins/' + plugins.all()[plugin]['id'], True)

    installer.exportPluginsToManager()
    return errors


def installAllFromDirectory(pluginsPath):
    """Install plugins from specified directory
    """
    errors = []

    installer = pyplugin_installer.instance()

    mask = pluginsPath + '/*.zip'

    for plugin in glob.glob(mask):
        result = installFromZipFile(plugin)
        if result is not None:
            errors.append(result)

    installer.exportPluginsToManager()
    return errors


def installFromStandardPath():
    """Also install all plugins from "standard" location
    """
    dirName = os.path.join(QgsApplication.qgisSettingsDirPath(), firstRunPluginsPath)
    if os.path.isdir(dirName):
        installAllFromDirectory(dirName)
        shutil.rmtree(dirName)


def installFromZipFile(pluginPath):
    """Install and activate plugin from the specified package
    """
    result = None

    with zipfile.ZipFile(pluginPath, 'r') as zf:
        pluginName = os.path.split(zf.namelist()[0])[0]

    pluginFileName = os.path.splitext(os.path.basename(pluginPath))[0]

    pluginsDirectory = home_plugin_path
    if not QDir(pluginsDirectory).exists():
        QDir().mkpath(pluginsDirectory)

    # If the target directory already exists as a link,
    # remove the link without resolving
    QFile(os.path.join(pluginsDirectory, pluginFileName)).remove()

    try:
        # Test extraction. If fails, then exception will be raised
        # and no removing occurs
        unzip(str(pluginPath), str(pluginsDirectory))
        # Removing old plugin files if exist
        removeDir(QDir.cleanPath(os.path.join(pluginsDirectory, pluginFileName)))
        # Extract new files
        unzip(str(pluginPath), str(pluginsDirectory))
    except:
        result = QCoreApplication.translate('BoundlessConnect',
            'Failed to unzip the plugin package\n{}.\nProbably it is broken'.format(pluginPath))

    if result is None:
        updateAvailablePlugins()
        loadPlugin(pluginName)
        plugins.getAllInstalled(testLoad=True)
        plugins.rebuild()
        plugin = plugins.all()[pluginName]

        settings = QSettings()
        if settings.contains('/PythonPlugins/' + pluginName):
            if settings.value('/PythonPlugins/' + pluginName, False, bool):
                startPlugin(pluginName)
                reloadPlugin(pluginName)
            else:
                unloadPlugin(pluginName)
                loadPlugin(pluginName)
        else:
            if startPlugin(pluginName):
                settings.setValue('/PythonPlugins/' + pluginName, True)

    return result


def isRepositoryInDirectory():
    """Return True if plugin repository is a plain directory
    """
    settings = QSettings('Boundless', 'BoundlessConnect')
    repoUrl = settings.value('repoUrl', '')

    return repoUrl != '' and os.path.isdir(os.path.abspath(repoUrl))


def isBoundlessPlugin(plugin):
    """Return true if plugin is Boundless plugin
    """
    if plugin['zip_repository'] == boundlessRepoName or \
            'boundless' in plugin['code_repository']:
        return True
    else:
        return False


def deprecatedPlugins():
    """Return list of installed deprecated Boundless plugins
    """
    installer = pyplugin_installer.instance()
    initPluginManager(installer)

    deprecated = []
    for plugin in plugins.all():
        if isBoundlessPlugin(plugins.all()[plugin]):
            if plugins.all()[plugin]['installed'] and \
                    (plugins.all()[plugin]['deprecated'] or
                    plugin in oldPlugins):
                deprecated.append(plugins.all()[plugin])

    return deprecated


def setRepositoryUrl():
    """Adds Boundless repository URL to Connect settings"""
    fName = os.path.join(QgsApplication.qgisSettingsDirPath(), repoUrlFile)
    if os.path.exists(fName):
        cfg = ConfigParser()
        cfg.read(fName)
        url = cfg.get('general', 'repoUrl')
        os.remove(fName)
    else:
        url = defaultRepoUrl

    settings = QSettings('Boundless', 'BoundlessConnect')
    settings.setValue('repoUrl', url)
    return url


def upgradeInstalledPlugins():
    installer = pyplugin_installer.instance()
    initPluginManager(installer)

    errors = []
    pluginsList = plugins.all().copy()
    for plugin in pluginsList:
        if isBoundlessPlugin(pluginsList[plugin]):
            if pluginsList[plugin]['installed'] and pluginsList[plugin]['status'] == 'upgradeable':
                dlg = QgsPluginInstallerInstallingDialog(iface.mainWindow(), plugins.all()[plugin])
                dlg.exec_()
                if dlg.result():
                    errors.append(dlg.result())
                else:
                    updateAvailablePlugins()
                    loadPlugin(plugins.all()[plugin]['id'])
                    plugins.getAllInstalled(testLoad=True)
                    plugins.rebuild()
                    if not plugins.all()[plugin]["error"]:
                        if startPlugin(plugins.all()[plugin]['id']):
                            settings = QSettings()
                            settings.setValue('/PythonPlugins/' + plugins.all()[plugin]['id'], True)

    installer.exportPluginsToManager()
    return errors


def addCheckForUpdates():
    if not repositories.checkingOnStart():
        repositories.setCheckingOnStart(True)
        repositories.setCheckingOnStartInterval(30)
        repositories.saveCheckingOnStartLastDate()

_tempFolder = None
def tempFolder():
    global _tempFolder
    if _tempFolder is None:
        _tempFolder = tempfile.mkdtemp()
    return _tempFolder

def deleteTempFolder():
    if _tempFolder is not None:
        shutil.rmtree(_tempFolder, True)

def tempFilename(ext):
    path = tempFolder()
    ext = "" if ext is None else ext
    filename = path + os.sep + str(time.time()) + "." + ext
    return filename