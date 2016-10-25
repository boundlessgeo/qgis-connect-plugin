import webbrowser
import pyplugin_installer
from pyplugin_installer.installer_data import plugins
from boundlessconnect.networkaccessmanager import NetworkAccessManager
from boundlessconnect import utils
from copy import copy
import os
from PyQt4.Qt import QIcon
import json

pluginPath = os.path.dirname(__file__)

LEVELS = ["Open", "Registered Users", "Desktop Basic", "Desktop standard", "Desktop enterprise", "Student"]
_LEVELS = [p.replace(" ", "").lower().strip() for p in LEVELS]

SUBSCRIBE_URL = ""

class ConnectContent():
    def __init__(self, url, name, description, level = ["open"]):
        self.url = url
        self.name = name
        self.description = description
        self.level = level

    def icon(self):
        return QIcon(os.path.join(pluginPath, "icons", "%s.png" % self.typeName().lower()))

    def categoryDescription(self):
        path = os.path.join(pluginPath, "html", "%s.html" % self.typeName().lower())
        with open(path) as f:
            return f.read()

    def canOpen(self, level):
        return level in self.level or _LEVELS[0] in self.level

    def open(self, level):
        if self.canOpen(level):
            self._open()
        else:
            webbrowser.open_new(SUBSCRIBE_URL)

    def asHtmlEntry(self, level):
        levelClass = 'canInstall' if self.canOpen(level) else 'cannotInstall'
        levels = ", ".join([LEVELS[_LEVELS.index(lev)] for lev in level])
        s = ("<a class='title' href='%s'>%s</a><div class='category'>%s</div><div class='%s'>%s</div><div class='description'>%s</div>"
            % (self.url, self.name, self.typeName(), levelClass, levels, self.description))
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

    def __init__(self, plugin):
        self.plugin = plugin
        self.name = plugin["name"]
        self.description = plugin["description"]
        self.url = plugin["download_url"]
        self.level = []

    def typeName(self):
        return "Plugin"

    def canOpen(self, level):
        return True

    def _open(self):
        installer = pyplugin_installer.instance()
        installer.installPlugin(self.name)

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

BASE_URL = "http://api.dev.boundlessgeo.com/v1/search/"

_plugins = []
def loadPlugins():
    global _plugins
    _plugins = []
    installer = pyplugin_installer.instance()
    installer.fetchAvailablePlugins(True)
    for plugin in plugins.all():
        if utils.isBoundlessPlugin(plugins.all()[plugin]) and plugin not in ['boundlessconnect']:
            _plugins.append(copy(plugins.all()[plugin]))

def getPlugins(text):
    if text:
        return [p for p in _plugins if text.lower() in p['name'].lower() or text in p['description'].lower()]
    else:
        return []

categories = {"LC": ConnectLearning,
              "DOC": ConnectDocumentation,
              "VID": ConnectVideo,
              "BLOG": ConnectBlog,
              "QA": ConnectQA,
              "DIS": ConnectDiscussion,
              "PLUG": ConnectPlugin}

RESULTS_PER_PAGE = 20

def search(text, page):
    nam = NetworkAccessManager()
    res, resText = nam.request(BASE_URL + "?q=%s&p=%s&c=%i" % (text, page, RESULTS_PER_PAGE))
    jsonText = json.loads(resText)
    results = []
    for element in jsonText["features"]:
        props = element["properties"]
        level = [p.replace(" ", "").lower().strip() for p in props["role"].split(",")]
        if props["category"] != "PLUG":
            results.append(categories[props["category"]](props["url"],
                                    props["title"], props["description"], level))
    results.extend([ConnectPlugin(p) for p in getPlugins(text)])
    return results

class OpenContentException(Exception):
    pass
