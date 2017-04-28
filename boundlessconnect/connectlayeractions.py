# -*- coding: utf-8 -*-

"""
***************************************************************************
    connectlayeractions.py
    ---------------------
    Date                 : March 2017
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
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import json
from json.decoder import JSONDecoder
from json.encoder import JSONEncoder

from functools import partial

from qgis.PyQt.QtWidgets import QAction

from qgis.core import QgsMapLayer
from qgis.utils import iface

from boundlessconnect import connectlayerupload
from boundlessconnect import utils


connectLayers = list()


class encoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


def decoder(jsonobj):
    if 'source' in jsonobj:
        return ConnectLayer(jsonobj['source'],
                            jsonobj['connectId'])
    else:
        return jsonobj


class ConnectLayer(object):
    def __init__(self, source, connectId):
        self.source = source
        self.connectId = connectId


def isConnectLayer(layer):
    for lay in connectLayers:
        if lay.source == layer.source():
            return True
    return False


def updateLayerActions(layer):
    removeLayerActions(layer)

    if isConnectLayer(layer):
        action = QAction("Remove from Connect", iface.legendInterface())
        action.triggered.connect(partial(removeLayerFromConnect, layer))

        if layer.type() == QgsMapLayer.RasterLayer:
            action.setEnabled(False)

        iface.legendInterface().addLegendLayerAction(action, "Connect", "id1", QgsMapLayer.VectorLayer, False)
        iface.legendInterface().addLegendLayerActionForLayer(action, layer)
        layer.connectActions = [action]
    else:
        action = QAction("Publish to Connect", iface.legendInterface())
        action.triggered.connect(partial(publishLayerToConnect, layer))

        if layer.type() == QgsMapLayer.RasterLayer:
            action.setEnabled(False)

        iface.legendInterface().addLegendLayerAction(action, "Connect", "id1", QgsMapLayer.VectorLayer, False)
        iface.legendInterface().addLegendLayerActionForLayer(action, layer)
        layer.connectActions = [action]


def removeLayerActions(layer):
    try:
        for action in layer.connectActions:
            iface.legendInterface().removeLegendLayerAction(action)
        layer.connectActions = []
    except AttributeError:
        pass


def readConnectLayers():
    try:
        global connectLayers
        fileName = os.path.join(utils.userFolder(), 'connectlayers')
        if os.path.exists(filename):
            with open(filename) as f:
                lines = f.readlines()
            jsonstring = '\n'.join(lines)
            if jsonstring:
                connectLayers = JSONDecoder(object_hook=decoder).decode(jsonstring)
    except KeyError:
        pass


def addConnectLayer(layer, connectLayerId):
    global connectLayers

    layer = ConnectLayer(layer.source(), connectLayerId)
    if layer not in connectLayers:
        for lay in connectLayers:
            if lay.source == layer.source():
                connectLayers.remove(lay)
        connectLayers.append(layer)

    saveConnectLayers()


def removeConnectLayer(layer):
    global connectLayers

    for i, obj in enumerate(connectLayers):
        if obj.source == layer.source():
            del connectLayers[i]
            saveConnectLayers()


def saveConnectLayers():
    fileName = os.path.join(utils.userFolder(), 'connectlayers')
    with open(fileName, 'w') as f:
        f.write(json.dumps(connectLayers, cls=encoder))


def connectId(layer):
    global connectLayers

    for lay in connectLayers:
        if lay.source == layer.source():
            return lay.connectId
    return None


def publishLayerToConnect(layer):
    ok, layerId = connectlayerupload.publish(layer)
    if ok:
        addConnectLayer(layer, layerId)
        updateLayerActions(layer)


def removeLayerFromConnect(layer):
    layerId = connectId(layer)
    if connectlayerupload.delete(layerId):
        removeConnectLayer(layer)
        updateLayerActions(layer)
