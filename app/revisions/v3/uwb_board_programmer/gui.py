import json,math,os,sys,threading,time,webbrowser
from pathlib import Path
from PySide6 import QtCore,QtGui,QtWidgets as W
from .models import Profile,Anchor,save_new,unique_path,utc
from .serial_io import ports
from .flashing import Flasher,bundles,images
from .controller import Controller
from .cloud import CloudClient,pull_config,validate_scope
from .recording import replay
from .positioning import calibrate_rotation
from . import credentials
from .i18n import Translator, localize_widgets

URL='https://uwb.mangosgo.com/?siteId=ca29a1a6-76c5-48ed-9c9a-e4615fcb4d09&floorId=58afbe99-a0a9-4fd2-ba69-4bf9acc96f6a'

STYLE = """
QWidget {font-family:'Segoe UI','Tahoma';font-size:13px;color:#25354b;}
QMainWindow,QWidget#Workspace,QWidget#Page,QScrollArea,QScrollArea>QWidget>QWidget {background:#f4f7fb;}
QFrame#Sidebar {background:#112239;border:0;}
QLabel#Brand {font-size:18px;font-weight:700;color:#ffffff;}
QLabel#BrandSub {color:#93a9c2;font-size:12px;}
QLabel#SidebarLabel {color:#7189a5;font-size:10px;font-weight:600;}
QLabel#SidebarFoot {color:#92a8c2;font-size:11px;}
QListWidget#Navigation {background:transparent;border:0;outline:0;color:#a8bbd2;font-size:13px;}
QListWidget#Navigation::item {padding:12px 14px;border-radius:8px;margin:3px 0;}
QListWidget#Navigation::item:hover {background:#1b3451;color:white;}
QListWidget#Navigation::item:selected {background:#245de8;color:white;}
QLabel#Eyebrow {color:#647b98;font-size:10px;font-weight:600;}
QLabel#PageTitle {font-size:27px;font-weight:700;color:#14283f;}
QLabel#PageSubtitle,QLabel#BodyText {color:#66788f;font-size:12px;}
QLabel#StatusBadge {background:#e7edf5;color:#526780;border:1px solid #dbe4ef;border-radius:12px;padding:5px 11px;font-size:11px;font-weight:600;}
QLabel#StatusBadge[active="true"] {background:#e0f4ef;color:#137861;border:1px solid #c1e8dc;}
QLabel#Banner {color:#657891;font-size:11px;}
QFrame#Card {background:white;border:1px solid #e0e7f0;border-radius:10px;}
QLabel#CardTitle {font-size:14px;font-weight:600;color:#243a56;background:transparent;}
QLabel#FieldLabel {color:#63758d;font-size:11px;font-weight:600;}
QLabel#MetricValue {color:#182f4c;font-size:34px;font-weight:600;}
QLabel#MetricLabel {color:#6b7d94;font-size:11px;font-weight:600;}
QLabel#MetricUnit {color:#7b8ea5;font-size:12px;}
QPushButton {background:#ffffff;border:1px solid #d7e1ed;border-radius:6px;padding:8px 13px;color:#334c6a;font-weight:600;}
QPushButton:hover {background:#f1f6ff;border-color:#a6bfe6;}
QPushButton:pressed {background:#e6effe;}
QPushButton[variant="primary"] {background:#245de8;border:1px solid #245de8;color:white;}
QPushButton[variant="primary"]:hover {background:#194ed0;border-color:#194ed0;}
QPushButton[variant="danger"] {background:#fff5f4;border-color:#f3d4ce;color:#b74635;}
QPushButton:disabled {background:#f3f5f8;border-color:#e5eaf1;color:#a3afc0;}
QLineEdit,QComboBox,QSpinBox,QDoubleSpinBox {background:white;border:1px solid #d8e2ee;border-radius:5px;padding:7px 9px;selection-background-color:#245de8;min-height:18px;}
QLineEdit:focus,QComboBox:focus,QSpinBox:focus,QDoubleSpinBox:focus {border-color:#6a96f0;}
QLineEdit:disabled,QComboBox:disabled,QSpinBox:disabled,QDoubleSpinBox:disabled {background:#f5f7fa;color:#a3afc0;}
QComboBox::drop-down {border:0;width:23px;}
QComboBox::down-arrow {image:url("__ICON_ROOT__/chevron-down.png");width:14px;height:14px;}
QSpinBox::up-button,QDoubleSpinBox::up-button {subcontrol-origin:border;subcontrol-position:top right;width:24px;border-left:1px solid #e1e8f2;}
QSpinBox::down-button,QDoubleSpinBox::down-button {subcontrol-origin:border;subcontrol-position:bottom right;width:24px;border-left:1px solid #e1e8f2;}
QSpinBox::up-arrow,QDoubleSpinBox::up-arrow {image:url("__ICON_ROOT__/caret-up.png");width:12px;height:12px;}
QSpinBox::down-arrow,QDoubleSpinBox::down-arrow {image:url("__ICON_ROOT__/caret-down.png");width:12px;height:12px;}
QComboBox QAbstractItemView {background:white;color:#25354b;selection-background-color:#e7efff;selection-color:#245de8;outline:0;}
QCheckBox {spacing:8px;}
QTableWidget {background:white;alternate-background-color:#f9fbfe;gridline-color:#e9eef5;border:1px solid #e3eaf3;border-radius:5px;selection-background-color:#edf3ff;selection-color:#1f4bab;}
QTableWidget::item {padding:5px 8px;}
QHeaderView::section {background:#f3f6fa;color:#64768f;font-size:11px;font-weight:600;padding:9px 7px;border:0;border-bottom:1px solid #e0e7f0;}
QTableCornerButton::section {background:#f3f6fa;border:0;}
QPlainTextEdit#ActivityLog {background:#f8fafd;color:#596d87;border:0;font-family:'Consolas';font-size:11px;padding:7px;}
QScrollArea {border:0;}
QScrollBar:vertical {background:transparent;width:8px;margin:2px;}
QScrollBar::handle:vertical {background:#cbd7e6;border-radius:3px;min-height:28px;}
QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical {height:0;}
QScrollBar:horizontal {background:#f4f7fb;height:8px;}
QScrollBar::handle:horizontal {background:#cbd7e6;border-radius:3px;min-width:28px;}
QScrollBar::add-line:horizontal,QScrollBar::sub-line:horizontal {width:0;}
QToolTip {color:#25354b;background:white;border:1px solid #d8e2ee;padding:5px;}
"""

class Signals(QtCore.QObject):
    log=QtCore.Signal(str);fix=QtCore.Signal(dict);done=QtCore.Signal(object);fail=QtCore.Signal(str)

