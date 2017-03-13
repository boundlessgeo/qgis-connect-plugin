# -*- coding: utf-8 -*-

"""
***************************************************************************
    checkcombobox.py
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
from builtins import str

__author__ = 'Alexander Bruy'
__date__ = 'March 2017'
__copyright__ = '(C) 2017 Boundless, http://boundlessgeo.com'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.PyQt.QtGui import QStandardItemModel
from qgis.PyQt.QtWidgets import QComboBox


class CheckableItemsModel(QStandardItemModel):

    checkStateChanged = pyqtSignal()

    def __init__(self, parent=None):
        super(CheckableItemsModel, self).__init__(parent)

    def flags(self, index):
        return super(CheckableItemsModel, self).flags(index) | Qt.ItemIsUserCheckable

    def data(self, index, role=Qt.DisplayRole):
        value = super(CheckableItemsModel, self).data(index, role)
        if index.isValid() and role == Qt.CheckStateRole and value is None:
            value = Qt.Unchecked
        return value

    def setData(self, index, value, role=Qt.EditRole):
        ok = super(CheckableItemsModel, self).setData(index, value, role)
        if ok and role == Qt.CheckStateRole:
            self.checkStateChanged.emit()

        return ok


class CheckComboBox(QComboBox):

    checkedItemsChanged = pyqtSignal(list)

    def __init__(self, parent=None):
        super(CheckComboBox, self).__init__(parent)

        # workaround for Mac and GTK to show checkboxes
        self.setStyleSheet('QComboBox { combobox-popup: 1px }')

        self.defaultText = ''
        self.separator = ','
        self.containerPressed = False

        self.checkableModel = CheckableItemsModel(self)
        self.setModel(self.checkableModel)

        self.model().checkStateChanged.connect(self.updateCheckedItems)
        self.model().rowsInserted.connect(self.updateCheckedItems)
        self.model().rowsRemoved.connect(self.updateCheckedItems)

        self.activated.connect(self.toggleCheckState)

    def itemCheckState(self, index):
        return self.itemData(index, Qt.CheckStateRole)

    def setItemCheckState(self, index, state):
        self.setItemData(index, state, Qt.CheckStateRole)

    def checkedItems(self):
        items = list()
        if self.model():
            index = self.model().index(0, self.modelColumn(), self.rootModelIndex())
            indexes = self.model().match(index, Qt.CheckStateRole, Qt.Checked, -1, Qt.MatchExactly)
            for i in indexes:
                items.append(index.data())

        return items

    def setCheckedItems(self, items):
        for i in items:
            index = self.findText(i)
            self.setItemCheckState(index, Qt.Checked if index != -1 else Qt.Unchecked)

    def updateCheckedItems(self):
        items = self.checkedItems()
        if len(items) == 0:
            self.setEditText(self.defaultText)
        else:
            self.setEditText(self.separator.join(items))

        self.checkedItemsChanged.emit(items)

    def toggleCheckState(self, index):
        value = self.itemData(index, Qt.CheckStateRole)
        if value is not None:
            self.setItemData(index, Qt.Checked if value == Qt.Unchecked else Qt.Unchecked, Qt.CheckStateRole)
