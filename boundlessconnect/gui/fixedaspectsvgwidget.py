# -*- coding: utf-8 -*-

"""
***************************************************************************
    fixedaspectsvgwidget.py
    ---------------------
    Date                 : August 2016
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

__author__ = 'Alexander Bruy'
__date__ = 'August 2016'
__copyright__ = '(C) 2016 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.PyQt.QtCore import QRect
from qgis.PyQt.QtGui import QPainter
from qgis.PyQt.QtSvg import QSvgWidget


class FixedAspectSvgWidget(QSvgWidget):

    def paintEvent(self, event):
        painter = QPainter(self)

        painter.setViewport(self.centeredViewport(self.size()))
        self.renderer().render(painter)

    def centeredViewport(self, size):
        width = size.width()
        height = size.height()

        aspectRatio = float(self.renderer().defaultSize().width()) / float(self.renderer().defaultSize().height())

        heightFromWidth = int(width / aspectRatio)
        widthFromHeight = int(height * aspectRatio)

        if heightFromWidth <= height:
            return QRect(0, (height - heightFromWidth) / 2, width, heightFromWidth)
        else:
            return QRect((width - widthFromHeight) / 2, 0, widthFromHeight, height)
