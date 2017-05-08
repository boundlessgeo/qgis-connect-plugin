# -*- coding: utf-8 -*-

"""
***************************************************************************
    plugins.py
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
from builtins import range

__author__ = 'Alexander Bruy'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import sys
import codecs

from qgis.PyQt.QtCore import QCoreApplication, QFileInfo, QObject, QSettings
from qgis.PyQt.QtXml import QDomDocument

try:
    from qgis.core import QGis
except ImportError:
    from qgis.core import Qgis as QGis

import qgis.utils

from pyplugin_installer.installer_data import (settingsGroup,
                                               seenPluginGroup,
                                               translatableAttributes)
from pyplugin_installer.version_compare import (compareVersions,
                                                normalizeVersion,
                                                isCompatible)

pluginPath = os.path.dirname(__file__)

boundlessRepoName = QCoreApplication.translate('Boundless Connect',
                                               'Boundless Plugin Repository')

authEndpointUrl = 'https://qgis.boundlessgeo.com/api/user_roles'
repoUrlFile = 'repoUrl.txt'
firstRunPluginsPath = 'first-run-plugins'

oldPlugins = ['opengeo']


class LocalPlugins(QObject):
    """Dict-like class for managing plugins from local repository
       Heavily based on corresponding class from QGIS Plugin Manager
    """

    def __init__(self):
        QObject.__init__(self)

        self.plugins = dict()
        self.localCache = dict()
        self.repoCache = dict()

        try:
            from qgistester.tests import addTestModule
            from boundlessconnect.test import testplugin
            addTestModule(testplugin, "Boundless Connect")
        except Exception as ex:
            pass

    def all(self):
        return self.plugins

    def allUpgradeable(self):
        result = dict()
        for i in self.plugins:
            if self.plugins[i]['status'] == 'upgradeable':
                result[i] = self.plugins[i]
        return result

    def clearRepoCache(self):
        self.repoCache = dict()

    def removeInstalledPlugin(self, key):
        if key in self.localCache:
            del self.localCache[key]

    def load(self):
        settings = QSettings('Boundless', 'BoundlessConnect')
        repoUrl = settings.value('repoUrl', '', str)

        repoPath = os.path.abspath(repoUrl)
        repoFile = os.path.join(repoPath, 'plugins.xml')

        repoXML = QDomDocument()
        with codecs.open(repoFile, 'r', encoding='utf-8') as f:
            content = f.read()
            repoXML.setContent(content)

        pluginNodes = repoXML.elementsByTagName('pyqgis_plugin')
        if pluginNodes.size():
            for i in range(pluginNodes.size()):
                fileName = pluginNodes.item(i).firstChildElement('file_name').text().strip()
                if not fileName:
                    fileName = QFileInfo(pluginNodes.item(i).firstChildElement('download_url').text().strip().split('?')[0]).fileName()
                name = fileName.partition('.')[0]

                experimental = False
                if pluginNodes.item(i).firstChildElement('experimental').text().strip().upper() in ['TRUE', 'YES']:
                    experimental = True

                deprecated = False
                if pluginNodes.item(i).firstChildElement('deprecated').text().strip().upper() in ['TRUE', 'YES']:
                    deprecated = True

                icon = pluginNodes.item(i).firstChildElement('icon').text().strip()

                if pluginNodes.item(i).toElement().hasAttribute('plugin_id'):
                    plugin_id = pluginNodes.item(i).toElement().attribute('plugin_id')
                else:
                    plugin_id = None

                plugin = {
                    'id': name,
                    'plugin_id': plugin_id,
                    'name': pluginNodes.item(i).toElement().attribute('name'),
                    'version_available': pluginNodes.item(i).toElement().attribute('version'),
                    'description': pluginNodes.item(i).firstChildElement('description').text().strip(),
                    'about': pluginNodes.item(i).firstChildElement('about').text().strip(),
                    'author_name': pluginNodes.item(i).firstChildElement('author_name').text().strip(),
                    'homepage': pluginNodes.item(i).firstChildElement('homepage').text().strip(),
                    'download_url': 'file:///{}'.format(os.path.join(repoPath, fileName)),
                    'category': pluginNodes.item(i).firstChildElement('category').text().strip(),
                    'tags': pluginNodes.item(i).firstChildElement('tags').text().strip(),
                    'changelog': pluginNodes.item(i).firstChildElement('changelog').text().strip(),
                    'author_email': pluginNodes.item(i).firstChildElement('author_email').text().strip(),
                    'tracker': pluginNodes.item(i).firstChildElement('tracker').text().strip(),
                    'code_repository': pluginNodes.item(i).firstChildElement('repository').text().strip(),
                    'downloads': pluginNodes.item(i).firstChildElement('downloads').text().strip(),
                    'average_vote': pluginNodes.item(i).firstChildElement('average_vote').text().strip(),
                    'rating_votes': pluginNodes.item(i).firstChildElement('rating_votes').text().strip(),
                    'icon': icon,
                    'experimental': experimental,
                    'deprecated': deprecated,
                    'filename': fileName,
                    'installed': False,
                    'available': True,
                    'status': 'not installed',
                    'error': '',
                    'error_details': '',
                    'version_installed': '',
                    "zip_repository": boundlessRepoName,
                    'library': '',
                    'readonly': False
                }

                qgisMinimumVersion = pluginNodes.item(i).firstChildElement('qgis_minimum_version').text().strip()
                if not qgisMinimumVersion:
                    qgisMinimumVersion = '2'
                qgisMaximumVersion = pluginNodes.item(i).firstChildElement('qgis_maximum_version').text().strip()
                if not qgisMaximumVersion:
                    qgisMaximumVersion = qgisMinimumVersion[0] + '.99'
                # If compatible, add the plugin to the list
                if not pluginNodes.item(i).firstChildElement('disabled').text().strip().upper() in ['TRUE', 'YES']:
                    if isCompatible(QGis.QGIS_VERSION, qgisMinimumVersion, qgisMaximumVersion):
                        # Add the plugin to the cache
                        repo = boundlessRepoName
                        try:
                            self.repoCache[repo] += [plugin]
                        except:
                            self.repoCache[repo] = [plugin]

    def getAllInstalled(self, testLoad=True):
        self.localCache = dict()

        # Reversed list of the plugin paths: first system plugins,
        # then user plugins and finally custom path(s)
        pluginPaths = list(qgis.utils.plugin_paths)
        pluginPaths.reverse()

        for pluginsPath in pluginPaths:
            isTheSystemDir = (pluginPaths.index(pluginsPath) == 0)
            if isTheSystemDir:
                # Temporarily add the system path as the first element to force
                # loading the readonly plugins, even if masked by user ones.
                sys.path = [pluginsPath] + sys.path
            try:
                pluginDir = QDir(pluginsPath)
                pluginDir.setFilter(QDir.AllDirs)
                for key in pluginDir.entryList():
                    if key not in ['.', '..']:
                        path = QDir.convertSeparators(pluginsPath + '/' + key)
                        readOnly = isTheSystemDir
                        # Only test those not yet loaded. Loaded plugins
                        # already proved they're OK
                        testLoadThis = testLoad and key not in qgis.utils.plugins
                        plugin = self.getInstalledPlugin(key, path=path, readOnly=readOnly, testLoad=testLoadThis)
                        self.localCache[key] = plugin
                        if key in list(self.localCache.keys()) and compareVersions(self.localCache[key]['version_installed'], plugin['version_installed']) == 1:
                            # An obsolete plugin in the "user" location is
                            # masking a newer one in the "system" location!
                            self.obsoletePlugins += [key]
            except:
                # It's not necessary to stop if one of the dirs is inaccessible
                pass

            if isTheSystemDir:
                # Remove the temporarily added path
                sys.path.remove(pluginsPath)

    def rebuild(self):
        self.plugins = dict()

        settings = QSettings()
        allowExperimental = settings.value(settingsGroup + '/allowExperimental', False, bool)
        allowDeprecated = settings.value(settingsGroup + '/allowDeprecated', False, bool)
        for repo in list(self.repoCache.values()):
            for plugin in repo:
                # Don't update original elements
                newPlugin = plugin.copy()
                key = newPlugin['id']

                # Check if the plugin is allowed and if there isn't any better
                # one added already
                if (allowExperimental or not newPlugin['experimental']) \
                        and (allowDeprecated or not newPlugin['deprecated']) \
                        and not (key in self.plugins and self.plugins[key]['version_available'] and compareVersions(self.plugins[key]['version_available'], plugin['version_available']) < 2):
                    # At this moment the self.plugins dict contains only
                    # locally installed plugins. Now, add the available one if
                    # not present yet or update it if present already
                    if key not in self.plugins:
                        self.plugins[key] = newPlugin
                    else:
                        # Update local plugin with remote metadata
                        # description, about, icon: only use remote data if
                        # local one not available. Prefer local version because
                        # of i18n.
                        # NOTE: don't prefer local name to not desynchronize
                        # names if repository doesn't support i18n.
                        # Also prefer local icon to avoid downloading.
                        for attrib in translatableAttributes + ['icon']:
                            if attrib != 'name':
                                if not self.plugins[key][attrib] and newPlugin[attrib]:
                                    self.plugins[key][attrib] = newPlugin[attrib]

                        # Other remote metadata is preffered:
                        for attrib in ['name', 'plugin_id', 'description',
                                       'about', 'category', 'tags',
                                       'changelog', 'author_name',
                                       'author_email', 'homepage', 'tracker',
                                       'code_repository', 'experimental',
                                       'deprecated', 'version_available',
                                       'zip_repository', 'download_url',
                                       'filename', 'downloads',
                                       'average_vote', 'rating_votes']:
                            if attrib not in translatableAttributes or attrib == 'name':
                                if plugin[attrib]:
                                    self.plugins[key][attrib] = newPlugin[attrib]
                    # Set status
                    #
                    # installed   available   status
                    # ---------------------------------------
                    # none        any         'not installed' (will be later checked if is 'new')
                    # any         none        'orphan'
                    # same        same        'installed'
                    # less        greater     'upgradeable'
                    # greater     less        'newer'
                    if not self.plugins[key]['version_available']:
                        self.plugins[key]['status'] = 'orphan'
                    elif not self.plugins[key]['version_installed']:
                        self.plugins[key]['status'] = 'not installed'
                    elif self.plugins[key]['version_installed'] in ['?', '-1']:
                        self.plugins[key]['status'] = 'installed'
                    elif compareVersions(self.plugins[key]['version_available'], self.plugins[key]['version_installed']) == 0:
                        self.plugins[key]['status'] = 'installed'
                    elif compareVersions(self.plugins[key]['version_available'], self.plugins[key]['version_installed']) == 1:
                        self.plugins[key]['status'] = 'upgradeable'
                    else:
                        self.plugins[key]['status'] = 'newer'

                    # debug: test if the status match the "installed" tag:
                    if self.plugins[key]['status'] in ['not installed'] and self.plugins[key]['installed']:
                        raise Exception('Error: plugin status is ambiguous (1)')
                    if self.plugins[key]['status'] in ['installed', 'orphan', 'upgradeable', 'newer'] and not self.plugins[key]['installed']:
                        raise Exception('Error: plugin status is ambiguous (2)')

        self.markNews()

    def markNews(self):
        settings = QSettings()
        seenPlugins = settings.value(seenPluginGroup, list(self.plugins.keys()), str)
        if len(seenPlugins) > 0:
            for i in list(self.plugins.keys()):
                if seenPlugins.count(i) == 0 and self.plugins[i]['status'] == 'not installed':
                    self.plugins[i]['status'] = 'new'

    def updateSeenPluginsList(self):
        settings = QSettings()
        seenPlugins = settings.value(seenPluginGroup, list(self.plugins.keys()), str)
        for i in list(self.plugins.keys()):
            if seenPlugins.count(i) == 0:
                seenPlugins += [i]
        settings.setValue(seenPluginGroup, seenPlugins)

    def isThereAnythingNew(self):
        for i in list(self.plugins.values()):
            if i['status'] in ['upgradeable', 'new']:
                return True
        return False


localPlugins = LocalPlugins()
