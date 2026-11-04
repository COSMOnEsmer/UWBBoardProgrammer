"""Collapsible panels whose live widgets can move into resizable windows."""
from PySide6 import QtCore,QtWidgets as W

class Panel(W.QFrame):
    def __init__(self,title,owner):
        super().__init__();self.setObjectName('Card');self.title=title;self.owner=owner;self.dialog=None;self.collapsed=False
        layout=W.QVBoxLayout(self);layout.setContentsMargins(12,8,12,10)
        header=W.QHBoxLayout();layout.addLayout(header)
        label=W.QLabel(title);label.setObjectName('CardTitle');header.addWidget(label);header.addStretch()
        self.collapse=W.QPushButton('Collapse');self.collapse.clicked.connect(self.toggle);header.addWidget(self.collapse)
        self.detach=W.QPushButton('Detach');self.detach.clicked.connect(self.float_or_dock);header.addWidget(self.detach)
        self.placeholder=W.QLabel('Panel is open in a separate window. Click Attach to restore.');self.placeholder.setWordWrap(True);self.placeholder.hide();layout.addWidget(self.placeholder)
        self.body=W.QWidget();self.body_layout=W.QVBoxLayout(self.body);self.body_layout.setContentsMargins(6,5,6,6);self.body_layout.setSpacing(10);layout.addWidget(self.body)
    def toggle(self):
        self.collapsed=not self.collapsed;self.body.setVisible(not self.collapsed);self.collapse.setText('Expand' if self.collapsed else 'Collapse')
    def float_or_dock(self):
        if self.dialog:self.dialog.close();return
        panel=self
        class Floating(W.QDialog):
            def closeEvent(self,event):panel.restore();event.accept()
        dialog=Floating(self.owner);dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose);dialog.setWindowTitle('UWB Board Programmer · '+self.title)
        dialog.setWindowFlags(dialog.windowFlags()|QtCore.Qt.WindowMinMaxButtonsHint)
        box=W.QVBoxLayout(dialog);box.addWidget(self.body);self.body.show();self.placeholder.show()
        self.collapse.setEnabled(False);self.detach.setText('Attach');self.dialog=dialog
        dialog.resize(max(560,min(self.width(),1200)),max(350,min(self.height()+80,900)));dialog.show()
    def restore(self):
        if not self.dialog:return
        self.dialog.layout().removeWidget(self.body);self.layout().addWidget(self.body);self.body.setVisible(not self.collapsed)
        self.placeholder.hide();self.detach.setText('Detach');self.collapse.setEnabled(True);self.dialog=None

def wrap_remaining_cards(owner):
    """Include metric, calibration and activity-log cards created outside card()."""
    def locate(layout,widget):
        if layout is None:return None
        if layout.indexOf(widget)>=0:return layout
        for i in range(layout.count()):
            nested=layout.itemAt(i).layout()
            found=locate(nested,widget) if nested else None
            if found is not None:return found
        return None
    for frame in list(owner.findChildren(W.QFrame)):
        if isinstance(frame,Panel) or frame.objectName()!='Card':continue
        container=locate(frame.parentWidget().layout(),frame)
        if container is None:continue
        labels=frame.findChildren(W.QLabel)
        title=next((label.text() for label in labels if label.objectName() in ('CardTitle','MetricLabel')),'Panel')
        panel=Panel(title,owner);container.replaceWidget(frame,panel);frame.setObjectName('PanelContent');panel.body_layout.addWidget(frame)
