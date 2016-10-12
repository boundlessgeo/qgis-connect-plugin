import webbrowser
import requests
import pyplugin_installer
from pyplugin_installer.installer_data import plugins

from boundlessconnect import utils
from copy import copy
import os

class ConnectContent():
	def __init__(self, url, name, description):
		self.url = url
		self.name = name
		self.description = description

LESSONS_PLUGIN_NAME = ""
class ConnectLesson(ConnectContent):
	def open(self):
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
	def open(self):
		webbrowser.open_new(self.url)


pluginPath = os.path.split(os.path.dirname(__file__))[0]

class ConnectPlugin(ConnectContent):

	def __init__(self, plugin):
		self.plugin = plugin
		self.name = plugin["name"]
		self.description = self._pluginDescription(plugin)

	def _pluginDescription(self, plugin):
		html = '<style>body, table {padding:0px; margin:0px; font-family:verdana; font-size: 1.1em;}</style>'
		html += '<body>'
		html += '<table cellspacing="4" width="100%"><tr><td>'
		html += '<img src="file://{}" style="float:right;max-width:64px;max-height:64px;">'.format(
														os.path.join(pluginPath, 'icons', 'desktop.png'))
		html += '<h1>{}</h1>'.format(plugin['name'])
		html += '<h3>{}</h3>'.format(plugin['description'])

		if plugin['about'] != '':
			html += plugin['about'].replace('\n', '<br/>')

		html += '<br/><br/>'

		if plugin['category'] != '':
			html += '{}: {} <br/>'.format(self.tr('Category'), plugin['category'])

		if plugin['tags'] != '':
			html += '{}: {} <br/>'.format(self.tr('Tags'), plugin['tags'])

		if plugin['homepage'] != '' or plugin['tracker'] != '' or plugin['code_repository'] != '':
			html += self.tr('More info:')

			if plugin['homepage'] != '':
				html += '<a href="{}">{}</a> &nbsp;'.format(plugin['homepage'], self.tr('homepage') )

			if plugin['tracker'] != '':
				html += '<a href="{}">{}</a> &nbsp;'.format(plugin['tracker'], self.tr('bug_tracker') )

			if plugin['code_repository'] != '':
				html += '<a href="{}">{}</a> &nbsp;'.format(plugin['code_repository'], self.tr('code_repository') )

			html += '<br/>'

		html += '<br/>'

		if plugin['author_email'] != '':
			html += '{}: <a href="mailto:{}">{}</a>'.format(self.tr('Author'), plugin['author_email'], plugin['author_name'])
			html += '<br/><br/>'
		elif plugin['author_name'] != '':
			html += '{}: {}'.format(self.tr('Author'), plugin['author_name'])
			html += '<br/><br/>'

		if plugin['version_installed'] != '':
			ver = plugin['version_installed']
			if ver == '-1':
				ver = '?'

			html += self.tr('Installed version: {} (in {})<br/>'.format(ver, plugin['library']))

		if plugin['version_available'] != '':
			html += self.tr('Available version: {} (in {})<br/>'.format(plugin['version_available'], plugin['zip_repository']))

		if plugin['changelog'] != '':
			html += '<br/>'
			changelog = self.tr('Changelog:<br/>{} <br/>'.format(plugin['changelog']))
			html += changelog.replace('\n', '<br/>')

		html += '</td></tr></table>'
		html += '</body>'

		return html

	def tr(self, t):
		return t

	def typeName(self):
		return "Plugin"

	def open(self):
		installer = pyplugin_installer.instance()
		installer.installPlugin(self.name)

class ConnectVideo(ConnectWebAdress):
	def typeName(self):
		return "Video"

class ConnectTutorial(ConnectWebAdress):
	def typeName(self):
		return "Tutorial"

class ConnectDocument(ConnectWebAdress):
	def typeName(self):
		return "Document"


BASE_URL = ""

TEST_SEARCH_RESULT = [
	ConnectTutorial("http://workshops.boundlessgeo.com/tutorial-lidar/", "Lidar tutorial", "Analyzing and Visualizing LiDAR"),
	ConnectVideo("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "Introduction to Desktop", "Learn the basic ideas about Boundless Desktop"),
	ConnectDocument("http://docs.qgis.org/2.14/pdf/en/QGIS-2.14-PyQGISDeveloperCookbook-en.pdf", "PyQGIS Cookbook", "Learn to use Python in QGIS")
]

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
        text = text.lower()
	return [p for p in _plugins if text in p['name'].lower() or text in p['description'].lower()]


def search(text):
	response =  TEST_SEARCH_RESULT
	response.extend([ConnectPlugin(p) for p in getPlugins(text)])
	return response
	r = requests.get(BASE_URL, params = {"search": text})
	r._raise_for_status()
	return r.json()



class OpenContentException(Exception):
	pass
