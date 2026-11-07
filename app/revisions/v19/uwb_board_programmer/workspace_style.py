"""Quiet typography and surfaces shared by all six hardware workflows."""
from PySide6 import QtCore,QtWidgets as W

TOKENS=dict(background='#f4f7fa',surface='#ffffff',ink='#172b42',muted='#66788c',accent='#087f94',nav='#11283f',border='#dce5ee')
STYLE='''
QWidget {font-family:'Segoe UI','Tahoma';font-size:13px;color:#263c50;}
QFrame#Sidebar {background:#11283f;}
QListWidget#Navigation::item {padding:11px 12px;margin:3px 0;border-radius:7px;}
QListWidget#Navigation::item:selected {background:#087f94;color:white;}
QLabel#PageTitle {font-size:27px;font-weight:650;color:#172b42;}
QLabel#PageSubtitle {font-size:13px;color:#66788c;}
QLabel#CardTitle {font-size:16px;font-weight:650;color:#172b42;}
QLabel#BodyText {font-size:12px;color:#66788c;}
QFrame#Card,QFrame#PanelHeader {background:white;border:0;border-radius:8px;}
QFrame#PanelHeader {border-bottom:1px solid #eef2f6;}
QDockWidget {background:white;border:1px solid #dce5ee;border-radius:9px;}
QMainWindow#DockWorkspace {background:#f4f7fa;}
QMainWindow::separator {background:#e2e9f0;width:8px;height:8px;}
QMainWindow::separator:hover {background:#7bc2cc;}
QPushButton {border:1px solid #d5e0e9;border-radius:6px;padding:7px 12px;font-weight:600;color:#27445c;background:white;}
QPushButton:hover {background:#edf7f9;border-color:#90c4cd;}
QPushButton[variant="primary"] {background:#087f94;border-color:#087f94;color:white;}
QPushButton[variant="primary"]:hover {background:#066c7f;}
QPushButton#PanelAction {border:0;background:transparent;color:#6b7d90;font-size:11px;padding:4px 7px;min-height:20px;}
QPushButton#PanelAction:hover {background:#edf7f9;color:#087f94;}
QHeaderView::section {background:#edf2f7;color:#485e73;font-size:11px;font-weight:600;padding:8px 9px;border:0;border-bottom:1px solid #dce5ee;}
QTableWidget {border:1px solid #e2e8ef;border-radius:6px;alternate-background-color:#f7f9fc;}
QLabel#FieldLabel {font-size:11px;color:#62788e;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox {padding:6px 9px;border:1px solid #d5e0e9;border-radius:5px;min-height:17px;}
QLabel#MetricValue {font-size:30px;color:#172b42;font-weight:600;}
QLabel#StatusBadge {border-radius:6px;padding:6px 10px;}
QPushButton:disabled,QPushButton[variant="primary"]:disabled {background:#f1f4f8;border-color:#e3e9f0;color:#a0aebe;}
QPushButton#PanelAction:disabled {background:transparent;border:0;color:#a0aebe;}
'''

def polish(owner):
    owner.setStyleSheet(owner.styleSheet()+STYLE);owner.log_toggle.hide()
    owner.navigation.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
    for label in owner.findChildren(W.QLabel):
        if label.objectName() in ('BodyText','FieldLabel'):label.setSizePolicy(W.QSizePolicy.Preferred,W.QSizePolicy.Maximum)
    for panelset in owner.workspace_panels:
        for dock in panelset.values():
            panel=dock.widget()
            if panel.title=='Auto Survey':
                for label in panel.body.findChildren(W.QLabel):
                    if label.objectName()=='CardTitle':label.hide()
                for text in ['1   Keep anchors fixed at their installation points.','2   Mark four measured Tag reference points.','3   Capture ranges, review coordinates, then save.']:
                    label=W.QLabel(text);label.setObjectName('BodyText');label.setWordWrap(True);panel.body_layout.insertWidget(panel.body_layout.count()-1,label)
    owner.anchor_table.horizontalHeader().setMinimumSectionSize(58)
    owner.anchor_table.horizontalHeader().setStretchLastSection(True)
    owner.setDockOptions(W.QMainWindow.AnimatedDocks|W.QMainWindow.AllowNestedDocks)
