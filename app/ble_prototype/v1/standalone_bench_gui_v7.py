"""Separate experimental desktop bench; released 2.0.1 is not modified."""
import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
import queue
import threading
import time
from PySide6 import QtCore,QtGui,QtWidgets as W
from uwb_board_programmer.models import Profile,unique_path,utc
from uwb_board_programmer.protocol import parse_line
from uwb_ble_cloud import CloudClient
from uwb_ble_receiver_v4 import Binding,Central
from uwb_ble_pipeline_v2 import CorrelatedLivePipeline


class Signals(QtCore.QObject):
    log=QtCore.Signal(str)
    state=QtCore.Signal(str,str)
    snapshot=QtCore.Signal(object)
    fix=QtCore.Signal(object)
    stopped=QtCore.Signal()
    flashed=QtCore.Signal(object)


class Worker:
    def __init__(self,root,profile,positioning,signals):
        self.root=root;self.profile=profile;self.positioning=positioning;self.signals=signals
        self.queue=queue.Queue(1024);self.end=threading.Event();self.stop_requested=threading.Event();self.overflow=threading.Event()
        self.loop=None;self.central=None;self.cloud=None;self.connected=set();self.last_tag=0;self.rx_counts={}
        self.health_data={'clock_status':'unknown','devices':[]}
        self.path=unique_path(root/'data/sessions','ble-pilot','.jsonl')
        self.file=self.path.open('x',encoding='utf8')
        self.record('header',dict(version='Standalone BLE pilot',mode='hardware',
                                 profile=profile.to_dict(),experimental=True))
        try:
            self.pipeline=CorrelatedLivePipeline(profile,self.record,self.on_fix) if positioning else None
        except Exception:
            self.file.close();raise

    def record(self,kind,data):
        self.file.write(json.dumps(dict(kind=kind,recorded_utc=utc(),data=data),ensure_ascii=False,allow_nan=False)+'\n')
        self.file.flush()

    def on_fix(self,fix):
        self.signals.fix.emit(fix)
        if self.cloud:self.cloud.publish_fix(fix)

    def emit(self,aid,kind,data):
        try:self.queue.put_nowait((time.monotonic(),aid,kind,data))
        except queue.Full:self.overflow.set()

    def start(self):
        threading.Thread(target=self.process,daemon=True,name='BLE-positioning').start()
        threading.Thread(target=self.receive,daemon=True,name='BLE-WinRT-MTA').start()

    def receive(self):
        initialized=False
        try:
            import sys
            if sys.platform=='win32':
                import ctypes
                result=ctypes.windll.ole32.CoInitializeEx(None,0)
                if result not in (0,1):raise RuntimeError('Cannot initialize the BLE worker as MTA: '+hex(result&0xffffffff))
                initialized=True
            self.loop=asyncio.new_event_loop();asyncio.set_event_loop(self.loop)
            bindings=[Binding(a.id,a.mac,a.role) for a in self.profile.anchors]
            self.central=Central(bindings,self.emit)
            if self.stop_requested.is_set():self.central.stop.set()
            self.loop.run_until_complete(self.central.run())
        except Exception as error:self.signals.log.emit(type(error).__name__+': '+str(error))
        finally:
            if self.loop:self.loop.close()
            if initialized:
                import ctypes
                ctypes.windll.ole32.CoUninitialize()
            self.end.set()

    def stop(self):
        self.stop_requested.set()
        if self.loop and self.central:
            try:self.loop.call_soon_threadsafe(self.central.stop.set)
            except RuntimeError:pass

    def process(self):
        next_snapshot=0
        try:
            while not self.end.is_set() or not self.queue.empty():
                if self.overflow.is_set():
                    self.overflow.clear()
                    while not self.queue.empty():
                        try:self.queue.get_nowait()
                        except queue.Empty:break
                    if self.pipeline:
                        for a in self.profile.anchors:self.pipeline.engine.reset(a.id)
                    self.signals.log.emit('Input queue overflow; clocks and pending measurements reset')
                try:
                    received,aid,kind,data=self.queue.get(timeout=.1)
                    if kind=='observation' and time.monotonic()-received>.5:
                        kind='reset';data={'reason':'stale_processing_queue'}
                    if self.pipeline:self.pipeline.event(aid,kind,data)
                    else:self.record('ble_'+kind,dict(anchor_id=aid,**data))
                    if kind=='connected':
                        self.connected.add(aid);self.signals.state.emit(aid,'connected')
                        self.signals.log.emit(aid+' '+data.get('firmware','')+' / '+data.get('radio_state','')+' / CRC '+data.get('config_crc',''))
                    if kind=='disconnected':self.connected.discard(aid);self.signals.state.emit(aid,'disconnected')
                    if kind=='error':self.signals.log.emit(aid+' '+data['message'])
                    if kind=='observation':self.rx_counts[aid]=self.rx_counts.get(aid,0)+1
                    if kind=='observation' and data['frame_type']=='BLINK' and data['peer_mac']==self.profile.tag_mac.upper():self.last_tag=time.monotonic()
                except queue.Empty:pass
                except Exception as error:
                    self.signals.log.emit('Processing: '+str(error))
                    if self.pipeline:
                        for a in self.profile.anchors:self.pipeline.engine.reset(a.id)
                now=time.monotonic()
                if now>=next_snapshot:
                    if self.pipeline:self.pipeline.engine.expire()
                    snapshot=self.pipeline.snapshot() if self.pipeline else {'clock_status':'capture only','fixes':0,'reason':'No position calculation'}
                    snapshot={**snapshot,'connected':sorted(self.connected),'rx_total':sum(self.rx_counts.values()),'rx_by_anchor':dict(self.rx_counts),'tag_age_s':round(now-self.last_tag,1) if self.last_tag else None}
                    devices=[dict(device_id=aid,device_type='anchor',status='online') for aid in sorted(self.connected)]
                    if self.last_tag:devices.append(dict(device_id=self.profile.tag_id,device_type='tag',status='online' if now-self.last_tag<3 else 'lost'))
                    self.health_data=dict(clock_status=snapshot['clock_status'],devices=devices)
                    self.signals.snapshot.emit(snapshot);next_snapshot=now+.5
        finally:
            self.record('closed',dict(radio_stop_commands_sent=0))
            self.file.close();self.signals.stopped.emit()


