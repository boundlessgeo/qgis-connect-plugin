# -*- coding: cp1252 -*-

from builtins import object

import os
import re
import json
from copy import copy
import webbrowser

from qgis.PyQt.QtGui import QIcon, QCursor
from qgis.PyQt.QtCore import Qt, QUrl, QFile
from qgis.PyQt.QtWidgets import QMessageBox, QApplication
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from qgis.gui import QgsMessageBar
from qgis.core import QgsNetworkAccessManager
from qgis.utils import iface, available_plugins, active_plugins

import pyplugin_installer
from pyplugin_installer.installer_data import plugins

from qgiscommons.networkaccessmanager import NetworkAccessManager

from boundlessconnect.gui.executor import execute
from boundlessconnect import utils

pluginPath = os.path.dirname(__file__)

OPEN_ROLE = "open"
PUBLIC_ROLE = "public"
SUBSCRIBE_URL = "https://connect.boundlessgeo.com/Upgrade-Subscription"


class OpenContentException(Exception):
    pass


class ConnectContent(object):
    def __init__(self, url, name, description, roles = ["open"]):
        self.url = url
        self.name = name
        self.description = description
        self.roles = roles

    def iconPath(self):
        #return QIcon(os.path.join(pluginPath, "icons", "%s.png" % self.typeName().lower()))
        pass

    def categoryDescription(self):
        path = os.path.join(pluginPath, "html", "%s.html" % self.typeName().lower())
        with open(path) as f:
            return f.read()

    def canOpen(self, roles):
        matches = [role for role in roles if role in self.roles]
        return bool(matches) or (OPEN_ROLE in self.roles) or (PUBLIC_ROLE in self.roles)

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


LESSONS_PLUGIN_NAME = "lessons"


class ConnectLesson(ConnectContent):
    def _open(self):
        if LESSONS_PLUGIN_NAME not in available_plugins:
            iface.messageBar.pushMessage("Cannot install lessons", "Lessons plugin is not installed", QgsMessageBar.WARNING)
        elif LESSONS_PLUGIN_NAME not in active_plugins:
            iface.messageBar.pushMessage("Cannot install lessosn", "Lessons plugin is not active", QgsMessageBar.WARNING)
        else:
            self.downloadAndInstall()

    def downloadAndInstall(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        url = QUrl(self.url)
        self.request = QNetworkRequest(url)
        self.reply = QgsNetworkAccessManager.instance().get(self.request)
        self.reply.finished.connect(self.requestFinished)

    def requestFinished(self):
        if self.reply.error() != QNetworkReply.NoError:
            QApplication.restoreOverrideCursor()
            iface.messageBar().pushMessage("Lessons could not be installed", self.reply.errorString(), QgsMessageBar.WARNING)
            self.reply.deleteLater()
            return
        f = QFile(utils.tempFilename(os.path.basename(self.url).split(".")[0]))
        f.open(QFile.WriteOnly)
        f.write(self.reply.readAll())
        f.close()
        self.reply.deleteLater()
        from lessons import installLessonsFromZipFile
        installLessonsFromZipFile(f.fileName())
        QApplication.restoreOverrideCursor()
        iface.messageBar().pushMessage("", "Lessons were correctly installed", QgsMessageBar.INFO)

    def typeName(self):
        return "Lesson"

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "howto.svg")


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

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "learning.svg")

class ConnectQA(ConnectWebAdress):
    def typeName(self):
        return "Q & A"

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "qa.svg")

class ConnectBlog(ConnectWebAdress):
    def typeName(self):
        return "Blog"

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "blog.svg")

class ConnectDocumentation(ConnectWebAdress):
    def typeName(self):
        return "Documentation"

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "doc.svg")


class ConnectDiscussion(ConnectWebAdress):
    def typeName(self):
        return "Discussion"


class ConnectOther(ConnectWebAdress):
    def typeName(self):
        return "Other"


BASE_URL = "http://api.dev.boundlessgeo.io/v1/search/"


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
              "BLOG": (ConnectBlog, "Blog"),
              "QA": (ConnectQA, "Q & A"),
              "LESSON": (ConnectLesson, "Lesson")}

RESULTS_PER_PAGE = 20


def search(text, category='', page=0):
    nam = NetworkAccessManager()
    if category == '':
        res, resText = nam.request("{}?q={}&si={}&c={}".format(BASE_URL, text, int(page), RESULTS_PER_PAGE))
    else:
        res, resText = nam.request("{}?q={}&cat={}&si={}&c={}".format(BASE_URL, text, category, int(page), RESULTS_PER_PAGE))
    jsonText = json.loads(resText)
    results = []
    for element in jsonText["features"]:
        props = element["properties"]
        roles = props["role"].split(",")
        category = props["category"]
        if category != "PLUG":
            title = props["title"] or props["description"].split(".")[0]
            if category in categories:
                results.append(categories[category][0](props["url"],
                                                        title,
                                                        props["description"], roles))
        else:
            plugin = _plugins.get(props["title"], None)
            if plugin:
                results.append(ConnectPlugin(plugin, roles))
    return results


def searchKnowledge(text):
    pass


def searchData(text):
    pass


def searchPlugins(text):
    pass
