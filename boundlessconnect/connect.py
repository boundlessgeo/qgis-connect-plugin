# -*- coding: cp1252 -*-

from builtins import object

import os
import re
import json
import urllib2
import tempfile
from copy import copy
import webbrowser

from qgis.PyQt.QtGui import QIcon, QCursor
from qgis.PyQt.QtCore import Qt, QUrl, QFile, QEventLoop
from qgis.PyQt.QtWidgets import QMessageBox, QApplication
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

from qgis.gui import QgsMessageBar, QgsFileDownloader
from qgis.core import QgsNetworkAccessManager, QgsRasterLayer, QgsMapLayerRegistry
from qgis.utils import iface, available_plugins, active_plugins

import pyplugin_installer
from pyplugin_installer.installer_data import plugins

from qgiscommons.networkaccessmanager import NetworkAccessManager
from qgiscommons.oauth2 import (oauth2_supported,
                                get_oauth_authcfg
                               )
from boundlessconnect.gui.executor import execute
from boundlessconnect import utils
from boundlessconnect import basemaputils

pluginPath = os.path.dirname(__file__)

OPEN_ROLE = "open"
PUBLIC_ROLE = "public"
SUBSCRIBE_URL = "https://connect.boundlessgeo.com/Upgrade-Subscription"

LESSONS_PLUGIN_NAME = "lessons"


class ConnectContent(object):
    def __init__(self, url, name, description, roles = ["open"]):
        self.url = url
        self.name = name
        self.description = description
        self.roles = roles

    def iconPath(self):
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
        canInstall = "green" if self.canOpen(roles) else "orange"
        s = """<div class="icon-knowledge"><div class="icon-knowledge-container">
               <img src="file://{image}"></div></div>
               <div class="description"><h2>{title}</h2><p>{description}</p>
               <a class="btn-action {available}" href="{url}">{itemType}</a>
               </div>
            """.format(image=self.iconPath().replace("\\", "/"),
                       title=self.name,
                       description=self.description,
                       available=canInstall,
                       url=self.url,
                       itemType=self.typeName().upper())
        return s


class ConnectWebAdress(ConnectContent):
    def _open(self):
        webbrowser.open_new(self.url)


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


class ConnectLesson(ConnectContent):
    def typeName(self):
        return "Lesson"

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "howto.svg")

    def _open(self):
        if LESSONS_PLUGIN_NAME not in available_plugins:
            iface.messageBar().pushMessage(
                "Cannot install lessons",
                "Lessons plugin is not installed",
                QgsMessageBar.WARNING)
        elif LESSONS_PLUGIN_NAME not in active_plugins:
            iface.messageBar().pushMessage(
                "Cannot install lessons",
                "Lessons plugin is not active",
                QgsMessageBar.WARNING)
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
            iface.messageBar().pushMessage(
                "Lessons could not be installed:\n",
                self.reply.errorString(),
                QgsMessageBar.WARNING)
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

        iface.messageBar().pushMessage(
            "Completed",
            "Lessons were correctly installed",
            QgsMessageBar.INFO)


