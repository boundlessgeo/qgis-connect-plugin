# -*- coding: utf-8 -*-

"""
***************************************************************************
    basemaputils.py
    ---------------------
    Date                 : June 2017
    Copyright            : (C) 2017 Boundless, http://boundlessgeo.com
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
__date__ = 'June 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

import os
import json
import shutil
import urllib2
import tempfile
from datetime import datetime

from qgis.PyQt.QtCore import QSettings, QEventLoop, QUrl
from qgis.PyQt.QtXml import QDomDocument, QDomElement

from qgis.core import (QgsApplication,
                       QgsCoordinateReferenceSystem,
                       QgsMapLayer,
                       QgsRasterLayer
                      )
from qgis.gui import QgsFileDownloader

from qgiscommons.networkaccessmanager import NetworkAccessManager
from qgiscommons.settings import pluginSetting

PROJECT_DEFAULT_TEMPLATE = os.path.join(os.path.dirname(__file__), 'resources', 'project_default.qgs.tpl')


def isSupported(layer):
    """Check whether the layer is supported by QGIS by excluding vector
    tiles
    """
    return (layer['tileFormat'] == 'PNG' and layer['standard'] == 'XYZ')


def defaultProjectPath():
    """Return the default project path"""
    return os.path.join(QgsApplication.qgisSettingsDirPath(), 'project_default.qgs')


def unsetDefaultProject():
    """Just store the setting"""
    settings = QSettings()
    settings.setValue('Qgis/newProjectDefault', False)


def writeDefaultProject(content, overwrite=False):
    """Create a new default project with the given content.
    If overwrite is True any pre-existing project will be silently
    overwritten.

    Return True in case of successful project writing
    """
    projectPath = defaultProjectPath()
    if not overwrite and os.path.isfile(projectPath):
        return False

    with open(projectPath, 'wb+') as f:
        f.write(content)

    settings = QSettings()
    settings.setValue('Qgis/newProjectDefault', True)
    return True


def addToDefaultProject(maps, visibleMaps, authcfg=None):
    """Add basemaps to the existing default project"""
    layers = []
    for m in maps:
        connstring = u'type=xyz&url={url}'
        if authcfg is not None:
            connstring = u'authcfg={authcfg}&' + connstring
        layer = QgsRasterLayer(connstring.format(url=urllib2.quote("{}?version={}".format(m['endpoint'], pluginSetting("apiVersion"))),
                                                 authcfg=authcfg), m['name'], 'wms')
        # I've no idea why the following is required even if the crs is specified
        # in the layer definition
        layer.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
        layers.append(layer)

    if os.path.isfile(defaultProjectPath()):
        backup = defaultProjectPath().replace(
            '.qgs', '-%s.qgs' % datetime.now().strftime('%Y-%m-%d-%H_%M_%S'))
        shutil.copy2(defaultProjectPath(), backup)

   # open default project
    with open(defaultProjectPath()) as f:
        content = f.read()

    doc = QDomDocument()
    setOk, errorString, errorLine, errorColumn = doc.setContent(content)
    if not setOk:
        return False

    root = doc.documentElement()

    for layer in layers:
        is_visible = layer.name() in visibleMaps
        xml = QgsMapLayer.asLayerDefinition([layer])
        r = xml.documentElement()
        mapLayerElement = r.firstChildElement("maplayers").firstChildElement("maplayer")

        layerTreeLayerElement = doc.createElement("layer-tree-layer")
        layerTreeLayerElement.setAttribute("expanded", "1")
        layerTreeLayerElement.setAttribute("checked", "Qt::Checked" if is_visible else "Qt::Unchecked")
        layerTreeLayerElement.setAttribute("id", layer.id())
        layerTreeLayerElement.setAttribute("name", layer.name())

        customPropertiesElement = doc.createElement("customproperties")
        layerTreeLayerElement.appendChild(customPropertiesElement)

        legendLayerElement = doc.createElement("legendlayer")
        legendLayerElement.setAttribute("drawingOrder", "-1")
        legendLayerElement.setAttribute("open", "true")
        legendLayerElement.setAttribute("checked", "Qt::Checked" if is_visible else "Qt::Unchecked")
        legendLayerElement.setAttribute("name", layer.name())
        legendLayerElement.setAttribute("showFeatureCount", "0")

        filegroupElement = doc.createElement("filegroup")
        filegroupElement.setAttribute("open", "true")
        filegroupElement.setAttribute("hidden", "false")

        legendlayerfileElement = doc.createElement("legendlayerfile")
        legendlayerfileElement.setAttribute("isInOverview", "0")
        legendlayerfileElement.setAttribute("layerid", layer.id())
        legendlayerfileElement.setAttribute("visible", "1" if is_visible else "0")

        filegroupElement.appendChild(legendlayerfileElement)
        legendLayerElement.appendChild(filegroupElement)

        crsElement = doc.createElement("layer_coordinate_transform")
        crsElement.setAttribute("destAuthId", "EPSG:3857")
        crsElement.setAttribute("srcAuthId", "EPSG:3857")
        crsElement.setAttribute("srcDatumTransform", "-1")
        crsElement.setAttribute("destDatumTransform", "-1")
        crsElement.setAttribute("layerid", layer.id())

        itemElement = doc.createElement("item")
        text = doc.createTextNode(layer.id())
        itemElement.appendChild(text)

        e = root.firstChildElement("layer-tree-group")
        e.appendChild(layerTreeLayerElement)

        e = root.firstChildElement("mapcanvas").firstChildElement("layer_coordinate_transform_info")
        e.appendChild(crsElement)

        e = root.firstChildElement("layer-tree-canvas").firstChildElement("custom-order")
        e.appendChild(itemElement)

        e = root.firstChildElement("legend")
        e.appendChild(legendLayerElement)

        e = root.firstChildElement("projectlayers")
        e.appendChild(mapLayerElement)

    with open(defaultProjectPath(), "wb+") as f:
        f.write(doc.toString())

    settings = QSettings()
    settings.setValue('Qgis/newProjectDefault', True)
    return True


def createDefaultProject(available_maps, visible_maps, project_template, authcfg=None):
    """Create a default project from a template and return it as a string"""
    layers = []
    for m in available_maps:
        connstring = u'type=xyz&url={url}'
        if authcfg is not None:
            connstring = u'authcfg={authcfg}&' + connstring
        layer = QgsRasterLayer(connstring.format(url=urllib2.quote("{}?version={}".format(m['endpoint'], pluginSetting("apiVersion"))),
                                                 authcfg=authcfg), m['name'], "wms")
        # I've no idea why the following is required even if the crs is specified
        # in the layer definition
        layer.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
        layers.append(layer)
    if len(layers):
        xml = QgsMapLayer.asLayerDefinition(layers)
        maplayers = "\n".join(xml.toString().split("\n")[3:-3])
        layer_tree_layer = ""
        custom_order = ""
        legend_layer = ""
        layer_coordinate_transform = ""
        for layer in layers:
            is_visible = layer.name() in visible_maps
            values = {'name': layer.name(), 'id': layer.id(), 'visible': ('1' if is_visible else '0'), 'checked': ('Qt::Checked' if is_visible else 'Qt::Unchecked')}
            custom_order += "<item>%s</item>" % layer.id()
            layer_tree_layer += """
            <layer-tree-layer expanded="1" checked="%(checked)s" id="%(id)s" name="%(name)s">
                <customproperties/>
            </layer-tree-layer>""" % values
            legend_layer += """
            <legendlayer drawingOrder="-1" open="true" checked="%(checked)s" name="%(name)s" showFeatureCount="0">
              <filegroup open="true" hidden="false">
                <legendlayerfile isInOverview="0" layerid="%(id)s" visible="%(visible)s"/>
              </filegroup>
            </legendlayer>""" % values
            layer_coordinate_transform += '<layer_coordinate_transform destAuthId="EPSG:3857" srcAuthId="EPSG:3857" srcDatumTransform="-1" destDatumTransform="-1" layerid="%s"/>' % layer.id()
        tpl = ""
        with open(project_template, 'rb') as f:
            tpl = f.read()
        for tag in ['custom_order', 'layer_tree_layer', 'legend_layer', 'layer_coordinate_transform', 'maplayers']:
            tpl = tpl.replace("#%s#" % tag.upper(), locals()[tag])
        return tpl
    else:
        return None


def createOrAddDefaultBasemap(maps, visibleMaps, authcfg=None):
    if os.path.isfile(defaultProjectPath()):
       return addToDefaultProject(maps, visibleMaps, authcfg)
    else:
        template = PROJECT_DEFAULT_TEMPLATE
        prj = createDefaultProject(maps, visibleMaps, template, authcfg)
        if prj is None or prj == '':
            return False

        return writeDefaultProject(prj)

def availableMaps(maps_uri, token):
    """Fetch the list of available maps from BCS endpoint,
    apparently this API method does not require auth"""
    # For testing purposes, we can also access to a json file directly
    if not maps_uri.startswith('http') or token is None:
        j = json.load(open(maps_uri))
    else:
        headers = {}
        headers["Authorization"] = "Bearer {}".format(token)

        nam = NetworkAccessManager()
        res, content = nam.request(maps_uri, headers=headers)
        try:
            j = json.loads(content)
        except:
            raise Exception("Unable to parse server reply.")

    return [l for l in j if isSupported(l)]


def getMapBoxStreetsMap(token):
    mapsUrl = searchUrl = "{}/basemaps?version={}".format(pluginSetting("connectEndpoint"), pluginSetting("apiVersion"))
    allMaps = availableMaps(mapsUrl, token)
    for m in allMaps:
        if m["name"] == "Mapbox Streets":
            return m
    return None


def restoreFromBackup():
    backups = glob.glob(os.path.join(QgsApplication.qgisSettingsDirPath(), "project_default-*.qgs"))
    backups.sort()
    lastBackup = backups[-1]
    shutil.copy2(lastBackup, defaultProjectPath())


def canAccessBasemap(roles):
    return True if "bcs-basemap-boundless" in roles else False
