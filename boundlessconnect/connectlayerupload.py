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


from boundlessconnect.networkaccessmanager import NetworkAccessManager
from boundlessconnect import utils

UPLOAD_ENDPOINT_URL = "https://api.dev.boundlessgeo.io/v1/token/"


def upload(layer):
    token = utils.getToken(UPLOAD_ENDPOINT_URL)

    headers = {}
    headers["Authorization"] = "Bearer {}".format(token)
    headers["Content-Type"] = "multipart/form-data; boundary={}".format(boundary)

    nam = NetworkAccessManager()
    res, resText = nam.request(UPLOAD_ENDPOINT_URL, method="POST", body=body, headers=headers)
