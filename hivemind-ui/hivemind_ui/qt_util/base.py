from typing import ClassVar, List, Optional

from PySide2 import QtWidgets, QtGui, QtCore
from PySide2.QtCore import Qt

import hivemind_ui.app as app
from hivemind_ui.qt_util.chain_wrapper import ChainingWrapper
import hivemind_ui.qt_util.qt_xml as qt_xml


class MetaBox(qt_xml.XmlComponent):
    def __init__(self, layout_type: ClassVar[QtWidgets.QBoxLayout]):
        super().__init__()
        self._layout: QtWidgets.QBoxLayout = layout_type()
        self._layout.setMargin(0)  # I like these defaults better
        self._layout.setSpacing(0)
        self.setLayout(self._layout)
        self._items: List[QtWidgets.QWidget] = []
        
        self.setSpacing = self._layout.setSpacing
        self.setAlignment = self._layout.setAlignment

    def addWidget(self, widget: QtWidgets.QWidget, stretch: Optional[int] = None) -> ChainingWrapper:
        self._layout.addWidget(widget)
        self._items.append(widget)
        if stretch is not None:
            self._layout.setStretch(len(self) - 1, stretch)
        return ChainingWrapper(widget)
        
    def removeWidget(self, widget: QtWidgets.QWidget):
        idx = self._layout.indexOf(widget)
        self._layout.removeWidget(widget)
        self._items.pop(idx)
        
    def replaceWidget(self, widget_from: QtWidgets.QWidget, widget_to: QtWidgets.QWidget):
        idx = self._layout.indexOf(widget_from)
        self._layout.replaceWidget(widget_from, widget_to)
        self._items[idx] = widget_to
        
    def __len__(self):
        return len(self._items)

    def __getitem__(self, idx: int) -> QtWidgets.QWidget:
        return self._items[idx]
        
    # No setitem


@qt_xml.register('HBox')
class HBox(MetaBox):
    def __init__(self):
        super().__init__(QtWidgets.QHBoxLayout)


@qt_xml.register('VBox')
class VBox(MetaBox):
    def __init__(self):
        super().__init__(QtWidgets.QVBoxLayout)


class NavButton(VBox):
    text: str
    panel_class: ClassVar

    def __init__(self):
        super().__init__()
        self._layout.setAlignment(Qt.AlignBottom)

        self.addWidget(QtWidgets.QWidget(), 1)
        self.addWidget(QtWidgets.QLabel(self.text), 0).setAlignment(Qt.AlignCenter)

        self._panel_class = self.panel_class

        self.show()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        window = app.get_root()
        window.set_panel(self._panel_class)

