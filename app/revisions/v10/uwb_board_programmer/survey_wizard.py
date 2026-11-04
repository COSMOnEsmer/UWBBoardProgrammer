"""Measured Auto Survey workflow. Original survey profiles are never replaced."""
from pathlib import Path
import threading
import numpy as np
from PySide6 import QtCore,QtWidgets as W
from .models import Profile,save_new
from .ble_controller import run_ble
from .standalone_flashing import inventory
from .survey_workflow import capture_graph,capture_reference,prepare_tag,survey_bindings
from .survey_geometry import solve_reference_survey
from uwb_battery_calibration.capture import capture_reference_ble,inspect_tag


class Events(QtCore.QObject):
    log=QtCore.Signal(str)
    done=QtCore.Signal(object)
    failed=QtCore.Signal(str)


class AutoSurveyDialog(W.QDialog):
    def __init__(self,root,profile,translate=lambda value:value,parent=None):
        super().__init__(parent);self.root=Path(root);self.profile=Profile.from_dict(profile.to_dict());self.t=translate
        survey_bindings(self.profile)
        self.graph=None;self.references={};self.preview=None;self.saved_profile=None;self.saved_path=None
        self.busy=False;self.cancel_event=threading.Event();self.close_pending=False
        self.events=Events();self.events.log.connect(self.log);self.events.done.connect(self.completed);self.events.failed.connect(self.failed)
        self.setWindowTitle(self.t('Auto Survey / Calibration'));self.resize(1100,850)
        layout=W.QVBoxLayout(self);layout.setContentsMargins(20,20,20,20);layout.setSpacing(12)
        title=W.QLabel(self.t('Measure anchor positions with TWR'));title.setObjectName('PageTitle');layout.addWidget(title)
        self.note(layout,'Measure four Tag reference points: origin, +X, +Y and +Z. The Tag moves between these known points; every anchor stays fixed. One Tag point alone cannot determine anchor XYZ.')
        self.power_summary=self.note(layout,'Battery calibration: power all four Anchors and use CR2032 for the BLE Tag. USB is only needed to prepare Tag firmware. Keep every antenna fixed.')
        self.tabs=W.QTabWidget();layout.addWidget(self.tabs,1)
        self.reference_page();self.preview_page();self.pair_page()
        self.status=W.QLabel(self.t('Ready. Keep anchors fixed during every capture.'));self.status.setWordWrap(True);layout.addWidget(self.status)
        self.logs=W.QPlainTextEdit();self.logs.setReadOnly(True);self.logs.setMaximumHeight(150);layout.addWidget(self.logs)
        row=W.QHBoxLayout();layout.addLayout(row);row.addStretch()
        self.cancel_button=self.button(row,'Close wizard',self.close)
        self.refresh_ports();self.change_tag_control();self.refresh_actions()

    def note(self,layout,text):
        widget=W.QLabel(self.t(text));widget.setWordWrap(True);widget.setObjectName('BodyText');layout.addWidget(widget);return widget

    def button(self,layout,text,action,primary=False):
        button=W.QPushButton(self.t(text));button.clicked.connect(lambda _:self.guard(action))
        if primary:button.setProperty('variant','primary')
        layout.addWidget(button);return button

    def page(self,name):
        page=W.QWidget();layout=W.QVBoxLayout(page);layout.setContentsMargins(16,16,16,16);layout.setSpacing(12)
        scroll=W.QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(page)
        self.tabs.addTab(scroll,self.t(name));return layout

    def pair_page(self):
        layout=self.page('Optional: anchor links')
        self.note(layout,'All four anchors must run Auto Survey firmware. Flash one board at a time in Devices & firmware. Calibration pauses TDoA temporarily and restores standalone operation after capture.')
        self.anchor_list=W.QTableWidget(4,3);self.anchor_list.setHorizontalHeaderLabels([self.t('Anchor'),self.t('UWB MAC'),self.t('Role')])
        self.anchor_list.setEditTriggers(W.QAbstractItemView.NoEditTriggers);self.anchor_list.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch)
        for row,anchor in enumerate(self.profile.anchors):
            for col,value in enumerate((anchor.id,anchor.mac,anchor.role)):self.anchor_list.setItem(row,col,W.QTableWidgetItem(value))
        layout.addWidget(self.anchor_list)
        row=W.QHBoxLayout();layout.addLayout(row);self.capture_pairs_button=self.button(row,'Capture six anchor pairs',self.capture_pairs,True);row.addStretch()
        self.pair_status=self.note(layout,'Anchor-pair ranging is an optional link diagnostic. It is not required for the four-reference survey.')
        self.note(layout,'A failed or NLOS anchor link is recorded. It does not prevent measurement from known Tag references. Keep all anchors powered for this optional test.')
        layout.addStretch()

    def reference_page(self):
        layout=self.page('1. Measured Tag references')
        row=W.QHBoxLayout();layout.addLayout(row);row.addWidget(W.QLabel(self.t('Tag control')))
        self.tag_control=W.QComboBox();self.tag_control.addItem(self.t('BLE Tag / CR2032'),'ble');self.tag_control.addItem(self.t('USB Tag / legacy'),'usb');row.addWidget(self.tag_control,1)
        self.check_tag_button=self.button(row,'Check BLE Tag',self.check_ble_tag)
        self.tag_power_note=self.note(layout,'Flash the BLE Tag image once by USB, then disconnect USB and use CR2032. Reset the Tag to open a 15-minute BLE calibration window. Current consumption and battery life still require measurement.')
        row=W.QHBoxLayout();layout.addLayout(row);row.addWidget(W.QLabel(self.t('USB port for firmware preparation')));self.tag_port=W.QComboBox();row.addWidget(self.tag_port,1);self.button(row,'Refresh USB ports',self.refresh_ports)
        row=W.QHBoxLayout();layout.addLayout(row)
        self.prepare_usb_button=self.button(row,'Prepare Tag firmware by USB',lambda:self.flash_tag('tag_ble_calibration' if self.tag_control.currentData()=='ble' else 'tag_setup'),True)
        self.prepare_battery_button=self.button(row,'Prepare battery Tag',lambda:self.flash_tag('tag_battery'))
        self.tag_status=self.note(layout,'Select USB only when preparing Tag firmware. BLE calibration does not require a Tag COM port.')
        row=W.QHBoxLayout();layout.addLayout(row);row.addWidget(W.QLabel(self.t('Range capture per anchor')))
        self.capture_seconds=W.QSpinBox();self.capture_seconds.setRange(5,20);self.capture_seconds.setSingleStep(5);self.capture_seconds.setSuffix(' s');self.capture_seconds.setValue(20);row.addWidget(self.capture_seconds);row.addStretch()
        self.note(layout,'Longer captures collect more samples. LOS and range-consistency gates remain unchanged.')
        self.note(layout,'Mark origin (0,0,0), X (Lx,0,0), Y (0,Ly,0) and Z (0,0,Lz). Measure Lx, Ly and Lz with a tape or laser. X and Y must be perpendicular and level; Z must be vertically above origin. Measure at the Tag antenna.')
        row=W.QHBoxLayout();layout.addLayout(row)
        self.measured_x=W.QLineEdit();self.measured_x.setPlaceholderText(self.t('Measured Lx (m)'));row.addWidget(self.measured_x)
        self.measured_y=W.QLineEdit();self.measured_y.setPlaceholderText(self.t('Measured Ly (m)'));row.addWidget(self.measured_y)
        self.measured_z=W.QLineEdit();self.measured_z.setPlaceholderText(self.t('Measured Lz (m)'));row.addWidget(self.measured_z)
        self.axes_confirm=W.QCheckBox(self.t('The reference axes are physically measured, perpendicular and aligned with vertical +Z.'));layout.addWidget(self.axes_confirm)
        self.fixed_positions=W.QCheckBox(self.t('Every Anchor stays at its marked installation point throughout this survey.'));layout.addWidget(self.fixed_positions)
        row=W.QHBoxLayout();layout.addLayout(row)
        self.origin_button=self.button(row,'Capture origin',lambda:self.capture_point('origin'),True)
        self.x_button=self.button(row,'Capture +X point',lambda:self.capture_point('x'))
        self.y_button=self.button(row,'Capture +Y point',lambda:self.capture_point('y'))
        self.z_button=self.button(row,'Capture +Z point',lambda:self.capture_point('z'))
        self.reference_status=self.note(layout,'Reference captures: 0 / 4')
        self.note(layout,'Use baselines of at least 0.4 m, preferably 1 m or more where space permits. Keep the Tag fixed until the selected point shows 4/4 anchor ranges. Keep clear line of sight.')
        self.usb_power_note=self.note(layout,'With limited USB power, capture the powered anchors first. Keep the Tag at the same point, switch power to a missing anchor, then press the same capture button again. Completed ranges are retained.')
        self.reset_references_button=self.button(layout,'Reset reference captures',self.reset_references)
        for field in (self.measured_x,self.measured_y,self.measured_z):field.textChanged.connect(self.invalidate_preview)
        self.axes_confirm.toggled.connect(self.invalidate_preview)
        self.fixed_positions.toggled.connect(self.invalidate_preview)
        self.tag_control.currentIndexChanged.connect(self.change_tag_control)
        layout.addStretch()

    def preview_page(self):
        layout=self.page('2. Review and save')
        self.note(layout,'Coordinates use the measured Tag reference frame. Z is relative to the origin antenna height. Matching this frame to an RTLS floor map is a separate setup step.')
        row=W.QHBoxLayout();layout.addLayout(row);self.compute_button=self.button(row,'Calculate anchor coordinates',self.calculate,True);row.addStretch()
        self.table=W.QTableWidget(4,6);self.table.setHorizontalHeaderLabels([self.t('Anchor'),'X (m)','Y (m)','Z (m)',self.t('Fit RMS (m)'),self.t('Model std XYZ (m)')])
        self.table.setEditTriggers(W.QAbstractItemView.NoEditTriggers);self.table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch);layout.addWidget(self.table)
        self.preview_status=self.note(layout,'Coordinates appear after all measured ranges and reference checks pass.')
        self.restore_battery=W.QCheckBox(self.t('Prepare the normal battery Tag when saving this survey'));self.restore_battery.setChecked(True);layout.addWidget(self.restore_battery)
        self.save_button=self.button(layout,'Save new profile and finish',self.save_survey,True)
        self.note(layout,'Model uncertainty includes a 0.05 m range floor. It does not prove absolute accuracy or calibrate antenna delay. Validate later at separate known Tag positions and heights. Poor 3D TDoA geometry can still prevent position fixes.')

    def invalidate_preview(self,*args):
        self.preview=None
        if hasattr(self,'save_button'):self.refresh_actions()

    def change_tag_control(self,*args):
        ble=self.tag_control.currentData()=='ble'
        self.check_tag_button.setVisible(ble);self.prepare_battery_button.setVisible(not ble)
        self.usb_power_note.setVisible(not ble)
        self.power_summary.setText(self.t('Battery calibration: power all four Anchors and use CR2032 for the BLE Tag. USB is only needed to prepare Tag firmware. Keep every antenna fixed.' if ble else 'Calibration power: USB Tag + one Anchor at a time. Keep antenna positions fixed; move the Power Bank or cable. Restart if an antenna moves.'))
        self.restore_battery.setChecked(not ble);self.restore_battery.setVisible(not ble)
        self.tag_power_note.setText(self.t('Flash the BLE Tag image once by USB, then disconnect USB and use CR2032. Reset the Tag to open a 15-minute BLE calibration window. Current consumption and battery life still require measurement.' if ble else 'USB legacy mode needs the USB calibration Tag image and its USB cable throughout capture.'))
        self.invalidate_preview()

    def check_ble_tag(self):
        def done(info):
            self.tag_status.setText('Type2DK / '+info['firmware']+' / '+info['mac']+' / '+str(info['ble_window_remaining_s'])+' s')
            self.status.setText(self.t('BLE Tag verified. Keep it at the measured reference point.'))
        self.run_job(lambda:run_ble(inspect_tag(self.profile,self.events.log.emit)),done)

    def refresh_ports(self):
        previous=self.tag_port.currentData();self.tag_port.clear()
        for port in inventory():self.tag_port.addItem(port.device+' / USB '+port.serial_number,(port.device,port.serial_number))
        for index in range(self.tag_port.count()):
            if self.tag_port.itemData(index)==previous:self.tag_port.setCurrentIndex(index)

    def selected_tag(self):
        value=self.tag_port.currentData()
        if not value:raise ValueError('Connect the Type2DK Tag by USB and refresh ports')
        return value

    def guard(self,action):
        try:action()
        except Exception as error:self.failed(type(error).__name__+': '+str(error))

    def log(self,text):self.logs.appendPlainText(str(text))

    def refresh_actions(self):
        self.tabs.setEnabled(not self.busy)
        complete=lambda name:bool(self.references.get(name,{}).get('complete'))
        ready=self.axes_confirm.isChecked() and self.fixed_positions.isChecked()
        self.origin_button.setEnabled(ready and not complete('origin'))
        self.x_button.setEnabled(ready and complete('origin') and not complete('x'))
        self.y_button.setEnabled(ready and complete('x') and not complete('y'))
        self.z_button.setEnabled(ready and complete('y') and not complete('z'))
        self.compute_button.setEnabled(all(complete(name) for name in ('origin','x','y','z')))
        self.save_button.setEnabled(self.preview is not None)
        for field in (self.measured_x,self.measured_y,self.measured_z,self.axes_confirm,self.fixed_positions,self.tag_control):field.setEnabled(not self.references)

    def run_job(self,operation,callback):
        if self.busy:raise ValueError('An Auto Survey operation is already running')
        self.busy=True;self.cancel_event.clear();self.on_done=callback;self.refresh_actions()
        self.status.setText(self.t('Working. Keep the selected USB board connected and all measured devices still.'))
        def work():
            try:self.events.done.emit(operation())
            except Exception as error:self.events.failed.emit(type(error).__name__+': '+str(error))
        self.worker=threading.Thread(target=work,daemon=True,name='Auto-Survey');self.worker.start()

    def completed(self,value):
        self.busy=False
        if self.close_pending:self.reject();return
        self.guard(lambda:self.on_done(value));self.refresh_actions()

    def failed(self,text):
        self.busy=False;self.status.setText(self.t('Operation stopped')+': '+text);self.log(text);self.refresh_actions()
        if self.close_pending:self.reject()

    def capture_pairs(self):
        def operation():
            value=run_ble(capture_graph(self.profile,self.events.log.emit,self.cancel_event,
                          lambda name,data:save_new(self.root/'data/surveys',name,data)))
            value['report']=str(save_new(self.root/'data/surveys','anchor-ranges',value));return value
        def done(value):
            self.graph=value
            self.pair_status.setText(self.t('Accepted anchor links')+f": {len(value['edges'])}/6\n"+'\n'.join(key+': '+error for key,error in value.get('errors',{}).items()))
            self.status.setText(value['report'])
        self.run_job(operation,done)

    def capture_point(self,name):
        points=self.reference_positions()
        ble=self.tag_control.currentData()=='ble'
        port,usb_serial=(None,None) if ble else self.selected_tag()
        previous=self.references.get(name)
        seconds=self.capture_seconds.value()
        def operation():
            recorder=lambda kind,data:save_new(self.root/'data/surveys',kind,data)
            value=run_ble(capture_reference_ble(self.profile,self.events.log.emit,self.cancel_event,recorder,
                          previous=previous,known_position=points[name],capture_seconds=seconds) if ble else
                          capture_reference(self.profile,None,port,usb_serial,self.events.log.emit,self.cancel_event,recorder,
                          previous=previous,known_position=points[name],capture_seconds=seconds))
            value['report']=str(save_new(self.root/'data/surveys','tag-reference-'+name,value));return value
        def done(value):
            self.references[name]=value;self.preview=None
            if value.get('tag_info'):
                self.tag_status.setText('Type2DK / '+value['tag_info']['firmware']+' / '+str(value.get('tag_window_remaining_s'))+' s')
            self.reference_status.setText(self.t('Captured reference points')+': '+', '.join(
                key+f" {len(data.get('ranges',{}))}/4" for key,data in self.references.items())+'\n'+
                '\n'.join(aid+f": LOS {q['los']} / NLOS {q['nlos']} / "+self.t('Failed')+f" {q['failed']}" for aid,q in value.get('quality',{}).items())+'\n'+
                '\n'.join(aid+': '+self.t(error) for aid,error in value.get('errors',{}).items()))
            if value.get('missing'):
                self.status.setText(self.t('Keep the Tag fixed. Power a missing anchor, then continue this reference.')+' '+', '.join(value['missing']))
            else:self.status.setText(value['report'])
            if all(self.references.get(key,{}).get('complete') for key in ('origin','x','y','z')):self.tabs.setCurrentIndex(1)
        self.run_job(operation,done)

    def reset_references(self):
        self.references={};self.preview=None;self.reference_status.setText(self.t('Reference captures: 0 / 4'));self.refresh_actions()

    def flash_tag(self,label):
        port,usb_serial=self.selected_tag()
        def done(value):
            self.tag_status.setText(self.t('Tag firmware prepared')+': '+value.get('last_hello',{}).get('version',''))
            self.status.setText(value['report'])
        self.run_job(lambda:prepare_tag(self.root,self.profile,port,usb_serial,label,self.events.log.emit),done)

    def reference_positions(self):
        if not self.axes_confirm.isChecked():raise ValueError('Confirm the physically measured reference axes')
        if not self.fixed_positions.isChecked():raise ValueError('Confirm fixed Anchor installation points before capturing')
        lengths=[float(field.text()) for field in (self.measured_x,self.measured_y,self.measured_z)]
        if not all(np.isfinite(v) and .4<=v<=20 for v in lengths):raise ValueError('Measured reference lengths must be 0.4..20 metres')
        return dict(origin=[0.,0.,0.],x=[lengths[0],0.,0.],y=[0.,lengths[1],0.],z=[0.,0.,lengths[2]])

    def calculate(self):
        points=self.reference_positions()
        if any(value.get('known_position')!=points[name] or not value.get('complete') for name,value in self.references.items()):
            raise ValueError('Reference coordinates changed or captures are incomplete; reset before continuing')
        result=solve_reference_survey([a.id for a in self.profile.anchors],self.references)
        self.preview={'geometry':result,'measured_axes_confirmed':True}
        for row,anchor in enumerate(self.profile.anchors):
            quality=result['anchor_quality'][anchor.id]
            values=[anchor.id,*[f'{v:.3f}' for v in result['anchors'][anchor.id]],f"{quality['residual_m']:.3f}",', '.join(f'{v:.3f}' for v in quality['model_std_m'])]
            for col,value in enumerate(values):self.table.setItem(row,col,W.QTableWidgetItem(value))
        self.preview_status.setText(self.t('Four-reference range fits passed. Review the coordinates before saving.'))
        self.status.setText(self.t('Validate TDoA at separate known Tag positions before claiming accuracy.'))
        save_new(self.root/'data/surveys','survey-preview',self.preview)
        self.refresh_actions()

    def save_survey(self):
        if not self.preview:raise ValueError('Calculate and review the measured coordinates first')
        profile=Profile.from_dict(self.profile.to_dict());profile.name+=' / Auto Survey'
        for anchor in profile.anchors:
            anchor.position=list(self.preview['geometry']['anchors'][anchor.id]);anchor.aoa_verified=False;anchor.rx_bias_m=0.
        xyz=np.array([a.position for a in profile.anchors]+[[0.,0.,0.]])
        profile.bounds=[(xyz.min(axis=0)-.5).tolist(),(xyz.max(axis=0)+.5).tolist()]
        profile.mode='tdoa_4';profile.transport='ble';profile.survey_verified=True;profile.validate(require_ports=False,require_aoa=False)
        # Noise in a planar installation must not masquerade as usable 3D height.
        centered=np.array([a.position for a in profile.anchors]);centered-=centered.mean(axis=0)
        vertical_extent=np.linalg.svd(centered,compute_uv=False)[-1]
        noise=max(max(q['model_std_m']) for q in self.preview['geometry']['anchor_quality'].values())
        if vertical_extent<3*noise:raise ValueError('Anchor height diversity is too small compared with survey uncertainty; coordinates remain in the preview report. Move an anchor vertically and repeat the survey.')
        if self.restore_battery.isChecked():self.selected_tag()  # Check before saving.
        path=save_new(self.root/'config/profiles','site-profile',profile.to_dict())
        save_new(self.root/'data/surveys','survey-result',dict(profile_file=str(path),**self.preview,
                 reference_reports={name:value['report'] for name,value in self.references.items()},anchor_ranges_report=self.graph['report'] if self.graph else None,
                 tdoa_accuracy_validated=False))
        self.saved_profile=profile;self.saved_path=path
        if self.restore_battery.isChecked():
            port,usb_serial=self.selected_tag()
            self.run_job(lambda:prepare_tag(self.root,profile,port,usb_serial,'tag_battery',self.events.log.emit),lambda value:self.accept())
        else:self.accept()

    def closeEvent(self,event):
        if self.busy:
            self.cancel_event.set();self.close_pending=True;self.status.setText(self.t('Stopping after the current radio or Flash operation completes.'));event.ignore()
        else:event.accept()

    def reject(self):
        if self.busy:
            self.cancel_event.set();self.close_pending=True
            self.status.setText(self.t('Stopping after the current radio or Flash operation completes.'))
        else:super().reject()
