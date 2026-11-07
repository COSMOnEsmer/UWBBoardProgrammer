"""The original full workspace, extended with standalone firmware and BLE/GATT."""
import json
import os
from pathlib import Path
from PySide6 import QtCore,QtWidgets as W
from .legacy_gui import Window as OriginalWindow
from .models import Profile
from .ble_controller import BleController,discover,run_ble
from . import standalone_flashing as standalone
from .diagnostics import diagnostic_lines


class Window(OriginalWindow):
    def __init__(self,root):
        self._integrated_ready=False;self.ble_devices=[]
        super().__init__(root)
        app=W.QApplication.instance()
        app.styleHints().setColorScheme(QtCore.Qt.ColorScheme.Light)
        self.setWindowTitle('UWB Board Programmer 2.8.3 | Standalone BLE + USB')
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
        self.logs.setVisible(True);self.logs.setFixedHeight(88);self.log_toggle.hide()
        self.banner.setText('Flash by USB, configure BLE anchors, survey coordinates, then start positioning.')
        from .panels import wrap_remaining_cards
        wrap_remaining_cards(self)
        from .panels import enable_free_layout
        enable_free_layout(self)
        from .workspace_style import polish
        polish(self)
        self.anchor_table.parentWidget().layout().insertWidget(0,self.survey_confirm);self.survey_confirm.show()
        self.live_status.parentWidget().layout().addWidget(self.quality);self.quality.show()
        self.apply_language()

    def setup_page(self):
        super().setup_page()
        self.transport_combo=W.QComboBox();self.transport_combo.setObjectName('AcquisitionTransport')
        self.transport_combo.addItem('Standalone · BLE / GATT','ble')
        self.transport_combo.addItem('USB · Legacy firmware','usb')
        mode_layout=self.mode_combo.parentWidget().layout()
        mode_row=next(mode_layout.itemAt(i).layout() for i in range(mode_layout.count()) if isinstance(mode_layout.itemAt(i).layout(),W.QHBoxLayout))
        self.field('CONNECTION MODE',self.transport_combo,mode_row)
        self.transport_note=self.banner
        self.tag_image=W.QComboBox();self.tag_image.addItem('Tag · battery / standalone','tag_battery')
        self.tag_image.addItem('Tag · Auto Survey / USB calibration','tag_setup')
        self.tag_image.addItem('Tag · BLE calibration / battery pilot','tag_ble_calibration')
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

    def cloud_page(self):
        super().cloud_page()
        self.gateway_import_button=self.button('Use gateway configuration',self.import_gateway_configuration,self.cloud_widget.layout())
        self.button('RTLS connection guide',lambda:os.startfile(str(self.root/'docs/RTLS_CONNECTION_2_8_0.th.md')),self.cloud_widget.layout())

    def import_gateway_configuration(self):
        if self.controller or self.cloud:raise ValueError('Disconnect BLE and RTLS before applying a different gateway profile')
        from .cloud import pull_config
        from .gateway_setup import GatewaySetup
        token=self.token.text().strip()
        def done(config):
            dialog=GatewaySetup(self.profile,config,self)
            if dialog.exec()==W.QDialog.Accepted:
                from .models import save_new
                self.profile=dialog.result_profile;path=save_new(self.root/'config/profiles','gateway-profile',self.profile.to_dict())
                self.populate_profile();self.plot.clear_position();self.log('Saved new gateway profile '+str(path))
        self.job(lambda:pull_config(token),done)

    def geometry_page(self):
        super().geometry_page()
        self.survey_confirm=W.QCheckBox('Anchor coordinates were measured at the physical antenna positions')
        self.survey_confirm.setObjectName('MeasuredSurveyConfirmed')
        self.geometry_widget.layout().insertWidget(1,self.survey_confirm)
        card=W.QFrame();card.setObjectName('Card');layout=W.QVBoxLayout(card);layout.setContentsMargins(18,14,18,14)
        title=W.QLabel('Auto Survey');title.setObjectName('CardTitle');layout.addWidget(title)
        self.label('Capture TWR ranges at four measured Tag reference points, review anchor XYZ, then save a new survey profile. Supports sequential anchor power.',layout)
        row=W.QHBoxLayout();layout.addLayout(row)
        self.auto_survey_button=self.button('Auto Survey / Calibration',self.open_auto_survey,row,'primary');row.addStretch()
        self.geometry_widget.layout().insertWidget(2,card)
        row=W.QHBoxLayout();self.anchor_table.parentWidget().layout().addLayout(row)
        self.align_button=self.button('Align survey to floor',self.open_floor_alignment,row,'primary')
        self.restore_survey_button=self.button('Use retained survey',self.restore_survey,row)
        self.frame_status=W.QLabel('Coordinates: unmapped. Align before RTLS publishing.');self.frame_status.setWordWrap(True);row.addWidget(self.frame_status,1)

    def open_auto_survey(self):
        if self.controller or self.cloud:raise ValueError('Disconnect acquisition and RTLS before Auto Survey')
        from .survey_wizard import AutoSurveyDialog
        dialog=AutoSurveyDialog(self.root,self.collect(),self.tr,self)
        if dialog.exec()==W.QDialog.Accepted and dialog.saved_profile:
            self.profile=dialog.saved_profile;self.populate_profile();self.plot.profile=self.profile;self.plot.clear_position();self.plot.update()
            self.log('Loaded measured Auto Survey profile '+str(dialog.saved_path));self.refresh_status();self.open_floor_alignment()

    def open_floor_alignment(self):
        if self.controller or self.cloud:raise ValueError('Disconnect BLE/USB and RTLS before aligning coordinates')
        from .alignment_dialog import AlignmentDialog
        from .models import save_new
        p=self.collect();p.validate(require_aoa=False)
        dialog=AlignmentDialog(p,self)
        if dialog.exec()==W.QDialog.Accepted:
            self.profile=dialog.result_profile;path=save_new(self.root/'config/profiles','floor-profile',self.profile.to_dict())
            self.populate_profile();self.plot.clear_position();self.log('Saved new aligned floor profile '+str(path));self.refresh_status()

    def restore_survey(self):
        if self.controller or self.cloud:raise ValueError('Disconnect acquisition and RTLS first')
        from .models import save_new
        p=self.collect()
        retained=p.alignment.get('source_profile') or p.survey_archive
        if not retained:raise ValueError('This profile has no retained survey')
        restored=Profile.from_dict(retained);active={a.mac.upper():a for a in p.anchors}
        for anchor in restored.anchors:
            row=active[anchor.mac.upper()];anchor.id=row.id;anchor.port=row.port
        restored.site_id=p.site_id;restored.floor_id=p.floor_id;restored.tag_id=p.tag_id;restored.floor_geometry=p.floor_geometry
        restored.coordinate_frame='survey';restored.floor_verified=False;restored.alignment={}
        self.profile=restored;path=save_new(self.root/'config/profiles','restored-survey',restored.to_dict())
        self.populate_profile();self.plot.clear_position();self.log('Restored survey into a NEW profile '+str(path));self.refresh_status()

    def live_page(self):
        super().live_page()
        controls=W.QHBoxLayout();self.continuity_check=W.QCheckBox('Continuous estimates: display + RTLS (Warning)');self.continuity_check.setChecked(True);self.continuity_check.toggled.connect(lambda _:self.plot.clear_position());controls.addWidget(self.continuity_check);self.live_status.parentWidget().layout().addLayout(controls)
        self.position_issue=W.QLabel('')
        self.position_issue.setObjectName('PositionIssue');self.position_issue.setWordWrap(True);self.position_issue.hide()
        self.live_status.parentWidget().layout().addWidget(self.position_issue)

    def navigate(self,index):
        if not self._integrated_ready:return super().navigate(index)
        headings=[('Devices & firmware','Flash standalone or legacy firmware one board at a time.'),
                  ('BLE / GATT','Discover, assign and monitor autonomous anchors.'),
                  ('Survey & calibration','Enter measured coordinates and calibrate angles when required.'),
                  ('Live positioning','RF synchronization, live Tag coordinates and the floor view.'),
                  ('RTLS Platform','Publish live Tag coordinates; approximate positions carry Warning status.'),
                  ('Sessions & replay','Review recorded measurements and positions locally.')]
        if not 0<=index<len(headings):return
        self.page_title.setText(headings[index][0]);self.page_subtitle.setText(headings[index][1])
        if self.navigation.currentRow()!=index:
            self.navigation.blockSignals(True);self.navigation.setCurrentRow(index);self.navigation.blockSignals(False)
        self.apply_language()

    def populate_profile(self):
        super().populate_profile()
        if hasattr(self,'survey_confirm'):self.survey_confirm.setChecked(self.profile.survey_verified)
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
        p.survey_verified=self.survey_confirm.isChecked()
        p.transport=self.transport_combo.currentData()
        if hasattr(self,'ble_scan_mode'):
            p.ble_scan_mode=self.ble_scan_mode.currentData();p.ble_scan_seconds=self.ble_scan_seconds.value()
        return p

    def change_transport(self):
        if self.controller or self.cloud or self.busy:
            raise ValueError('Disconnect acquisition and RTLS before changing connection mode.')
        self.profile.transport=self.transport_combo.currentData()
        ble=self.profile.transport=='ble'
        heading='VALIDATION ns' if ble else 'RMS ns'
        self.clock_table.horizontalHeaderItem(3).setData(0x1000,heading)
        self.clock_table.horizontalHeaderItem(3).setText(heading)
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
        if not diagnostic:self.plot.profile=p;self.plot.clear_position();self.plot.update()
        self.log('BLE reception opened. Autonomous UWB radios remain active independently of this PC.')
        self.refresh_status()

    def start_anchors(self):
        if self.transport_combo.currentData()=='ble':
            if not self.controller:raise ValueError('Connect BLE first.')
            if not self.controller.profile.survey_verified:
                raise ValueError('Confirm measured anchor coordinates before starting positions. Use BLE diagnostics for bench tests.')
        return super().start_anchors()

    def connect_cloud(self):
        p=self.controller.profile if self.controller else self.collect()
        if p.transport=='ble' and not p.survey_verified:
            raise ValueError('RTLS publishing requires confirmed measured anchor coordinates.')
        from .coordinates import require_floor
        require_floor(p)
        return super().connect_cloud()

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
            self.controller.pipe.continuous_display=self.continuity_check.isChecked();state=self.controller.snapshot();self.plot.set_live(state.get('preview'),self.controller.health()['devices']);age='—' if state['tag_age_s'] is None else str(state['tag_age_s'])+' s'
            status=f"BLE {len(state['connected'])}/{len(self.profile.anchors)} | RF frames {state['rf_total']} | Tag age {age} | Clock {state['clock_status']} | Display updates {state.get('continuous_estimates',0)} | Accepted fixes {state['fixes']}"
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
            self.start_button.setEnabled(not state['diagnostic'] and self.controller.profile.survey_verified and
                                         not state['running'] and not state['starting'] and not self.busy)
            self.stop_button.setEnabled(state['running'] and not state['diagnostic'])
            self.position_issue.setText(self.tr('Strict / RTLS diagnostics')+'\n'+'\n'.join(diagnostic_lines(state,self.tr)))
            if state.get('preview'):
                preview=state['preview']
                for axis in 'XYZ':self.position_values[axis].setText(f"{preview[axis.lower()+'_m']:.3f}")
                self.quality.setText(('Accepted position' if preview.get('accepted') else 'WARNING / estimated position / RTLS publishing enabled when connected')+' '+preview.get('warning',''))
            if not state.get('preview') and not state['fixes'] and state.get('last_solver_rejection'):
                self.quality.setText(self.tr('No accepted position. See the measured uncertainty and rejection reason above.'))
            if not self.controller.profile.survey_verified:
                self.start_button.setEnabled(False)
                status=status.replace('Clock synced','Clock model stable')
                self.ble_live_status.setText(status+' | Survey unverified: clock diagnostics only')
                self.live_status.setText(status+'\nSurvey unverified: clock diagnostics only. Measure anchor coordinates before positioning.')
        elif ble:
            self.plot.set_live(None,[])
            self.live_status.setText('BLE disconnected. Connect anchors to record, then start positioning after surveying.')
            self.ble_live_status.setText('BLE disconnected')
            self.position_issue.setText('')
        else:self.position_issue.setText('')
        self.position_issue.setVisible(bool(self.position_issue.text().strip()))
        if hasattr(self,'gateway_import_button'):self.gateway_import_button.setEnabled(not opened and not self.cloud and not self.busy)
        self.survey_confirm.setEnabled(not opened)
        self.auto_survey_button.setEnabled(ble and not opened and not self.cloud and not self.busy and self.profile.mode=='tdoa_4')
        self.survey_confirm.setVisible(ble)
        for field in (self.anchor_table,self.site,self.floor,self.tag_id,self.bounds):field.setEnabled(not opened)
        if hasattr(self,'frame_status'):
            p=self.controller.profile if self.controller else self.profile
            state=p.coordinate_frame.upper()+(' / confirmed' if p.floor_verified else ' / review required')
            self.frame_status.setText('Coordinates: '+state+' | Z: floor height; site elevation is separate' if p.coordinate_frame=='floor' else 'Coordinates: '+state+' | Align before RTLS publishing')
            self.align_button.setEnabled(not opened and not self.cloud and not self.busy and all(a.position is not None for a in p.anchors))
            self.restore_survey_button.setEnabled(not opened and not self.cloud and not self.busy and bool(p.alignment or p.survey_archive))
        self.apply_language()

    def open_guide(self):
        os.startfile(str(self.root/('docs/INTEGRATED_STANDALONE_GUIDE.v10.th.md' if self.language=='th'
                                    else 'docs/INTEGRATED_STANDALONE_GUIDE.v10.en.md')))

    def closeEvent(self,event):
        if self.busy:
            W.QMessageBox.warning(self,self.tr('Operation running'),self.tr('Wait for Flash/operation to finish before closing.'))
            event.ignore();return
        try:self.close_anchors()
        except Exception as error:self.log(str(error));event.ignore();return
        from .panels import Panel
        for panel in self.findChildren(Panel):
            if panel.dialog:panel.dialog.close()
        event.accept()