class FloorPlot(W.QWidget):
    def __init__(self):
        super().__init__();self.profile=None;self.trail=[];self.setMinimumHeight(240)
    def set_fix(self,fix):
        self.trail.append((fix['x_m'],fix['y_m']));self.trail=self.trail[-300:];self.update()
    def paintEvent(self,event):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(),QtGui.QColor('#ffffff'))
        if not self.profile:p.end();return
        lo,hi=self.profile.bounds;pad=40
        scale=min(max(1,self.width()-2*pad)/(hi[0]-lo[0]),max(1,self.height()-2*pad)/(hi[1]-lo[1]))
        pw=(hi[0]-lo[0])*scale;ph=(hi[1]-lo[1])*scale
        left=(self.width()-pw)/2;top=(self.height()-ph)/2
        def point(x,y):return QtCore.QPointF(left+(x-lo[0])*scale,top+ph-(y-lo[1])*scale)
        area=QtCore.QRectF(left,top,pw,ph)
        p.fillRect(area,QtGui.QColor('#f8fafd'))
        p.setPen(QtGui.QPen(QtGui.QColor('#e8eef6'),1))
        for i in range(1,10):
            x=lo[0]+(hi[0]-lo[0])*i/10;p.drawLine(point(x,lo[1]),point(x,hi[1]))
        for i in range(1,5):
            y=lo[1]+(hi[1]-lo[1])*i/5;p.drawLine(point(lo[0],y),point(hi[0],y))
        p.setPen(QtGui.QColor('#d4dfed'));p.drawRect(area)
        p.setFont(QtGui.QFont('Segoe UI',9));p.setPen(QtGui.QColor('#71849d'))
        p.drawText(QtCore.QPointF(left,top+ph+23),f'{lo[0]:g}, {lo[1]:g} m')
        p.drawText(QtCore.QPointF(left+pw-65,top+ph+23),f'X {hi[0]:g} m')
        p.drawText(QtCore.QPointF(left,top-9),f'Y {hi[1]:g} m')
        p.setPen(QtGui.QPen(QtGui.QColor('#15958b'),2))
        for a,b in zip(self.trail,self.trail[1:]):p.drawLine(point(*a),point(*b))
        for a in self.profile.anchors:
            if a.position is None:continue
            q=point(*a.position[:2]);p.setPen(QtCore.Qt.NoPen);p.setBrush(QtGui.QColor('#dfeaff'));p.drawEllipse(q,12,12)
            p.setBrush(QtGui.QColor('#245de8'));p.drawEllipse(q,5,5);p.setPen(QtGui.QColor('#425977'));p.drawText(q+QtCore.QPointF(13,-8),a.id)
        if self.trail:
            q=point(*self.trail[-1]);p.setPen(QtCore.Qt.NoPen);p.setBrush(QtGui.QColor('#d3eee9'));p.drawEllipse(q,14,14)
            p.setBrush(QtGui.QColor('#15958b'));p.drawEllipse(q,6,6)
        else:
            p.setPen(QtGui.QColor('#8b9cb1'));p.setFont(QtGui.QFont('Segoe UI',10))
            p.drawText(area,QtCore.Qt.AlignCenter,getattr(self,'translate',str)('Waiting for a valid position'))
        p.end()

