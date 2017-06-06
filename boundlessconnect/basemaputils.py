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

from qgis.PyQt.QtCore import QSettings
from qgis.PyQt.QtXml import QDomDocument, QDomElement

from qgis.core import (QgsApplication,
                       QgsCoordinateReferenceSystem,
                       QgsMapLayer,
                       QgsRasterLayer
                      )


def isSupported(layer):
    """Check weither the layer is supported by QGIS by excluding vector
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
        connstring = u'type=xyz&url=%(url)s'
        if authcfg is not None:
            connstring = u'authcfg=%(authcfg)s&' + connstring
        layer = QgsRasterLayer(connstring % {
            'url': urllib2.quote(m['endpoint']),
            'authcfg': authcfg,
        }, m['name'], 'wms')
        # I've no idea why the following is required even if the crs is specified
        # in the layer definition
        layer.setCrs(QgsCoordinateReferenceSystem('EPSG:3857'))
        layers.append(layer)

   # open default project
    with open(defaultProjectPath()) as f:
        content = f.read()

    doc = QDomDocument()
    setOk, errorString, errorLine, errorColumn = doc.setContent(content)
    if not setOk:
        return False

    root = doc.documentElement()

    for layer in layers:
        is_visible = layer.name() in visible_maps
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
