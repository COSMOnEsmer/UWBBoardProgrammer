"""The original full workspace, extended with standalone firmware and BLE/GATT."""
import json
import os
from pathlib import Path
from PySide6 import QtCore,QtWidgets as W
from .legacy_gui import Window as OriginalWindow
from .models import Profile
from .ble_controller import BleController,discover,run_ble
from . import standalone_flashing as standalone


class Window(OriginalWindow):
    def __init__(self,root):
        self._integrated_ready=False;self.ble_devices=[]
        super().__init__(root)
        app=W.QApplication.instance()
        app.styleHints().setColorScheme(QtCore.Qt.ColorScheme.Light)
        self.setWindowTitle('UWB Board Programmer 2.1.0 | Standalone BLE + USB')
        self.ble_page()
        page=self.tabs.widget(self.tabs.count()-1);self.tabs.removeTab(self.tabs.count()-1)
        self.tabs.insertTab(1,page,'BLE / GATT')
        self.navigation.insertItem(1,W.QListWidgetItem('02   BLE / GATT'))
        names=['01   Devices & firmware','02   BLE / GATT','03   Survey & calibration',
               '04   Live positioning','05   RTLS Platform','06   Sessions & replay']
        for index,name in enumerate(names):
            item=self.navigation.item(index);item.setText(name);item.setData(0x1000,name)
            item.setSizeHint(QtCore.QSize(180,48))
        self.transport_combo.currentIndexChanged.connect(lambda _:self.guard(self.change_transport))
        self._integrated_ready=True
        self.populate_profile();self.change_transport();self.navigate(0);self.refresh_status()
        self.logs.setVisible(True);self.logs.setFixedHeight(60);self.log_toggle.setText('Hide log')
        self.banner.setText('Flash by USB, configure BLE anchors, survey coordinates, then start positioning.')
        self.apply_language()

    def setup_page(self):
        super().setup_page()
        self.transport_combo=W.QComboBox();self.transport_combo.setObjectName('AcquisitionTransport')
        self.transport_combo.addItem('Standalone · BLE / GATT','ble')
        self.transport_combo.addItem('USB · Legacy firmware','usb')
        mode_row=self.mode_combo.parentWidget().layout().itemAt(2).layout()
        self.field('CONNECTION MODE',self.transport_combo,mode_row)
        self.transport_note=self.banner
        self.tag_image=W.QComboBox();self.tag_image.addItem('Tag · battery / standalone','tag_battery')
        self.tag_image.addItem('Tag · setup / USB diagnostics','tag_setup')
        self.tag_image.setObjectName('StandaloneTagImage')
        self.tag_mac.parentWidget().layout().addWidget(self.tag_image)
        self.flash_all_button.setVisible(False)

    def ble_page(self):
        self.ble_widget,layout=self.page('BLE / GATT')
        card=self.card('BLE discovery','Scan for anchors running the standalone telemetry firmware, then assign each UWB MAC to your surveyed anchor.',layout)
        row=W.QHBoxLayout();card.addLayout(row)
        self.ble_scan_mode=W.QComboBox();self.ble_scan_mode.addItem('Passive scan','passive');self.ble_scan_mode.addItem('Active scan','active')
        self.ble_scan_seconds=W.QSpinBox();self.ble_scan_seconds.setRange(3,30);self.ble_scan_seconds.setSuffix(' s')
        self.field('SCAN MODE',self.ble_scan_mode,row);self.field('SCAN DURATION',self.ble_scan_seconds,row)
        self.ble_scan_button=self.button('Scan BLE anchors',self.scan_ble,row,'primary')
        self.ble_table=W.QTableWidget(0,6);self.ble_table.setObjectName('BleDiscoveryTable')
        self.ble_table.setHorizontalHeaderLabels(['UWB MAC','ROLE','BLE ADDRESS','RSSI dBm','ASSIGNED ANCHOR','STATE'])
        self.table_style(self.ble_table,40);self.ble_table.setEditTriggers(W.QAbstractItemView.NoEditTriggers)
        self.ble_table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch)
        self.ble_table.setMinimumHeight(200);card.addWidget(self.ble_table)
        row=W.QHBoxLayout();card.addLayout(row);self.ble_bind_target=W.QComboBox();row.addWidget(self.ble_bind_target,1)
        self.ble_assign_button=self.button('Assign selected BLE anchor',self.assign_ble,row)
        self.ble_scan_status=self.label('Scan to discover standalone anchors. The system uses the Windows default Bluetooth adapter.',card)
        card=self.card('Receive & verify','Connect to check firmware, GATT notifications, RF frame counts and Tag reception before calculating a position.',layout)
        row=W.QHBoxLayout();card.addLayout(row)
        self.ble_connect_button=self.button('Connect BLE + record',lambda:self.open_anchors(True),row,'primary')
        self.ble_disconnect_button=self.button('Disconnect BLE',self.close_anchors,row)
        self.ble_live_status=self.label('BLE disconnected',card)
        self.ble_info=self.label('Firmware, boot ID and configuration CRC appear here after connection.',card)
        self.label('Save the anchor mapping and scan settings using Save new profile in Survey & calibration. Start 3D processing from Live positioning after the survey is complete.',card)
        layout.addStretch()

    def navigate(self,index):
        if not self._integrated_ready:return super().navigate(index)
        headings=[('Devices & firmware','Flash standalone or legacy firmware one board at a time.'),
                  ('BLE / GATT','Discover, assign and monitor autonomous anchors.'),
                  ('Survey & calibration','Enter measured coordinates and calibrate angles when required.'),
                  ('Live positioning','RF synchronization, live Tag coordinates and the floor view.'),
                  ('RTLS Platform','Connect your hardware gateway and publish accepted live positions.'),
                  ('Sessions & replay','Review recorded measurements and positions locally.')]
        if not 0<=index<len(headings):return
        self.page_title.setText(headings[index][0]);self.page_subtitle.setText(headings[index][1])
        if self.navigation.currentRow()!=index:
            self.navigation.blockSignals(True);self.navigation.setCurrentRow(index);self.navigation.blockSignals(False)
        self.apply_language()

    def populate_profile(self):
        super().populate_profile()
        self.transport_combo.blockSignals(True)
        self.transport_combo.setCurrentIndex(0 if self.profile.transport=='ble' else 1)
        self.transport_combo.blockSignals(False)
        if hasattr(self,'ble_scan_mode'):
            self.ble_scan_mode.setCurrentIndex(0 if self.profile.ble_scan_mode=='passive' else 1)
            self.ble_scan_seconds.setValue(self.profile.ble_scan_seconds)
            self.ble_bind_target.clear()
            for index,a in enumerate(self.profile.anchors):self.ble_bind_target.addItem(a.id+' / '+a.role,index)
        if self._integrated_ready:self.change_transport()

    def rebuild_device_rows(self):
        revisions={key:box.currentText() for key,box in zip(self._device_keys,self.rev_boxes)}
        super().rebuild_device_rows()
        for key,box in zip(self._device_keys,self.rev_boxes):
            box.addItem('4.1')
            if key in revisions:box.setCurrentText(revisions[key])
        if hasattr(self,'ble_bind_target'):
            self.ble_bind_target.clear()
            for index,a in enumerate(self.profile.anchors):self.ble_bind_target.addItem(a.id+' / '+a.role,index)

    def collect(self):
        p=super().collect()
        p.transport=self.transport_combo.currentData()
        if hasattr(self,'ble_scan_mode'):
            p.ble_scan_mode=self.ble_scan_mode.currentData();p.ble_scan_seconds=self.ble_scan_seconds.value()
        return p

    def change_transport(self):
        if self.controller or self.cloud or self.busy:
            raise ValueError('Disconnect acquisition and RTLS before changing connection mode.')
        self.profile.transport=self.transport_combo.currentData()
        ble=self.profile.transport=='ble'
        self.tag_image.setVisible(ble);self.tag_mac.setReadOnly(ble);self.blink.setEnabled(not ble)
        self.transport_note.setText('Standalone anchors start themselves. The PC receives BLE measurements and computes positions.' if ble
                                    else 'Legacy USB mode uses the original serial firmware and START/STOP workflow.')
        self.refresh_bundles();self.refresh_status()

    def refresh_bundles(self):
        if self.transport_combo.currentData()!='ble':return super().refresh_bundles()
        self.firmware_combo.clear()
        try:
            manifest,images=standalone.latest_bundle(self.root)
            self.firmware_combo.addItem('Standalone BLE · '+images[0]['version'],str(manifest))
            self.log('Standalone firmware bundle: '+images[0]['version'])
        except ValueError as error:self.log(str(error))

    def revision(self,row):
        if self.rev_boxes[row].currentIndex()<=0:raise ValueError('Check the physical EVK revision before flashing.')
        return float(self.rev_boxes[row].currentText())

    def flash_selected(self):
        if self.transport_combo.currentData()!='ble':return super().flash_selected()
        if self.controller:raise ValueError('Disconnect BLE/USB acquisition before flashing.')
        row=self.target.currentIndex();count=len(self.profile.anchors)
        if not 0<=row<=count:raise ValueError('Select a board to flash.')
        if self.revision(row)!=4.1:raise ValueError('Standalone bench images are verified for EVK Rev4.1. Select the physical revision.')
        port=self.port_boxes[row].currentText().strip().split(' — ')[0].upper()
        if not port.startswith('COM') or not port[3:].isdigit():raise ValueError('Select the COM port of the board to flash.')
        manifest=self.firmware_combo.currentData()
        if not manifest:raise ValueError('Complete standalone firmware bundle is missing.')
        values=json.loads(Path(manifest).read_text(encoding='utf8'))['images']
        label=self.tag_image.currentData() if row==count else ('master' if row==0 else 'slave'+str(row+1))
        entry=next(e for e in values if e['image_label']==label)
        mac=self.tag_mac.text().strip().upper() if row==count else self.anchor_table.item(row,1).text().strip().upper()
        role='tag' if row==count else self.anchor_table.item(row,2).text().strip()
        if mac!=entry['provisioned_mac'].upper() or (row<count and role!=entry['role']):
            raise ValueError('Selected firmware provisions '+entry['provisioned_mac']+' / '+entry['role']+'. Match the board slot and profile before flashing.')
        if row==count and self.blink.value()!=entry['interval_ms']:
            raise ValueError('This standalone Tag image provisions '+str(entry['interval_ms'])+' ms. A custom interval needs a new firmware image.')
        physical=[p for p in standalone.inventory() if p.device.upper()==port]
        if len(physical)!=1:raise ValueError('The selected Murata FTDI USB board is not connected.')
        serial_number=physical[0].serial_number
        self.job(lambda:standalone.flash_selected(self.root,entry,port,serial_number,self.signals.log.emit),self.flash_finished)

    def flash_finished(self,result):
        self.log('Flash report: '+str(result.get('report','')))
        if not result.get('program_verify_passed'):raise ValueError(result.get('error','Firmware verification failed.'))
        if not result.get('configuration_acknowledged'):
            raise ValueError('Flash bytes verified. Configuration acknowledgement is pending; inspect the saved report.')
        self.log('Standalone firmware and persistent identity verified. Test RF reception before deployment.')

    def scan_ble(self):
        if self.controller:raise ValueError('Disconnect BLE acquisition before starting a separate scan.')
        seconds=self.ble_scan_seconds.value();mode=self.ble_scan_mode.currentData()
        self.ble_scan_status.setText('Scanning for standalone UWB anchors...')
        self.job(lambda:run_ble(discover(seconds,mode)),self.scan_finished)

    def scan_finished(self,values):
        self.ble_devices=values;self.ble_table.setRowCount(len(values))
        for index,value in enumerate(values):
            assigned=next((a.id for a in self.collect().anchors if a.mac.upper()==value['mac']),'—')
            for col,text in enumerate([value['mac'],value['role'],value['address'],str(value['rssi']),assigned,'discovered']):
                self.ble_table.setItem(index,col,W.QTableWidgetItem(text))
        self.ble_table.clearSelection()
        self.ble_scan_status.setText(str(len(values))+' standalone BLE anchors found. Select one row to assign it.' if values else 'No standalone anchors found. Power the anchors and scan again.')

    def assign_ble(self):
        row=self.ble_table.currentRow()
        if not 0<=row<len(self.ble_devices):raise ValueError('Select a discovered BLE anchor first.')
        index=self.ble_bind_target.currentData();value=self.ble_devices[row];p=self.collect()
        if value['role']!=p.anchors[index].role:raise ValueError('BLE role does not match the selected anchor role.')
        if any(i!=index and a.mac.upper()==value['mac'] for i,a in enumerate(p.anchors)):
            raise ValueError('This UWB MAC is already assigned to another anchor.')
        self.anchor_table.item(index,1).setText(value['mac']);self.collect()
        self.ble_table.item(row,4).setText(p.anchors[index].id)
        self.log('BLE mapping: '+p.anchors[index].id+' / '+value['mac'])

    def open_anchors(self,diagnostic):
        if self.transport_combo.currentData()!='ble':return super().open_anchors(diagnostic)
        if self.controller:raise ValueError('Acquisition is already open.')
        if self.cloud:raise ValueError('Disconnect RTLS before opening a different acquisition profile.')
        p=self.collect()
        if not diagnostic:p.validate(require_ports=False,require_aoa=True)
        self.controller=BleController(self.root,p,self.signals.log.emit,self.signals.fix.emit,diagnostic=diagnostic)
        self.record_status.setText(str(self.controller.record.path))
        if not diagnostic:self.plot.profile=p;self.plot.trail=[];self.plot.update()
        self.log('BLE reception opened. Autonomous UWB radios remain active independently of this PC.')
        self.refresh_status()

    def close_anchors(self):
        if self.controller:self.controller.close();self.controller=None
        self.disconnect_cloud();self.refresh_status()

    def refresh_status(self):
        super().refresh_status()
        if not self._integrated_ready:return
        ble=self.transport_combo.currentData()=='ble';opened=self.controller is not None
        self.open_button.setText('Connect BLE + record' if ble else 'Open anchors + record')
        self.diagnostic_button.setText('BLE capture / diagnostics' if ble else 'Diagnostic mode')
        self.start_button.setText('Start positioning' if ble else 'Start anchors')
        self.stop_button.setText('Pause positioning' if ble else 'Stop')
        self.close_button.setText('Disconnect BLE' if ble else 'Close ports')
        self.flash_all_button.setVisible(not ble)
        self.tag_mac.setReadOnly(ble);self.blink.setEnabled(not ble and not opened and not self.busy)
        self.ble_scan_button.setEnabled(ble and not opened and not self.busy)
        self.ble_assign_button.setEnabled(ble and not opened and not self.busy and bool(self.ble_devices))
        self.ble_connect_button.setEnabled(ble and not opened and not self.busy)
        self.ble_disconnect_button.setEnabled(ble and opened and not self.busy)
        self.ble_scan_mode.setEnabled(not opened and not self.busy);self.ble_scan_seconds.setEnabled(not opened and not self.busy)
        if ble and opened:
            state=self.controller.snapshot();age='—' if state['tag_age_s'] is None else str(state['tag_age_s'])+' s'
            status=f"BLE {len(state['connected'])}/{len(self.profile.anchors)} | RF frames {state['rf_total']} | Tag age {age} | Clock {state['clock_status']} | Fixes {state['fixes']}"
            self.ble_live_status.setText(status);self.live_status.setText(status+'\n'+state['reason'])
            info=[]
            for aid,value in state['hello'].items():
                info.append(aid+' / '+value['firmware']+' / boot '+value['boot']+' / CRC '+value['config_crc'])
            self.ble_info.setText('\n'.join(info) or 'Waiting for autonomous anchors...')
            self.hardware_badge.setText('BLE '+str(len(state['connected']))+'/'+str(len(self.profile.anchors)))
            for row,value in enumerate(self.ble_devices):
                aid=next((a.id for a in self.controller.profile.anchors if a.mac.upper()==value['mac']),None)
                if aid:self.ble_table.item(row,5).setText(state['states'].get(aid,'disconnected'))
            if state['diagnostic']:self.start_button.setEnabled(False)
        elif ble:
            self.live_status.setText('BLE disconnected. Connect anchors to record, then start positioning after surveying.')
            self.ble_live_status.setText('BLE disconnected')
        self.apply_language()

    def open_guide(self):
        os.startfile(str(self.root/('docs/INTEGRATED_STANDALONE_GUIDE.v1.th.md' if self.language=='th'
                                    else 'docs/INTEGRATED_STANDALONE_GUIDE.v1.en.md')))

    def closeEvent(self,event):
        if self.busy:
            W.QMessageBox.warning(self,self.tr('Operation running'),self.tr('Wait for Flash/operation to finish before closing.'))
            event.ignore();return
        try:self.close_anchors()
        except Exception as error:self.log(str(error));event.ignore();return
        event.accept()
