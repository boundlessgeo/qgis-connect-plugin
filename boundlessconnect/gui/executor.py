# -*- coding: utf-8 -*-

"""
***************************************************************************
    executor.py
    ---------------------
    Date                 : March 2016
    Copyright            : (C) 2016 Boundless, http://boundlessgeo.com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Victor Olaya'
__date__ = 'March 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'



from qgis.core import *
from PyQt4 import QtGui, QtCore

def execute(func):
    try:
        QtCore.QCoreApplication.processEvents()
        QtGui.QApplication.setOverrideCursor(QtGui.QCursor(QtCore.Qt.WaitCursor))
        return func()
    finally:
        QtGui.QApplication.restoreOverrideCursor()
        QtCore.QCoreApplication.processEvents()
