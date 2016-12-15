# -*- coding: cp1252 -*-

from builtins import object

import os
import re
import json
from copy import copy
import webbrowser

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QMessageBox
from qgis.utils import iface

import pyplugin_installer
from pyplugin_installer.installer_data import plugins

from boundlessconnect.gui.executor import execute
from boundlessconnect.networkaccessmanager import NetworkAccessManager
from boundlessconnect import utils

pluginPath = os.path.dirname(__file__)

OPEN_ROLE = "open"

SUBSCRIBE_URL = "https://connect.boundlessgeo.com/Upgrade-Subscription"

class ConnectContent(object):
    def __init__(self, url, name, description, roles = ["open"]):
        self.url = url
        self.name = name
        self.description = description
        self.roles = roles

    def icon(self):
        return QIcon(os.path.join(pluginPath, "icons", "%s.png" % self.typeName().lower()))

    def categoryDescription(self):
        path = os.path.join(pluginPath, "html", "%s.html" % self.typeName().lower())
        with open(path) as f:
            return f.read()

    def canOpen(self, roles):
        matches = [role for role in roles if role in self.roles]
        return bool(matches) or OPEN_ROLE in self.roles

    def open(self, roles):
        if self.canOpen(roles):
            self._open()
        else:
            webbrowser.open_new(SUBSCRIBE_URL)

    def asHtmlEntry(self, roles):
        canInstall = 'CanInstall' if self.canOpen(roles) else 'CannotInstall'
        s = ("<div class='outer'><a class='title%s' href='%s'>%s</a><div class='inner'><div class='category%s'>%s</div><div class='description%s'>%s</div></div></div>"
            % (canInstall, self.url, self.name, canInstall, self.typeName(), canInstall, self.description))
        return s

LESSONS_PLUGIN_NAME = ""
class ConnectLesson(ConnectContent):
    def _open(self):
        if LESSONS_PLUGIN_NAME not in available_plugins:
            raise OpenContentException("Lessons plugin is not installed")
        elif LESSONS_PLUGIN_NAME not in active_plugins:
            raise OpenContentException("Lessons plugin is not active")
        self.downloadAndInstall()

    def downloadAndInstall(self):
        pass

    def typeName(self):
        return "Lesson"

class ConnectWebAdress(ConnectContent):
    def _open(self):
        webbrowser.open_new(self.url)

class ConnectPlugin(ConnectContent):

    def __init__(self, plugin, roles):
        self.plugin = plugin
        self.name = plugin["name"]
        self.description = re.sub('<p>This plugin is available.*?access</a></p>', '', plugin["description"])
        self.url = plugin["download_url"]
        self.roles = roles

    def typeName(self):
        return "Plugin"

    def _open(self):
        if self.plugin['status'] == 'upgradeable':
            reply = QMessageBox.question(iface.mainWindow(), 'Plugin',
                     "An older version of the plugin is already installed. Do you want to upgrade it?",
                     QMessageBox.Yes | QMessageBox.No)

            if reply != QMessageBox.Yes:
                return
        elif self.plugin['status'] in ['not installed', 'new']:
            pass
        else:
            reply = QMessageBox.question(iface.mainWindow(), 'Plugin',
                     "The plugin is already installed. Do you want to reinstall it?",
                     QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        def _install():
            installer = pyplugin_installer.instance()
            installer.installPlugin(self.plugin["id"])
        execute(_install)

class ConnectVideo(ConnectWebAdress):
    def typeName(self):
        return "Video"

class ConnectLearning(ConnectWebAdress):
    def typeName(self):
        return "Learning"

class ConnectQA(ConnectWebAdress):
    def typeName(self):
        return "Q & A"

class ConnectBlog(ConnectWebAdress):
    def typeName(self):
        return "Blog"

class ConnectDocumentation(ConnectWebAdress):
    def typeName(self):
        return "Documentation"

class ConnectDiscussion(ConnectWebAdress):
    def typeName(self):
        return "Discussion"

class ConnectOther(ConnectWebAdress):
    def typeName(self):
        return "Other"

BASE_URL = "http://api.boundlessgeo.com/v1/search/"

_plugins = {}
def loadPlugins():
    global _plugins
    _plugins = {}
    installer = pyplugin_installer.instance()
    installer.fetchAvailablePlugins(True)
    for name in plugins.all():
        plugin = plugins.all()[name]
        if utils.isBoundlessPlugin(plugin) and name not in ['boundlessconnect']:
            _plugins[plugin["name"]] = copy(plugin)


categories = {"LC": (ConnectLearning, "Learning"),
              "DOC": (ConnectDocumentation, "Documentation"),
              "VID": (ConnectVideo, "Video"),
              "BLOG": (ConnectBlog, "Blog"),
              "QA": (ConnectQA, "Q & A"),
              "DIS": (ConnectDiscussion, "Discussion"),
              "PLUG": (ConnectPlugin, "Plugin")}

RESULTS_PER_PAGE = 20

def search(text, category=None, page=0):
    nam = NetworkAccessManager()
    if category is None:
        res, resText = nam.request("{}?q={}&si={}&c={}".format(BASE_URL, text, int(page), RESULTS_PER_PAGE))
    else:
        res, resText = nam.request("{}categories/{}/?q={}&si={}&c={}".format(BASE_URL, category, text, int(page), RESULTS_PER_PAGE))
    jsonText = json.loads(resText)
    results = []
    for element in jsonText["features"]:
        props = element["properties"]
        roles = props["role"].split(",")
        if props["category"] != "PLUG":
            title = props["title"] or props["description"].split(".")[0]
            results.append(categories[props["category"]][0](props["url"],
                                    title, props["description"], roles))
        else:
            plugin = _plugins.get(props["title"], None)
            if plugin:
                results.append(ConnectPlugin(plugin, roles))
    return results

class OpenContentException(Exception):
    pass
