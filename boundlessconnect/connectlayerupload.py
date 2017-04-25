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
import shutil
import zipfile

from requests.packages.urllib3.filepost import encode_multipart_formdata

from boundlessconnect.networkaccessmanager import NetworkAccessManager
from boundlessconnect.mapboxgl import layerToMapbox
from boundlessconnect import utils

UPLOAD_ENDPOINT_URL = "https://api.dev.boundlessgeo.io/v1/token/"


def publish(layer):
    folder = utils.tempDirName()
    print "EXPORT TO", folder
    layerToMapbox(layer, folder, False)
    exportedFile = utils.tempFilename("layerexport.zip")
    print "ZIP TO", exportedFile

    shutil.make_archive(os.path.splitext(exportedFile)[0], "zip", folder)

    with open(exportedFile, 'rb') as f:
        fileContent = f.read()
    fields = {"file": (os.path.basename(exportedFile), fileContent) }
    payload, content_type = encode_multipart_formdata(fields)

    headers = {}
    headers["Content-Type"] = content_type

    #nam = NetworkAccessManager()
    #res, resText = nam.request(UPLOAD_ENDPOINT_URL, method="POST", body=payload, headers=headers)
