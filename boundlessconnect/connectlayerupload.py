# -*- coding: utf-8 -*-

"""
***************************************************************************
    connectlayerupload.py
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
from builtins import object

__author__ = 'Alexander Bruy'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os
import json
import shutil
import zipfile

from requests.packages.urllib3.filepost import encode_multipart_formdata

from boundlessconnect.networkaccessmanager import NetworkAccessManager
from boundlessconnect.mapboxgl import layerToMapbox
from boundlessconnect import utils

UPLOAD_ENDPOINT_URL = "https://dev.lyrs.boundlessgeo.com/api/layers"


def publish(layer):
    folder = utils.tempDirName()
    layerToMapbox(layer, folder, False)
    exportedFile = utils.tempFilename("layerexport.zip")

    shutil.make_archive(os.path.splitext(exportedFile)[0], "zip", folder)

    with open(exportedFile, 'rb') as f:
        fileContent = f.read()
    fields = {"name": layer.name(),
              "source": (os.path.basename(exportedFile), fileContent)}
    payload, content_type = encode_multipart_formdata(fields)

    headers = {}
    headers["Content-Type"] = content_type

    nam = NetworkAccessManager()
    res, resText = nam.request(UPLOAD_ENDPOINT_URL, method="POST", body=payload, headers=headers)
    data = json.loads(resText)

    url = data["params"]["data"]["s3Url"]
    metadata = {"name": layer.name(),
                "source": {"url": url}
               }

    if register(metadata):
        return True, data["id"]
    else:
        return False, None


def register(metadata):
    headers = {}
    headers["Content-Type"] = "application/json"

    res, resText = nam.request(UPLOAD_ENDPOINT_URL, method="POST", body=metadata, headers=headers)
    response = json.loads(resText)
    if response["type"] == "REGISTER_LAYER_SUCCEEDED":
        return True
    else:
        return False


def delete(layerId):
    nam = NetworkAccessManager()
    res, resText = nam.request("{}/{}".format(UPLOAD_ENDPOINT_URL, layerId), method="DELETE")
    print resText
    return True