class ConnectPlugin(ConnectContent):

    def __init__(self, plugin, roles):
        self.plugin = plugin
        self.name = plugin["name"]
        self.description = re.sub("<p>This plugin is available.*?access</a></p>", "", plugin["description"])
        self.url = plugin["download_url"]
        self.roles = roles

    def typeName(self):
        return "Plugin"

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "plugin.svg")

    def asHtmlEntry(self, roles):
        canInstall = "green" if self.canOpen(roles) else "orange"
        s = """<div class="icon-knowledge"><div class="icon-knowledge-container">
               <img src="file://{image}"></div></div>
               <div class="description"><h2>{title}</h2><p>{description}</p>
               <a class="btn-action {available}" href="{url}">INSTALL</a>
               </div>
            """.format(image=self.iconPath().replace("\\", "/"),
                       title=self.name,
                       description=self.description,
                       available=canInstall,
                       url=self.url
                      )
        return s

    def _open(self):
        if self.plugin["status"] == "upgradeable":
            reply = QMessageBox.question(
                iface.mainWindow(),
                "Plugin",
                "An older version of the plugin is already installed. Do you want to upgrade it?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return
        elif self.plugin["status"] in ["not installed", "new"]:
            pass
        else:
            reply = QMessageBox.question(
                iface.mainWindow(),
                "Plugin",
                "The plugin is already installed. Do you want to reinstall it?",
                QMessageBox.Yes | QMessageBox.No)
            if reply != QMessageBox.Yes:
                return

        def _install():
            installer = pyplugin_installer.instance()
            installer.installPlugin(self.plugin["id"])

        execute(_install)


class ConnectBasemap(ConnectContent):
    def __init__(self, url, name, description, json, roles=["open"]):
        self.url = url
        self.name = name
        self.description = description
        self.roles = roles
        self.json = json

    def typeName(self):
        return "Basemap"

    def iconPath(self):
        return os.path.join(pluginPath, "icons", "thumbnail.png")

    def asHtmlEntry(self, roles):
        canInstall = "green" if self.canOpen(roles) else "orange"
        s = """<div class="icon"><div class="icon-thumbnail-container">
               <img src="file://{image}"></div></div>
               <div class="description">{title}{description}
               <a class="btn-action {available}" href="canvas{url}">ADD TO MAP</a>
               <a class="btn-action {available}" href="project{url}">ADD TO DEFAULT PROJECT</a>
               </div>
            """.format(image=self.iconPath().replace("\\", "/"),
                       title=self.name,
                       description=self.description,
                       available=canInstall,
                       url=self.url
                      )
        return s

    def addToCanvas(self, roles):
        if self.canOpen(roles):
            if not oauth2_supported:
                iface.messageBar().pushMessage(
                    "Cannot load basemap",
                    "OAuth support is not available",
                    QgsMessageBar.WARNING)
            else:
                authcfg = get_oauth_authcfg()
                if authcfg is None:
                    iface.messageBar().pushMessage(
                        "Cannot load basemap",
                        "Cannot find a valid authentication configuration",
                        QgsMessageBar.WARNING)
                else:
                    authId = authcfg.id()
                    connstring = u'type=xyz&url=%(url)s'
                    connstring = u'authcfg=%(authcfg)s&' + connstring
                    layer = QgsRasterLayer(connstring % {
                        "url": urllib2.quote(self.url), "authcfg": authId}, self.name, "wms")
                    if layer.isValid():
                        QgsMapLayerRegistry.instance().addMapLayer(layer)
                    else:
                        iface.messageBar().pushMessage(
                            "Cannot load basemap",
                            "Cannot create basemap layer",
                            QgsMessageBar.WARNING)
        else:
            webbrowser.open_new(SUBSCRIBE_URL)

    def addToDefaultProject(self, roles):
        if self.canOpen(roles):
            if not oauth2_supported:
                iface.messageBar().pushMessage(
                    "Cannot add basemap",
                    "OAuth support is not available",
                    QgsMessageBar.WARNING)
            else:
                authcfg = get_oauth_authcfg()
                if authcfg is None:
                    iface.messageBar().pushMessage(
                        "Cannot add basemap",
                        "Cannot find a valid authentication configuration",
                        QgsMessageBar.WARNING)
                else:
                    authId = authcfg.id()
                    if not basemaputils.createOrAddDefaultBasemap([self.json], [self.name], authId):
                        iface.messageBar().pushMessage(
                            "Cannot add basemap",
                            "Cannot update or create default project",
                            QgsMessageBar.WARNING)

        else:
            webbrowser.open_new(SUBSCRIBE_URL)


RESULTS_PER_PAGE = 20
BASE_URL = "http://api.boundlessgeo.io/v1/search/"

_plugins = {}
def loadPlugins():
    global _plugins
    _plugins = {}
    installer = pyplugin_installer.instance()
    installer.fetchAvailablePlugins(True)
    for name in plugins.all():
        plugin = plugins.all()[name]
        if utils.isBoundlessPlugin(plugin) and name not in ["boundlessconnect"]:
            _plugins[plugin["name"]] = copy(plugin)


categories = {"LC": (ConnectLearning, "Learning"),
              "DOC": (ConnectDocumentation, "Documentation"),
              "BLOG": (ConnectBlog, "Blog"),
              "QA": (ConnectQA, "Q & A")
             }


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

def findAll(text, category):
    page = 0
    results = []

    data = search(text, category, page)
    results = data
    while len(data) == RESULTS_PER_PAGE:
        page += 1
        data = search(text, category, page)
        results.extend(data)

    return results


BASEMAPS_ENDPOINT = "http://api.boundlessgeo.io/v1/basemaps/"
def searchBasemaps(text):
    t = tempfile.mktemp()
    q = QgsFileDownloader(QUrl(BASEMAPS_ENDPOINT), t)
    loop = QEventLoop()
    q.downloadExited.connect(loop.quit)
    loop.exec_()
    if not os.path.isfile(t):
        return []
    with open(t) as f:
        j = json.load(f)
    os.unlink(t)

    maps = [l for l in j if basemaputils.isSupported(l)]

    results = []
    for item in maps:
        if text.lower() in item["name"].lower() or text.lower() in item["description"].lower():
            results.append(
                ConnectBasemap(item["endpoint"],
                               item["name"],
                               item["description"],
                               item,
                               item["accessList"]))

    return results