class Window(W.QMainWindow):
    def __init__(self,root):
        super().__init__()
        for font in ['segoeui.ttf','segoeuib.ttf','tahoma.ttf','tahomabd.ttf']:
            QtGui.QFontDatabase.addApplicationFont(str(Path('C:/Windows/Fonts')/font))
        W.QApplication.instance().setStyle('Fusion');W.QApplication.instance().setFont(QtGui.QFont('Segoe UI',10))
        self.root=Path(root);self.profile=Profile.for_mode('tdoa_4')
        self.worker=None;self.cloud=None;self.close_pending=False;self.language='en';self.flashing=False
        self.signals=Signals();self.signals.log.connect(self.log);self.signals.state.connect(self.state)
        self.signals.snapshot.connect(self.snapshot);self.signals.fix.connect(self.show_fix);self.signals.stopped.connect(self.stopped);self.signals.flashed.connect(self.flash_done)
        self.setWindowTitle('UWB Board Programmer | Standalone BLE Pilot');self.resize(1150,820)
        self.setWindowIcon(QtGui.QIcon(str(self.root/'resources/branding/logo-v1.ico')))
        self.setStyleSheet('QMainWindow{background:#f4f7fb}QGroupBox{background:white;border:1px solid #dbe4ef;border-radius:8px;margin-top:12px;padding:14px}QGroupBox::title{subcontrol-origin:margin;left:14px;color:#345273}QPushButton{padding:9px 16px;border:1px solid #cdd9e8;border-radius:5px;background:white}QPushButton:disabled{color:#91a1b3}QTableWidget,QPlainTextEdit,QLineEdit{background:white;border:1px solid #dbe4ef}QLabel{color:#263c55}')
        central=W.QWidget();layout=W.QVBoxLayout(central);layout.setContentsMargins(24,20,24,20);layout.setSpacing(12);self.setCentralWidget(central)
        header=W.QHBoxLayout();title=W.QLabel('UWB Board Programmer  •  Standalone BLE Pilot');title.setFont(QtGui.QFont('Segoe UI',19,QtGui.QFont.Bold));header.addWidget(title,1)
        self.languages=W.QComboBox();self.languages.addItems(['English','ไทย']);self.languages.currentIndexChanged.connect(self.translate);header.addWidget(self.languages);layout.addLayout(header)
        self.notice=W.QLabel();self.notice.setWordWrap(True);layout.addWidget(self.notice)
        self.group=W.QGroupBox();group=W.QVBoxLayout(self.group);layout.addWidget(self.group)
        controls=W.QHBoxLayout();self.load=W.QPushButton();self.load.clicked.connect(self.load_profile);controls.addWidget(self.load)
        self.flash_button=W.QPushButton();self.flash_button.clicked.connect(self.flash_board);controls.addWidget(self.flash_button)
        self.position=W.QCheckBox();controls.addWidget(self.position);controls.addStretch();self.start=W.QPushButton();self.start.clicked.connect(self.start_capture);controls.addWidget(self.start)
        self.stop=W.QPushButton();self.stop.clicked.connect(self.disconnect);self.stop.setEnabled(False);controls.addWidget(self.stop);group.addLayout(controls)
        self.table=W.QTableWidget(4,4);self.table.setHorizontalHeaderLabels(['Anchor ID','UWB MAC','Role','BLE state']);self.table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch);self.table.setMaximumHeight(190);group.addWidget(self.table)
        self.status=W.QLabel('Disconnected');self.status.setWordWrap(True);group.addWidget(self.status)
        self.fix=W.QLabel('X —   Y —   Z —');self.fix.setFont(QtGui.QFont('Segoe UI',16));group.addWidget(self.fix)
        self.cloud_group=W.QGroupBox('RTLS Platform');cloud_layout=W.QHBoxLayout(self.cloud_group);layout.addWidget(self.cloud_group)
        self.gateway=W.QLineEdit();self.gateway.setPlaceholderText('Gateway ID');cloud_layout.addWidget(self.gateway)
        self.token=W.QLineEdit();self.token.setEchoMode(W.QLineEdit.Password);self.token.setPlaceholderText('Gateway bearer token');cloud_layout.addWidget(self.token,2)
        self.cloud_button=W.QPushButton();self.cloud_button.clicked.connect(self.toggle_cloud);cloud_layout.addWidget(self.cloud_button)
        self.logs=W.QPlainTextEdit();self.logs.setReadOnly(True);self.logs.setMaximumBlockCount(1000);layout.addWidget(self.logs,1)
        self.populate();self.translate();self.log('Experimental bench. Hardware acceptance is pending. No device connections open automatically.')

    def populate(self):
        self.table.setRowCount(len(self.profile.anchors))
        for row,a in enumerate(self.profile.anchors):
            for col,value in enumerate([a.id,a.mac,a.role,'disconnected']):self.table.setItem(row,col,W.QTableWidgetItem(value))

    def translate(self):
        th=self.languages.currentIndex()==1;self.language='th' if th else 'en'
        self.notice.setText('รุ่นทดลอง: ต้องใช้เฟิร์มแวร์ BLE ของโครงการ การทดสอบ GATT / RF / 4 Anchors / 3D / RTLS ยังไม่ครบ การตัด BLE ไม่ส่ง STOP ไปยังบอร์ด' if th else 'Experimental: custom BLE firmware required. GATT, RF, four-anchor, 3D and RTLS acceptance is pending. Disconnecting BLE sends no radio STOP.')
        self.table.setHorizontalHeaderLabels(['Anchor ID','UWB MAC','บทบาท','สถานะ BLE'] if th else ['Anchor ID','UWB MAC','Role','BLE state'])
        self.group.setTitle('เชื่อมต่อ Anchors และบันทึกข้อมูลจริง' if th else 'Anchor connections and live recording')
        self.flash_button.setText('Flash ทีละบอร์ด' if th else 'Flash one board')
        self.load.setText('โหลดโปรไฟล์พิกัด' if th else 'Load surveyed profile');self.position.setText('คำนวณ 3D ด้วย 4 Anchors' if th else 'Calculate 3D with four anchors')
        self.start.setText('เชื่อมต่อ BLE' if th else 'Connect BLE');self.stop.setText('ตัดการเชื่อมต่อ' if th else 'Disconnect')
        self.cloud_button.setText(('ตัด RTLS' if th else 'Disconnect RTLS') if self.cloud else ('เชื่อม RTLS' if th else 'Connect RTLS'))

    def log(self,text):self.logs.appendPlainText(datetime.now().strftime('%H:%M:%S')+'  '+text)

    def load_profile(self):
        path,_=W.QFileDialog.getOpenFileName(self,'Profile',str(self.root/'config/profiles'),'JSON (*.json)')
        if not path:return
        try:
            profile=Profile.from_dict(json.loads(Path(path).read_text(encoding='utf8')))
            if profile.mode!='tdoa_4':raise ValueError('Select a four-anchor TDoA profile')
            self.profile=profile;self.populate();self.log('Profile loaded: '+path)
        except Exception as error:W.QMessageBox.warning(self,'Profile',str(error))

    def start_capture(self):
        try:
            profile=Profile.from_dict(self.profile.to_dict())
            for row,a in enumerate(profile.anchors):
                a.id=self.table.item(row,0).text().strip();a.mac=self.table.item(row,1).text().strip().upper();a.role=self.table.item(row,2).text().strip().lower()
            bindings=[Binding(a.id,a.mac,a.role) for a in profile.anchors]
            Central(bindings,lambda *args:None)
            self.worker=Worker(self.root,profile,self.position.isChecked(),self.signals)
            self.table.setEditTriggers(W.QAbstractItemView.NoEditTriggers);self.load.setEnabled(False);self.flash_button.setEnabled(False);self.position.setEnabled(False);self.start.setEnabled(False);self.stop.setEnabled(True)
            self.worker.start();self.log('Session: '+str(self.worker.path))
        except Exception as error:W.QMessageBox.warning(self,'BLE',str(error))

    def state(self,aid,state):
        for row in range(self.table.rowCount()):
            if self.table.item(row,0).text()==aid:self.table.item(row,3).setText(state)

    def snapshot(self,data):
        self.status.setText(f"BLE {len(data['connected'])}/4 | RF frames: {data.get('rx_total',0)} | Tag age: {data.get('tag_age_s')} s | clock: {data['clock_status']} | fixes: {data['fixes']} | {data.get('reason','')}")

    def show_fix(self,fix):self.fix.setText(f"X {fix['x_m']:.3f} m   Y {fix['y_m']:.3f} m   Z {fix['z_m']:.3f} m")

    def toggle_cloud(self):
        if self.cloud:
            self.cloud.close();self.cloud=None
            if self.worker:self.worker.cloud=None
            self.translate();return
        if not self.worker or not self.worker.positioning:
            W.QMessageBox.warning(self,'RTLS','Start a live BLE positioning session with a surveyed profile first.');return
        try:
            if not self.token.text().strip():raise ValueError('Enter a hardware gateway token, not the dashboard password')
            self.cloud=CloudClient(self.worker.profile,self.token.text(),self.gateway.text(),self.signals.log.emit,lambda:self.worker.health_data if self.worker else {'clock_status':'unknown','devices':[]})
            self.worker.cloud=self.cloud;self.cloud.start();self.translate()
        except Exception as error:W.QMessageBox.warning(self,'RTLS',str(error))

    def disconnect(self):
        if self.cloud:self.cloud.close();self.cloud=None
        if self.worker:self.worker.cloud=None;self.worker.stop()
        self.stop.setEnabled(False);self.translate()

    def stopped(self):
        if self.cloud:self.cloud.close();self.cloud=None
        self.worker=None;self.start.setEnabled(True);self.load.setEnabled(True);self.flash_button.setEnabled(True);self.position.setEnabled(True);self.stop.setEnabled(False)
        self.table.setEditTriggers(W.QAbstractItemView.DoubleClicked|W.QAbstractItemView.EditKeyPressed)
        self.log('BLE session closed. No radio STOP commands sent.');self.translate()
        if self.close_pending:self.close()

    def flash_board(self):
        if self.worker or self.flashing:return
        from uwb_ble_flasher import inventory,latest_bundle,flash_selected
        try:
            manifest,images=latest_bundle(self.root);ports=inventory()
            if not ports:raise ValueError('Connect one Murata EVK by USB first')
            dialog=W.QDialog(self);dialog.setWindowTitle('Flash บอร์ด Murata ทีละตัว' if self.language=='th' else 'Flash one Murata EVK');form=W.QFormLayout(dialog)
            image_box=W.QComboBox();port_box=W.QComboBox()
            for entry in images:image_box.addItem(entry['anchor_slot']+' / '+entry['model']+' / '+entry['image_label']+' / '+entry['provisioned_mac'])
            for port in ports:port_box.addItem(port.device+' / USB '+port.serial_number)
            image_box.setPlaceholderText('Select firmware / เลือกเฟิร์มแวร์');port_box.setPlaceholderText('Select USB port / เลือกพอร์ต USB')
            image_box.setCurrentIndex(-1);port_box.setCurrentIndex(-1)
            form.addRow('เฟิร์มแวร์ที่เลือก' if self.language=='th' else 'Selected firmware',image_box);form.addRow('บอร์ดที่เชื่อมต่อ' if self.language=='th' else 'Connected board',port_box)
            revision=W.QComboBox();revision.addItems(['Rev4.1']);form.addRow('EVK revision',revision)
            note=W.QLabel('เลือกรุ่นและบทบาทให้ตรงกับบอร์ดที่เชื่อมต่อ ใช้พอร์ตที่เลือกเพียงพอร์ตเดียว ระบบจะสำรองสองชุดก่อน Flash เฟิร์มแวร์ชุดนี้เป็นรุ่นทดลอง' if self.language=='th' else 'Select the connected board model and role carefully. Only this USB port is required. Two backups are verified before programming. These images are experimental.');note.setWordWrap(True);form.addRow(note)
            buttons=W.QDialogButtonBox(W.QDialogButtonBox.Ok|W.QDialogButtonBox.Cancel);buttons.button(W.QDialogButtonBox.Ok).setText('เริ่ม Flash บอร์ดนี้' if self.language=='th' else 'Flash selected board')
            buttons.button(W.QDialogButtonBox.Ok).setEnabled(False)
            def selection_changed():buttons.button(W.QDialogButtonBox.Ok).setEnabled(image_box.currentIndex()>=0 and port_box.currentIndex()>=0)
            image_box.currentIndexChanged.connect(selection_changed);port_box.currentIndexChanged.connect(selection_changed)
            buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);form.addRow(buttons)
            if dialog.exec()!=W.QDialog.Accepted:return
            if image_box.currentIndex()<0 or port_box.currentIndex()<0:raise ValueError('Select the firmware model/role and connected USB port explicitly')
            entry=images[image_box.currentIndex()];port=ports[port_box.currentIndex()]
            self.flashing=True;self.start.setEnabled(False);self.load.setEnabled(False);self.flash_button.setEnabled(False);self.position.setEnabled(False)
            self.log('Firmware bundle: '+str(manifest))
            def work():
                try:result=flash_selected(self.root,entry,port.device,port.serial_number,self.signals.log.emit)
                except Exception as error:result={'error':str(error),'program_verify_passed':False}
                self.signals.flashed.emit(result)
            threading.Thread(target=work,daemon=True,name='selected-board-flash').start()
        except Exception as error:W.QMessageBox.warning(self,'Flash',str(error))

    def flash_done(self,result):
        self.flashing=False;self.start.setEnabled(True);self.load.setEnabled(True);self.flash_button.setEnabled(True);self.position.setEnabled(True)
        self.log('Flash report: '+str(result.get('report',result)))
        if not result.get('program_verify_passed'):W.QMessageBox.warning(self,'Flash',result.get('error','Flash not verified'))

    def closeEvent(self,event):
        if self.flashing:
            W.QMessageBox.warning(self,'Flash','Wait for backup/program/verify to finish before closing.');event.ignore();return
        if self.worker:self.close_pending=True;self.disconnect();event.ignore()
        else:event.accept()
