# -*- coding: utf-8 -*-

"""
***************************************************************************
    buttonlineedit.py
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

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import os

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtCore import pyqtSignal, Qt
from qgis.PyQt.QtWidgets import QLineEdit, QToolButton, QStyle

pluginPath = os.path.split(os.path.dirname(__file__))[0]


class ButtonLineEdit(QLineEdit):
    buttonClicked = pyqtSignal()

    def __init__(self, parent=None):
        super(ButtonLineEdit, self).__init__(parent)

        self.setPlaceholderText("Search")

        self.btnSearch = QToolButton(self)
        self.btnSearch.setIcon(QIcon(os.path.join(pluginPath, "icons", "search.svg")))
        self.btnSearch.setStyleSheet("QToolButton { border: none; padding: 0px; }")
        self.btnSearch.setCursor(Qt.ArrowCursor)
        self.btnSearch.clicked.connect(self.buttonClicked.emit)

        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        buttonSize = self.btnSearch.sizeHint()

        self.setStyleSheet("QLineEdit {{padding-right: {}px; }}".format(buttonSize.width() + frameWidth + 1))
        self.setMinimumSize(max(self.minimumSizeHint().width(), buttonSize.width() + frameWidth * 2 + 2),
                            max(self.minimumSizeHint().height(), buttonSize.height() + frameWidth * 2 + 2))

    def resizeEvent(self, event):
        buttonSize = self.btnSearch.sizeHint()
        frameWidth = self.style().pixelMetric(QStyle.PM_DefaultFrameWidth)
        self.btnSearch.move(self.rect().right() - frameWidth - buttonSize.width(),
                            (self.rect().bottom() - buttonSize.height() + 1) / 2)

        super(ButtonLineEdit, self).resizeEvent(event)