class Window(W.QMainWindow):
    def __init__(self,root):
        super().__init__()
        # Explicit registration also supports Qt's offscreen font database.
        for filename in ['segoeui.ttf','segoeuib.ttf','segoeuisl.ttf','tahoma.ttf','tahomabd.ttf']:
            QtGui.QFontDatabase.addApplicationFont(str(Path(os.environ.get('WINDIR','C:/Windows'))/'Fonts'/filename))
        app=W.QApplication.instance();app.setStyle('Fusion');app.setFont(QtGui.QFont('Segoe UI',10));QtCore.QLocale.setDefault(QtCore.QLocale('en_GB'));self.setLocale(QtCore.QLocale('en_GB'))
        palette=QtGui.QPalette()
        for role,color in [(QtGui.QPalette.Window,'#f4f7fb'),(QtGui.QPalette.WindowText,'#25354b'),(QtGui.QPalette.Base,'#ffffff'),(QtGui.QPalette.AlternateBase,'#f9fbfe'),(QtGui.QPalette.Text,'#25354b'),(QtGui.QPalette.Button,'#ffffff'),(QtGui.QPalette.ButtonText,'#334c6a'),(QtGui.QPalette.Highlight,'#245de8'),(QtGui.QPalette.HighlightedText,'#ffffff')]:palette.setColor(role,QtGui.QColor(color))
        palette.setColor(QtGui.QPalette.Disabled,QtGui.QPalette.Text,QtGui.QColor('#a3afc0'));app.setPalette(palette)
        self.root=Path(root);self.profile=Profile();self.controller=None;self.cloud=None;self.busy=False;self.cal_rows={};self.latest_fix=None;self.pending_done=None
        self.translator=Translator(self.root);self.language=self.translator.load_language();self.log_history=[];self._device_keys=[];self._extra_anchor=None
        self.signals=Signals();self.signals.log.connect(self.log);self.signals.fix.connect(self.show_fix);self.signals.done.connect(self.job_done);self.signals.fail.connect(self.job_fail)
        self.setWindowTitle('UWB Board Programmer | Murata Workspace');self.resize(1340,940);self.setMinimumSize(1080,760);self.setStyleSheet(STYLE.replace('__ICON_ROOT__',str(self.root/'resources/ui-v1').replace('\\','/')))
        self.setWindowIcon(QtGui.QIcon(str(self.root/'resources/branding/logo-v1.ico')))
        center=W.QWidget();center.setObjectName('Workspace');outer=W.QHBoxLayout(center);outer.setContentsMargins(0,0,0,0);outer.setSpacing(0);self.setCentralWidget(center)
        sidebar=W.QFrame();sidebar.setObjectName('Sidebar');sidebar.setFixedWidth(246);sl=W.QVBoxLayout(sidebar);sl.setContentsMargins(18,28,18,22);sl.setSpacing(9);outer.addWidget(sidebar)
        logo=W.QLabel();logo.setPixmap(QtGui.QPixmap(str(self.root/'resources/branding/logo-v1.png')).scaled(54,54,QtCore.Qt.KeepAspectRatio,QtCore.Qt.SmoothTransformation));sl.addWidget(logo);sl.addSpacing(7)
        brand=W.QLabel('UWB Board\nProgrammer');brand.setObjectName('Brand');sl.addWidget(brand)
        sub=W.QLabel('MURATA WORKSPACE');sub.setObjectName('BrandSub');sl.addWidget(sub);sl.addSpacing(30)
        small=W.QLabel('WORKFLOW');small.setObjectName('SidebarLabel');sl.addWidget(small)
        self.navigation=W.QListWidget();self.navigation.setObjectName('Navigation');self.navigation.setFocusPolicy(QtCore.Qt.NoFocus)
        for name in ['01   Devices & firmware','02   Survey & calibration','03   Live positioning','04   RTLS Platform','05   Sessions & replay']:
            item=W.QListWidgetItem(name);item.setSizeHint(QtCore.QSize(180,52));self.navigation.addItem(item)
        sl.addWidget(self.navigation,1)
        small=W.QLabel('HARDWARE');small.setObjectName('SidebarLabel');sl.addWidget(small)
        self.hardware_label=W.QLabel();self.hardware_label.setObjectName('SidebarFoot');sl.addWidget(self.hardware_label);sl.addSpacing(14)
        small=W.QLabel('VERSION 2.0.0\nFirmware validation pending');small.setObjectName('SidebarFoot');sl.addWidget(small)
        body=W.QWidget();body.setObjectName('Workspace');bl=W.QVBoxLayout(body);bl.setContentsMargins(26,24,26,18);bl.setSpacing(13);outer.addWidget(body,1)
        header=W.QHBoxLayout();hl=W.QVBoxLayout();hl.setSpacing(4);header.addLayout(hl,1)
        eyebrow=W.QLabel('KMUTNB  /  HARDWARE WORKSPACE');eyebrow.setObjectName('Eyebrow');hl.addWidget(eyebrow)
        self.page_title=W.QLabel();self.page_title.setObjectName('PageTitle');hl.addWidget(self.page_title)
        self.page_subtitle=W.QLabel();self.page_subtitle.setObjectName('PageSubtitle');self.page_subtitle.setWordWrap(True);hl.addWidget(self.page_subtitle)
        languages=W.QVBoxLayout();languages.setSpacing(5);label=W.QLabel('LANGUAGE');label.setObjectName('FieldLabel');languages.addWidget(label)
        self.language_combo=W.QComboBox();self.language_combo.setObjectName('LanguageSelector');self.language_combo.addItem('English','en');self.language_combo.addItem('ไทย','th');self.language_combo.setCurrentIndex(1 if self.language=='th' else 0);self.language_combo.setMinimumWidth(116);languages.addWidget(self.language_combo);languages.addStretch();header.addLayout(languages);header.addSpacing(10)
        badges=W.QVBoxLayout();badges.setSpacing(6);self.hardware_badge=W.QLabel('Hardware offline');self.hardware_badge.setObjectName('StatusBadge');self.cloud_badge=W.QLabel('Cloud disconnected');self.cloud_badge.setObjectName('StatusBadge');badges.addWidget(self.hardware_badge);badges.addWidget(self.cloud_badge);header.addLayout(badges);bl.addLayout(header)
        self.banner=W.QLabel('Connect boards when ready. Survey anchor positions before acquisition.');self.banner.setObjectName('Banner');self.banner.setWordWrap(True);bl.addWidget(self.banner)
        self.tabs=W.QTabWidget();self.tabs.tabBar().hide();self.tabs.setStyleSheet('QTabWidget::pane{border:0;background:transparent;}');bl.addWidget(self.tabs,1)
        self.setup_page();self.geometry_page();self.live_page();self.cloud_page();self.record_page()
        self.navigation.currentRowChanged.connect(self.tabs.setCurrentIndex);self.tabs.currentChanged.connect(self.navigate);self.navigation.setCurrentRow(0);self.navigate(0)
        log_card=W.QFrame();log_card.setObjectName('Card');ll=W.QVBoxLayout(log_card);ll.setContentsMargins(13,9,13,8);ll.setSpacing(2)
        lr=W.QHBoxLayout();label=W.QLabel('Activity log');label.setObjectName('CardTitle');lr.addWidget(label);lr.addStretch();self.log_toggle=W.QPushButton('Hide log');self.log_toggle.setStyleSheet('padding:2px 8px;font-size:11px;border:0;');lr.addWidget(self.log_toggle);ll.addLayout(lr)
        self.logs=W.QPlainTextEdit();self.logs.setObjectName('ActivityLog');self.logs.setReadOnly(True);self.logs.setMaximumBlockCount(1500);self.logs.setFixedHeight(76);self.logs.setVisible(False);self.log_toggle.setText('Show log');ll.addWidget(self.logs);bl.addWidget(log_card)
        self.log_toggle.clicked.connect(self.toggle_log)
        self.timer=QtCore.QTimer(self);self.timer.timeout.connect(self.refresh_status);self.timer.start(500)
        self.populate_profile();self.refresh_ports();self.refresh_bundles();self.load_latest_credentials();self.refresh_status()
        self.language_combo.currentIndexChanged.connect(self.change_language)
        self.mode_combo.currentIndexChanged.connect(lambda _:self.guard(self.change_mode))
        self.apply_language()
        self.log('Ready. Select a workflow step to begin. Serial ports and cloud connections stay closed until requested.')
    def navigate(self,index):
        headings=[('Devices & firmware','Assign USB ports and prepare your anchors and tag.'),('Survey & calibration','Define the workspace and align measured angles with the floor.'),('Live positioning','Monitor RF synchronization and the latest 3D tag position.'),('RTLS Platform','Connect the hardware gateway to the KMUTNB floor.'),('Sessions & replay','Review recorded measurements without publishing to the cloud.')]
        self.page_title.setText(headings[index][0]);self.page_subtitle.setText(headings[index][1])
        if self.navigation.currentRow()!=index:self.navigation.setCurrentRow(index)
        self.apply_language()
    def toggle_log(self):
        visible=not self.logs.isVisible();self.logs.setVisible(visible);self.log_toggle.setText('Hide log' if visible else 'Show log')
    def page(self,name):
        widget=W.QWidget();widget.setObjectName('Page');layout=W.QVBoxLayout(widget);layout.setContentsMargins(0,0,8,0);layout.setSpacing(14)
        scroll=W.QScrollArea();scroll.setWidgetResizable(True);scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff);scroll.setWidget(widget);self.tabs.addTab(scroll,name);return widget,layout
    def card(self,title,description,layout):
        widget=W.QFrame();widget.setObjectName('Card');inside=W.QVBoxLayout(widget);inside.setContentsMargins(18,15,18,16);inside.setSpacing(10)
        label=W.QLabel(title);label.setObjectName('CardTitle');inside.addWidget(label)
        if description:self.label(description,inside)
        layout.addWidget(widget);return inside
    def button(self,text,fn,layout,variant=None):
        b=W.QPushButton(text);b.setCursor(QtCore.Qt.PointingHandCursor)
        if variant:b.setProperty('variant',variant)
        b.clicked.connect(lambda checked=False:self.guard(fn));layout.addWidget(b);return b
    def line(self,text=''):return W.QLineEdit(text)
    def label(self,text,layout):
        x=W.QLabel(text);x.setObjectName('BodyText');x.setWordWrap(True);layout.addWidget(x);return x
    def table_style(self,table,row_height=42):
        table.verticalHeader().hide();table.verticalHeader().setDefaultSectionSize(row_height);table.setAlternatingRowColors(True);table.setSelectionBehavior(W.QAbstractItemView.SelectRows);table.setShowGrid(False);table.setWordWrap(False)
    def field(self,text,widget,layout):
        box=W.QVBoxLayout();box.setSpacing(5);label=W.QLabel(text);label.setObjectName('FieldLabel');box.addWidget(label);box.addWidget(widget);layout.addLayout(box,1)
    def setup_page(self):
        self.setup_widget,l=self.page('Devices & firmware')
        c=self.card('Device assignment','Identify the model and revision printed on each board. USB flashing requires EVK revision 3 or later.',l)
        row=W.QHBoxLayout();c.addLayout(row);self.mode_combo=W.QComboBox();self.mode_combo.setObjectName('PositioningMode');self.mode_combo.addItem('3 anchors · TDoA + AoA (3D)','hybrid_3');self.mode_combo.addItem('4 anchors · TDoA (3D)','tdoa_4');self.field('POSITIONING MODE',self.mode_combo,row)
        self.mode_note=W.QLabel();self.mode_note.setObjectName('BodyText');self.mode_note.setWordWrap(True);c.addWidget(self.mode_note)
        self.device_table=W.QTableWidget(0,4);self.device_table.setHorizontalHeaderLabels(['DEVICE / ROLE','USB PORT','EVK REVISION','FIRMWARE']);self.table_style(self.device_table,46)
        self.device_table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch);c.addWidget(self.device_table);self.port_boxes=[];self.rev_boxes=[]
        row=W.QHBoxLayout();c.addLayout(row);self.button('Refresh ports',self.refresh_ports,row);row.addStretch();self.label('Ports stay closed until you request an operation.',row)
        c=self.card('Firmware deployment','The app checks image hashes, verifies the flash, then reads the board identity over USB.',l)
        row=W.QHBoxLayout();c.addLayout(row);self.firmware_combo=W.QComboBox();row.addWidget(self.firmware_combo,1);self.button('Reload bundles',self.refresh_bundles,row)
        row=W.QHBoxLayout();c.addLayout(row);self.target=W.QComboBox();row.addWidget(self.target,1)
        self.flash_button=self.button('Flash selected board',self.flash_selected,row,'primary');self.flash_all_button=self.button('Flash all anchors',self.flash_all,row)
        c=self.card('Standalone tag settings','The tag workflow saves these settings, installs the battery image and verifies them again before you disconnect USB.',l)
        row=W.QHBoxLayout();c.addLayout(row);self.tag_mac=self.line();self.tag_mac.setPlaceholderText('16 hexadecimal digits');self.field('TAG MAC ADDRESS',self.tag_mac,row)
        self.blink=W.QSpinBox();self.blink.setRange(100,10000);self.blink.setSuffix(' ms');self.field('BLINK INTERVAL',self.blink,row);l.addStretch()
    def geometry_page(self):
        self.geometry_widget,l=self.page('Survey & calibration')
        c=self.card('Anchor geometry','Use surveyed coordinates in metres in the RTLS floor frame. Positive Z points upward.',l)
        self.anchor_table=W.QTableWidget(3,12);self.anchor_table.setHorizontalHeaderLabels(['ANCHOR ID','MAC ADDRESS','ROLE','X (m)','Y (m)','Z (m)','YAW','PITCH','ROLL','RX BIAS','3D AoA','ANGLES']);self.table_style(self.anchor_table,43)
        self.anchor_table.horizontalHeader().setSectionResizeMode(W.QHeaderView.ResizeToContents);self.anchor_table.horizontalHeader().setMinimumSectionSize(57);self.anchor_table.setFixedHeight(181);c.addWidget(self.anchor_table)
        c=self.card('Workspace profile','IDs and bounds must match the floor used in RTLS.',l)
        self.site=self.line();self.floor=self.line();self.tag_id=self.line();self.bounds=self.line()
        row=W.QHBoxLayout();c.addLayout(row);self.field('SITE ID',self.site,row);self.field('FLOOR ID',self.floor,row)
        row=W.QHBoxLayout();c.addLayout(row);self.field('TAG ID',self.tag_id,row);self.field('BOUNDS [[xmin,ymin,zmin],[xmax,ymax,zmax]]',self.bounds,row)
        row=W.QHBoxLayout();c.addLayout(row);self.button('Save new profile',self.save_profile,row,'primary');self.button('Load profile',self.load_profile,row);self.button('Export RTLS anchor setup',self.export_cloud,row);row.addStretch()
        g=self.card('Orientation calibration','Capture at least three different known tag directions, including different heights. Verify the fitted angles at other reference points before enabling 3D AoA. Four-anchor TDoA ignores AoA.',l)
        row=W.QHBoxLayout();g.addLayout(row);self.cal_anchor=W.QComboBox();self.cal_anchor.addItems(['A1','A2','A3']);row.addWidget(self.cal_anchor)
        self.reference_xyz=self.line();self.reference_xyz.setPlaceholderText('Reference tag X, Y, Z in metres');row.addWidget(self.reference_xyz,1)
        self.button('Capture angles',self.capture_reference,row);self.button('Fit orientation',self.fit_orientation,row)
        row=W.QHBoxLayout();g.addLayout(row);self.button('Import references',self.import_calibration,row);self.cal_count=W.QLabel('0 references');self.cal_count.setObjectName('BodyText');row.addWidget(self.cal_count);row.addStretch()
        self.label('Open Diagnostic mode in Live positioning to capture angles. Azimuth runs from local +X toward +Y; elevation runs toward +Z. Check the actual EVK axes first.',g)
        c=self.card('Measurement quality','Set noise estimates and the maximum accepted vertical uncertainty from your reference measurements.',l)
        row=W.QHBoxLayout();c.addLayout(row);self.sigma_a=W.QDoubleSpinBox();self.sigma_a.setRange(.1,90);self.sigma_a.setSuffix(' deg');self.field('AoA STANDARD DEVIATION',self.sigma_a,row)
        self.sigma_t=W.QDoubleSpinBox();self.sigma_t.setRange(.001,10);self.sigma_t.setDecimals(3);self.sigma_t.setSuffix(' m');self.field('TDoA STANDARD DEVIATION',self.sigma_t,row)
        self.max_z=W.QDoubleSpinBox();self.max_z.setRange(.01,10);self.max_z.setSuffix(' m');self.field('MAXIMUM Z 95% UNCERTAINTY',self.max_z,row);l.addStretch()
    def live_page(self):
        _,l=self.page('Live positioning');c=self.card('Acquisition','Open the surveyed hardware profile, then start all configured anchors.',l);row=W.QHBoxLayout();c.addLayout(row)
        self.open_button=self.button('Open anchors + record',lambda:self.open_anchors(False),row,'primary');self.diagnostic_button=self.button('Diagnostic mode',lambda:self.open_anchors(True),row)
        self.start_button=self.button('Start anchors',self.start_anchors,row,'primary');self.stop_button=self.button('Stop',self.stop_anchors,row,'danger');self.close_button=self.button('Close ports',self.close_anchors,row)
        self.live_status=W.QLabel('Serial ports closed');self.live_status.setObjectName('BodyText');self.live_status.setWordWrap(True);c.addWidget(self.live_status)
        row=W.QHBoxLayout();row.setSpacing(12);l.addLayout(row);self.position_values={}
        for axis,description in [('X','FLOOR X'),('Y','FLOOR Y'),('Z','HEIGHT')]:
            frame=W.QFrame();frame.setObjectName('Card');ml=W.QVBoxLayout(frame);ml.setContentsMargins(18,13,18,13);label=W.QLabel(f'{axis}  /  {description}');label.setObjectName('MetricLabel');ml.addWidget(label)
            mr=W.QHBoxLayout();value=W.QLabel('--');value.setObjectName('MetricValue');mr.addWidget(value);unit=W.QLabel('m');unit.setObjectName('MetricUnit');mr.addWidget(unit);mr.addStretch();ml.addLayout(mr);self.position_values[axis]=value;row.addWidget(frame,1)
        self.xyz=W.QLabel();self.xyz.hide()
        self.quality=W.QLabel('No fix yet. Waiting for synchronized RF measurements.');self.quality.setObjectName('BodyText');self.quality.setWordWrap(True);l.addWidget(self.quality)
        row=W.QHBoxLayout();row.setSpacing(14);l.addLayout(row,1)
        map_container=W.QVBoxLayout();row.addLayout(map_container,3);c=self.card('Floor view','Floor-local metres  |  blue: anchors  |  teal: tag',map_container);self.plot=FloorPlot();c.addWidget(self.plot,1)
        side=W.QVBoxLayout();row.addLayout(side,2);c=self.card('Clock synchronization','Slave clocks are corrected using RF SYNC timestamps.',side)
        self.clock_table=W.QTableWidget(2,4);self.clock_table.setHorizontalHeaderLabels(['SLAVE','SAMPLES','DRIFT ppm','RMS ns']);self.table_style(self.clock_table,39);self.clock_table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch);self.clock_table.setFixedHeight(120);c.addWidget(self.clock_table)
        self.angle_status=W.QLabel('Waiting for tag azimuth, elevation and FOM.');self.angle_status.setObjectName('BodyText');self.angle_status.setWordWrap(True);c.addWidget(self.angle_status)
        self.label('Every anchor must receive the same BLINK with fresh RF clock synchronization. Hybrid mode also requires verified 3D AoA. USB arrival times are not used for TDoA.',c);c.addStretch()
    def cloud_page(self):
        self.cloud_widget,l=self.page('RTLS Platform')
        c=self.card('Hardware gateway','Use a separate gateway and anchor IDs for the real Murata boards on KMUTNB / 2nd Floor.',l)
        self.gateway_id=self.line();self.gateway_id.setPlaceholderText('Gateway ID issued by RTLS');self.token=self.line();self.token.setEchoMode(W.QLineEdit.Password);self.token.setPlaceholderText('Gateway bearer token')
        row=W.QHBoxLayout();c.addLayout(row);self.field('GATEWAY ID',self.gateway_id,row)
        row=W.QHBoxLayout();c.addLayout(row);self.field('BEARER TOKEN',self.token,row)
        row=W.QHBoxLayout();c.addLayout(row);self.button('Open dashboard',lambda:webbrowser.open(URL),row);self.button('Register gateway',lambda:webbrowser.open('https://uwb.mangosgo.com/admin/edge-gateways/new'),row);row.addStretch()
        c=self.card('Connection & publishing','The app verifies the site, floor and anchor coordinates, and checks acknowledgements for each event.',l)
        row=W.QHBoxLayout();c.addLayout(row);self.button('Check configuration',self.check_cloud,row);self.button('Save encrypted token',self.save_token,row)
        self.cloud_connect=self.button('Connect RTLS',self.connect_cloud,row,'primary');self.button('Disconnect',self.disconnect_cloud,row)
        self.publish_position=W.QCheckBox('Publish live positions that pass the quality checks');self.publish_position.setChecked(True);c.addWidget(self.publish_position)
        self.publish_raw=W.QCheckBox('Also publish raw BLINK and SYNC measurements');c.addWidget(self.publish_raw)
        self.cloud_status=W.QLabel('RTLS disconnected');self.cloud_status.setObjectName('BodyText');self.cloud_status.setWordWrap(True);c.addWidget(self.cloud_status)
        self.label('Surveyed anchor coordinates must match RTLS within 1 cm. During an outage, local recording continues; only fresh data is published after reconnecting.',c)
        c=self.card('Credential storage','Tokens saved by this app use Windows DPAPI and are tied to your Windows user. Your dashboard password is not a gateway token.',l)
        self.label('Offline replay stays local. No recorded or synthetic positions are published during replay.',c);l.addStretch()
    def record_page(self):
        _,l=self.page('Sessions & replay')
        c=self.card('Measurement sessions','Each session records the profile, serial messages, RF timestamps, SYNC events, positions and rejection reasons in a new JSONL file.',l)
        self.record_status=W.QLabel('No recording session is open.');self.record_status.setObjectName('BodyText');self.record_status.setWordWrap(True);c.addWidget(self.record_status)
        row=W.QHBoxLayout();c.addLayout(row);self.button('Open data folder',lambda:os.startfile(str(self.root/'data')),row);row.addStretch()
        c=self.card('Offline replay','Close serial ports and disconnect RTLS before reviewing a recorded session.',l)
        row=W.QHBoxLayout();c.addLayout(row);self.button('Replay a session',self.replay_session,row,'primary');row.addStretch()
        self.label('Replay keeps the recorded UTC timestamps and recalculates positions locally. It does not connect to RTLS.',c)
        c=self.card('Getting started','The user guide covers firmware deployment, surveying, both positioning modes and hardware acceptance tests.',l)
        row=W.QHBoxLayout();c.addLayout(row);self.button('Open user guide',self.open_guide,row);row.addStretch();l.addStretch()

    def guard(self,fn):
        try:return fn()
        except Exception as e:self.job_fail(str(e))
    def tr(self,text):return self.translator.translate(str(text),self.language)
    def apply_language(self):
        localize_widgets(self,self.tr)
        if hasattr(self,'plot'):self.plot.translate=self.tr;self.plot.update()
    def change_language(self):
        self.language=self.language_combo.currentData();self.translator.save_language(self.language)
        self.apply_language();self.logs.setPlainText('\n'.join(stamp+'  '+self.tr(text) for stamp,text in self.log_history))
    def open_guide(self):os.startfile(str(self.root/('docs/USER_GUIDE_TH.v1.md' if self.language=='th' else 'docs/USER_GUIDE_EN.v1.md')))
    def log(self,text):
        stamp=time.strftime('%H:%M:%S');self.log_history.append((stamp,str(text)));self.log_history=self.log_history[-1500:];self.logs.appendPlainText(stamp+'  '+self.tr(text))
    def job(self,fn,done=None):
        if self.busy:raise ValueError('Another operation is still running')
        self.busy=True;self.pending_done=done;self.refresh_status()
        def work():
            try:self.signals.done.emit(fn())
            except Exception as e:self.signals.fail.emit(str(e))
        threading.Thread(target=work,daemon=True).start()
    def job_done(self,result):
        self.busy=False
        if self.pending_done:self.guard(lambda:self.pending_done(result))
        self.pending_done=None;self.refresh_status()
    def job_fail(self,text):
        self.busy=False;self.log('ERROR: '+text);W.QMessageBox.warning(self,'UWB Board Programmer',self.tr(text))
    def populate_profile(self):
        self.rebuild_device_rows();p=self.profile;self.site.setText(p.site_id);self.floor.setText(p.floor_id);self.tag_id.setText(p.tag_id);self.tag_mac.setText(p.tag_mac);self.blink.setValue(p.blink_interval_ms);self.bounds.setText(json.dumps(p.bounds))
        self.sigma_a.setValue(p.aoa_sigma_deg);self.sigma_t.setValue(p.tdoa_sigma_m);self.max_z.setValue(p.max_z_uncertainty_m)
        for row,a in enumerate(p.anchors):
            values=[a.id,a.mac,a.role,*(a.position if a.position is not None else ['','','']),a.yaw,a.pitch,a.roll,a.rx_bias_m]
            for col,val in enumerate(values):self.anchor_table.setItem(row,col,W.QTableWidgetItem(str(val)))
            verify=W.QCheckBox();verify.setChecked(a.aoa_verified);self.anchor_table.setCellWidget(row,10,verify)
            self.anchor_table.setItem(row,11,W.QTableWidgetItem('—'));self.port_boxes[row].setCurrentText(a.port)
        self.port_boxes[len(p.anchors)].setCurrentText(p.tag_port);self.plot.profile=p;self.plot.update();self.apply_language()
    def rebuild_device_rows(self):
        p=self.profile;n=len(p.anchors)
        revisions={key:box.currentIndex() for key,box in zip(self._device_keys,self.rev_boxes)}
        self._device_keys=[a.id for a in p.anchors]+['__tag__'];self.device_table.setRowCount(n+1);self.port_boxes=[];self.rev_boxes=[]
        for row,key in enumerate(self._device_keys):
            role='Tag' if row==n else p.anchors[row].role.title();label='Type2DK · Tag' if row==n else f'Type2BP A{row+1} · {role}'
            item=W.QTableWidgetItem(label);item.setFlags(item.flags()&~QtCore.Qt.ItemIsEditable);self.device_table.setItem(row,0,item)
            combo=W.QComboBox();combo.setEditable(True);combo.setPlaceholderText('Select a COM port');self.port_boxes.append(combo);self.device_table.setCellWidget(row,1,combo)
            rev=W.QComboBox();rev.addItems(['Unknown']+[str(i) for i in range(1,11)]);rev.setCurrentIndex(revisions.get(key,0));self.rev_boxes.append(rev);self.device_table.setCellWidget(row,2,rev)
            item=W.QTableWidgetItem('Setup + battery' if row==n else role);item.setFlags(item.flags()&~QtCore.Qt.ItemIsEditable);self.device_table.setItem(row,3,item)
        self.device_table.setFixedHeight(46*(n+1)+42);self.anchor_table.setRowCount(n);self.anchor_table.setFixedHeight(43*n+52)
        self.target.clear();self.target.addItems([f'A{i+1} · {a.role.title()}' for i,a in enumerate(p.anchors)]+['Tag · setup + battery'])
        self.cal_anchor.clear();self.cal_anchor.addItems([f'A{i+1}' for i in range(n)]);self.clock_table.setRowCount(n-1);self.clock_table.setFixedHeight(39*(n-1)+42)
        self.mode_combo.blockSignals(True);self.mode_combo.setCurrentIndex(1 if p.mode=='tdoa_4' else 0);self.mode_combo.blockSignals(False)
        self.mode_note.setText('4 Type2BP: 1 master + 3 slaves. TDoA uses no AoA. Survey non-coplanar anchor positions; ambiguous fixes are rejected.' if n==4 else '3 Type2BP: 1 master + 2 slaves. Verify azimuth and elevation on at least one anchor for 3D TDoA + AoA.')
        self.hardware_label.setText(f'{n} x Type2BP anchors\n1 x Type2DK tag')
        self.sigma_a.setEnabled(p.mode=='hybrid_3');self.refresh_ports();self.apply_language()
    def change_mode(self):
        mode=self.mode_combo.currentData()
        if mode==self.profile.mode:return
        if self.controller or self.cloud or self.busy:
            self.mode_combo.blockSignals(True);self.mode_combo.setCurrentIndex(1 if self.profile.mode=='tdoa_4' else 0);self.mode_combo.blockSignals(False)
            raise ValueError('Close COM ports and disconnect RTLS before changing the positioning mode.')
        try:p=self.collect()
        except Exception:
            self.mode_combo.blockSignals(True);self.mode_combo.setCurrentIndex(1 if self.profile.mode=='tdoa_4' else 0);self.mode_combo.blockSignals(False);raise
        if mode=='tdoa_4':p.anchors.append(self._extra_anchor or Anchor('KMUTNB-RF-A4','0200000000000004','slave'))
        else:self._extra_anchor=p.anchors.pop()
        p.mode=mode;self.profile=p;self.populate_profile();self.latest_fix=None;self.plot.trail=[];self.plot.update()
        for label in self.position_values.values():label.setText('--')
        self.quality.setText('No fix yet. Waiting for synchronized RF measurements.');self.refresh_status()
    def collect(self):
        if self.controller:return Profile.from_dict(self.controller.profile.to_dict())
        p=Profile.from_dict(self.profile.to_dict());p.site_id=self.site.text().strip();p.floor_id=self.floor.text().strip();p.tag_id=self.tag_id.text().strip();p.tag_mac=self.tag_mac.text().strip().upper();p.blink_interval_ms=self.blink.value();p.tag_port=self.port_boxes[len(p.anchors)].currentText().strip().split(' — ')[0]
        p.bounds=json.loads(self.bounds.text());p.aoa_sigma_deg=self.sigma_a.value();p.tdoa_sigma_m=self.sigma_t.value();p.max_z_uncertainty_m=self.max_z.value()
        for row in range(len(p.anchors)):
            vals=[self.anchor_table.item(row,col).text().strip() for col in range(10)]
            if any(vals[3:6]) and not all(vals[3:6]):raise ValueError('Enter all three X, Y and Z coordinates, or leave all three empty.')
            p.anchors[row]=Anchor(vals[0],vals[1].upper(),vals[2],port=self.port_boxes[row].currentText().strip().split(' — ')[0],position=[float(v) for v in vals[3:6]] if all(vals[3:6]) else None,yaw=float(vals[6]),pitch=float(vals[7]),roll=float(vals[8]),rx_bias_m=float(vals[9]),aoa_verified=self.anchor_table.cellWidget(row,10).isChecked())
        self.profile=p;return p
    def refresh_ports(self):
        found=ports();values=[p['port']+' — '+p['description'] for p in found]
        for combo in self.port_boxes:
            current=combo.currentText().split(' — ')[0];combo.clear();combo.addItem('');combo.addItems(values);combo.setCurrentText(current)
        self.log(str(len(found))+' serial ports found. Board model/revision must be identified physically.')
    def refresh_bundles(self):
        self.firmware_combo.clear()
        for p in bundles(self.root):self.firmware_combo.addItem(p.parent.name,str(p))
        self.log(str(self.firmware_combo.count())+' verified-build manifests found')
    def available_images(self):
        manifest=self.firmware_combo.currentData()
        if not manifest:raise ValueError('No complete firmware manifest found')
        return images(self.root,manifest)
    def revision(self,row):
        value=self.rev_boxes[row].currentText()
        if self.rev_boxes[row].currentIndex()==0:raise ValueError('Check the physical EVK revision before flashing.')
        return int(value)
    def flash_selected(self):
        if self.controller:raise ValueError('Close COM ports before flashing')
        p=self.collect();row=self.target.currentIndex();revision=self.revision(row);available=self.available_images();port=p.tag_port if row==len(p.anchors) else p.anchors[row].port
        if not port:raise ValueError('Select the COM port of the board to flash.')
        flasher=Flasher(self.root,self.signals.log.emit)
        if row==len(p.anchors):self.job(lambda:flasher.setup_tag(available,port,revision,p))
        else:
            role=p.anchors[row].role
            if role not in available:raise ValueError('Firmware bundle does not contain '+role)
            self.job(lambda:flasher.flash(available[role],port,revision,'Type2BP'))
    def flash_all(self):
        if self.controller:raise ValueError('Close COM ports before flashing')
        p=self.collect();revs=[self.revision(i) for i in range(len(p.anchors))];available=self.available_images();flasher=Flasher(self.root,self.signals.log.emit)
        if not all(a.port for a in p.anchors) or len({a.port.upper() for a in p.anchors})!=len(p.anchors):raise ValueError('Assign a different COM port to every anchor.')
        for a in p.anchors:
            if a.role not in available:raise ValueError('Missing firmware '+a.role)
        self.job(lambda:[flasher.flash(available[a.role],a.port,revs[i],'Type2BP') for i,a in enumerate(p.anchors)])
    def save_profile(self):
        if self.controller or self.cloud:raise ValueError('Close COM/cloud before changing a profile')
        p=self.collect();path=save_new(self.root/'config/profiles','site-profile',p.to_dict());self.log('Saved new profile '+str(path))
    def load_profile(self):
        if self.controller or self.cloud:raise ValueError('Close serial/cloud before changing profile')
        path,_=W.QFileDialog.getOpenFileName(self,self.tr('Load profile'),str(self.root/'config/profiles'),'JSON (*.json)')
        if path:self.profile=Profile.from_dict(json.loads(Path(path).read_text(encoding='utf-8')));self.populate_profile();self.log('Loaded profile without editing source '+path)
    def export_cloud(self):
        p=self.collect();p.validate(require_aoa=False)
        rows=[{'id':a.id,'floorId':p.floor_id,'posXM':a.position[0],'posYM':a.position[1],'posZM':a.position[2],'role':a.role,'hardwareMac':a.mac} for a in p.anchors]
        path=save_new(self.root/'config/cloud-onboarding','anchors',{'siteId':p.site_id,'floorId':p.floor_id,'gatewayName':'KMUTNB-UWB-Programmer','anchors':rows,'instructions':'Enter these surveyed anchors in RTLS Site Configurations; this is a setup worksheet, not an undocumented API request.'});self.log('RTLS surveyed anchor setup '+str(path));os.startfile(str(path))
    def open_anchors(self,diagnostic):
        self.banner.setText('Hardware acquisition - firmware validation on real boards is pending.')
        if self.controller:raise ValueError('Anchors already open')
        if self.cloud:raise ValueError('Disconnect cloud before opening a different acquisition profile')
        p=self.collect();p.validate(require_ports=True,require_aoa=not diagnostic);self.plot.profile=p;self.plot.trail=[];self.plot.update()
        self.controller=Controller(self.root,p,self.signals.log.emit,self.signals.fix.emit,diagnostic=diagnostic);self.record_status.setText(str(self.controller.record.path));self.refresh_status()
    def start_anchors(self):
        if not self.controller:raise ValueError('Open Anchors first')
        self.controller.command('start')
    def stop_anchors(self):
        if self.controller:self.controller.command('stop')
    def close_anchors(self):
        if self.controller:self.controller.close();self.controller=None
        self.disconnect_cloud();self.refresh_status()
    def show_fix(self,fix):
        self.latest_fix=fix
        for axis in 'XYZ':self.position_values[axis].setText(f"{fix[axis.lower()+'_m']:.3f}")
        self.xyz.setText(f"X {fix['x_m']:.3f}       Y {fix['y_m']:.3f}       Z {fix['z_m']:.3f} m")
        self.quality.setText(f"{fix['time']} • {fix['num_anchors_used']} Anchors • horizontal 95% {fix['accuracy_m']:.3f} m • Z 95% ±{fix['z_uncertainty_m']:.3f} m • residual {fix['residual']:.3f} m")
        self.plot.set_fix(fix)
    def health(self):return self.controller.health() if self.controller else {'clock_status':'unknown','devices':[]}
    def check_cloud(self):
        p=self.controller.profile if self.controller else self.collect();token=self.token.text().strip()
        def work():
            cfg=pull_config(token);validate_scope(p,cfg);return cfg
        self.job(work,lambda cfg:self.log('RTLS token/site/floor/anchor coordinates verified: '+str(cfg.get('configVersion'))))
    def connect_cloud(self):
        if self.cloud:raise ValueError('RTLS already connecting/connected')
        p=self.controller.profile if self.controller else self.collect();p.validate(require_aoa=False)
        self.cloud=CloudClient(p,self.token.text(),self.gateway_id.text(),self.signals.log.emit,self.health)
        if self.controller:self.controller.cloud=self.cloud
        self.cloud.start();self.refresh_status()
    def disconnect_cloud(self):
        if self.cloud:self.cloud.close();self.cloud=None
        if self.controller:self.controller.cloud=None
    def save_token(self):
        if not self.token.text().strip() or not self.gateway_id.text().strip():raise ValueError('Enter gateway ID and bearer token first')
        path=credentials.save(self.root,self.token.text().strip(),self.gateway_id.text().strip());self.log('Saved user-scoped DPAPI credential '+str(path))
    def load_latest_credentials(self):
        found=sorted((self.root/'data/credentials').glob('gateway-*.json'),reverse=True)
        if not found:return
        try:
            d=credentials.load(found[0]);self.token.setText(d['token']);self.gateway_id.setText(d['gateway_id']);self.log('Loaded local Windows-encrypted gateway credential')
        except Exception as e:self.log('Credential could not be loaded: '+str(e))
    def capture_reference(self):
        if not self.controller or not self.controller.running:raise ValueError('Run Diagnostic with a Tag at a known reference position first')
        row=self.cal_anchor.currentIndex();a=self.controller.profile.anchors[row];o=self.controller.latest.get(a.id)
        if not o or o.frame_type!='BLINK' or o.peer_mac!=self.controller.profile.tag_mac or o.az is None or o.el is None or min(o.az_fom,o.el_fom)<self.profile.min_fom:raise ValueError('No valid Tag azimuth/elevation/FOM')
        if time.monotonic()-self.controller.pipe.last_blink.get(a.id,0)>max(2,2*self.profile.blink_interval_ms/1000):raise ValueError('Angle measurement is stale')
        xyz=[float(v) for v in self.reference_xyz.text().split(',')]
        if len(xyz)!=3 or not all(math.isfinite(v) for v in xyz):raise ValueError('Reference must be X,Y,Z in metres')
        self.cal_rows.setdefault(a.id,[]).append({'position':xyz,'az':o.az,'el':o.el,'time':o.received_utc});self.cal_count.setText(str(len(self.cal_rows[a.id]))+' references for '+a.id)
        path=save_new(self.root/'data/calibration','references',{'anchor_id':a.id,'rows':self.cal_rows[a.id]});self.log('Reference captured '+str(path))
    def import_calibration(self):
        path,_=W.QFileDialog.getOpenFileName(self,self.tr('Reference JSON'),str(self.root/'data/calibration'),'JSON (*.json)')
        if path:
            d=json.loads(Path(path).read_text(encoding='utf-8'));self.cal_rows[d['anchor_id']]=d['rows'];self.cal_count.setText(str(len(d['rows']))+' imported references')
    def fit_orientation(self):
        if self.controller:raise ValueError('Stop and Close COM ports before applying a new orientation')
        p=self.collect();row=self.cal_anchor.currentIndex();a=p.anchors[row];result=calibrate_rotation(a,self.cal_rows.get(a.id,[]))
        for col,key in [(6,'yaw'),(7,'pitch'),(8,'roll')]:self.anchor_table.item(row,col).setText(f'{result[key]:.5f}')
        self.anchor_table.cellWidget(row,10).setChecked(False);self.log('Orientation fit '+str(result)+'; verify other known points before marking 3D AoA verified');self.save_profile()
    def replay_session(self):
        if self.controller or self.cloud:raise ValueError('Close live serial and cloud before offline replay')
        path,_=W.QFileDialog.getOpenFileName(self,self.tr('Offline replay'),str(self.root/'data/sessions'),'RF sessions (*.jsonl)')
        if path:
            with open(path,encoding='utf-8') as f:self.plot.profile=Profile.from_dict(json.loads(next(f))['data']['profile'])
            self.plot.trail=[]
            self.banner.setText('Offline replay - recorded data stays on this PC.');self.job(lambda:replay(path,self.signals.fix.emit,self.signals.log.emit),lambda s:self.log('Offline replay '+str(s)))
    def refresh_status(self):
        opened=self.controller is not None
        self.setup_widget.setEnabled(not opened and not self.busy);self.geometry_widget.setEnabled(not opened and not self.cloud and not self.busy)
        # Reference capture remains available while the RF profile itself is locked.
        if opened:self.geometry_widget.setEnabled(True);self.anchor_table.setEnabled(False);self.site.setEnabled(False);self.floor.setEnabled(False);self.bounds.setEnabled(False)
        for field in [self.tag_id,self.sigma_a,self.sigma_t,self.max_z]:field.setEnabled(not opened and not self.cloud and not self.busy)
        if not opened:self.anchor_table.setEnabled(True);self.site.setEnabled(True);self.floor.setEnabled(True);self.bounds.setEnabled(True)
        self.open_button.setEnabled(not opened and not self.busy);self.diagnostic_button.setEnabled(not opened and not self.busy);self.start_button.setEnabled(opened and not self.busy);self.stop_button.setEnabled(opened);self.close_button.setEnabled(opened and not self.busy)
        if opened:
            self.controller.publish_position=self.publish_position.isChecked();self.controller.publish_raw=self.publish_raw.isChecked();s=self.controller.snapshot()
            self.live_status.setText(('DIAGNOSTIC — no position publishing | ' if s['diagnostic'] else 'LIVE | ')+str(s['states'])+'\nClock '+s['clock_status']+' | fixes '+str(s['fixes'])+' | rejected '+str(s['rejected'])+' | '+s['reason'])
            for row,(aid,c) in enumerate(s['clocks'].items()):
                for col,val in enumerate([aid,c['samples'],f"{c['drift_ppm']:.3f}",'—' if c['rms_ns'] is None else f"{c['rms_ns']:.3f}"]):self.clock_table.setItem(row,col,W.QTableWidgetItem(str(val)))
            lines=[]
            for a in self.controller.profile.anchors:
                o=self.controller.pipe.latest_angles.get(a.id)
                if o:lines.append(f'{a.id}: az {o.az}° / el {o.el}° / FOM {o.az_fom}/{o.el_fom} / NLOS {o.nlos}')
            self.angle_status.setText('\n'.join(lines) or 'Waiting for Tag BLINK')
        else:self.live_status.setText('COM ports closed')
        self.gateway_id.setEnabled(not self.cloud and not self.busy);self.token.setEnabled(not self.cloud and not self.busy)
        if self.cloud:self.cloud_status.setText(f'RTLS connected={self.cloud.connected} | config verified={self.cloud.ready} | ACK OK={self.cloud.ack_ok} | errors={self.cloud.ack_error} | dropped={self.cloud.dropped}')
        else:self.cloud_status.setText('RTLS disconnected')
        self.hardware_badge.setText('Acquiring RF' if opened and self.controller.running else 'Ports open' if opened else 'Hardware offline')
        self.cloud_badge.setText('Cloud connected' if self.cloud and self.cloud.connected else 'Cloud connecting' if self.cloud else 'Cloud disconnected')
        for badge,active in [(self.hardware_badge,opened and self.controller.running),(self.cloud_badge,bool(self.cloud and self.cloud.connected))]:
            badge.setProperty('active',active);badge.style().unpolish(badge);badge.style().polish(badge)
        self.mode_combo.setEnabled(not opened and not self.cloud and not self.busy)
        self.sigma_a.setEnabled(self.profile.mode=='hybrid_3' and not opened and not self.cloud and not self.busy)
        self.apply_language()
    def closeEvent(self,event):
        if self.busy:W.QMessageBox.warning(self,self.tr('Operation running'),self.tr('Wait for Flash/operation to finish before closing.'));event.ignore();return
        self.close_anchors();event.accept()

def main(root):
    app=W.QApplication.instance() or W.QApplication(sys.argv);app.setApplicationName('UWB Board Programmer');window=Window(root);window.show();return app.exec()
