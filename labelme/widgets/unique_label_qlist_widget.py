import html
from qtpy import QtWidgets, QtCore
from qtpy.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QListWidgetItem
from PyQt5.QtGui import QMouseEvent
from PyQt5 import QtWidgets
from labelme.shape import Shape
import requests
import threading
import re


class UniqueLabelQListWidget(QtWidgets.QListWidget):  # 假设使用 PyQt5
    def __init__(self, parent=None):
        super(UniqueLabelQListWidget, self).__init__(parent)
        self.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection
        )  # 设置为多选模式

    def mousePressEvent(self, event: QMouseEvent):
        if event.modifiers() & Qt.ControlModifier:
            super().mousePressEvent(event)
        else:
            self.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            super().mousePressEvent(event)
            self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            current_index = self.indexAt(event.pos())
            if not current_index.isValid():
                self.clearSelection()
            else:
                item = self.item(current_index.row())
                if item:
                    self.handle_request(item)
                    # threading.Thread(target=self.handle_request, args=(item,)).start()

    def handle_request(self, item):
        host = self.parent().parent()
        uuid = host.uuid
        server_url = host.server_url
        if isinstance(item, list):
            params = {"prompt": item, "uuid": uuid}
        else:
            item = [item.data(QtCore.Qt.UserRole)]
            params = {"prompt": item, "uuid": uuid}
        try:
            response = requests.get(server_url + "decode/", params=params)
            if response.status_code == 200:
                shapes_list = response.json()["shapes_list"]
                points_list = response.json()["points_list"]
                for label, shape_type, points in zip(item, shapes_list, points_list):
                    if shape_type == "unknown":
                        continue

                    label = label
                    points = points
                    shape_type = shape_type
                    description = host.selected_flags
                    group_id = None
                    other_data = {}

                    if not points:
                        # skip point-empty shape
                        continue

                    shape = Shape(
                        label=label,
                        shape_type=shape_type,
                        group_id=group_id,
                        description=description,
                        mask=None,
                    )
                    for x, y in points:
                        shape.addPoint(QtCore.QPointF(x, y))
                    shape.close()

                    flags = {}
                    for i in range(host.flag_widget.count()):
                        flags[host.flag_widget.item(i).text()] = False
                    flags[host.selected_flags] = True

                    shape.flags = flags
                    shape.other_data = other_data

                    host.labelList.clearSelection()
                    host.canvas.shapes.append(shape)
                    host.canvas.storeShapes()
                    host.canvas.current = None
                    host.canvas.setHiding(False)
                    host.canvas.update()
                    shape = host.canvas.setLastLabel(label, flags)

                    host.addLabel(shape)
                    host.actions.editMode.setEnabled(True)
                    host.actions.undoLastPoint.setEnabled(False)
                    host.actions.undo.setEnabled(True)
                    host.setDirty()
        except:
            pass

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Control:
            self.clearSelection()

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key_Control:
            selected_items = self.selectedItems()
            selected_items = [item.data(QtCore.Qt.UserRole) for item in selected_items]
            self.handle_request(selected_items)

    def findItemByLabel(self, label):
        for row in range(self.count()):
            item = self.item(row)
            if item.data(Qt.UserRole) == label:
                return item

    def createItemFromLabel(self, label):
        if self.findItemByLabel(label):
            raise ValueError("Item for label '{}' already exists".format(label))
        item = QListWidgetItem()
        item.setData(Qt.UserRole, label)
        return item

    def setItemLabel(self, item, label, color=None):
        qlabel = QLabel()
        if color is None:
            qlabel.setText("{}".format(label))
        else:
            qlabel.setText(
                '{} <font color="#{:02x}{:02x}{:02x}">●</font>'.format(
                    html.escape(label), *color
                )
            )
        qlabel.setAlignment(Qt.AlignBottom)
        item.setSizeHint(qlabel.sizeHint())
        self.setItemWidget(item, qlabel)
