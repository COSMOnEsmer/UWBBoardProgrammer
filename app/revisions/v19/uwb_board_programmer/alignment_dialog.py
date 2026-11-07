"""Review a rigid metre-frame registration before saving a new floor profile."""
import json
import numpy as np
from PySide6 import QtCore,QtWidgets as W
from .coordinates import source_profile,align_profile,transform,matrix,fit_references,outside_floor,floor_geometry

class AlignmentDialog(W.QDialog):
    def __init__(self,profile,parent=None):
        super().__init__(parent);self.profile=profile;self.source=source_profile(profile);self.result_profile=None;self.preview=None;self.fit=None
        self.setWindowTitle('Align survey to floor')
        available=W.QApplication.primaryScreen().availableGeometry();self.resize(min(1120,available.width()-60),min(820,available.height()-90))
        root=W.QVBoxLayout(self);scroll=W.QScrollArea();scroll.setWidgetResizable(True);body=W.QWidget();layout=W.QVBoxLayout(body);scroll.setWidget(body);root.addWidget(scroll)
        self.note(layout,'Align survey to floor','Preserve the original survey. Review Anchor and Tag coordinates in the same floor frame before publishing.')
        self.scope=W.QLabel('Site: '+profile.site_id+'   |   Floor: '+profile.floor_id);self.scope.setWordWrap(True);layout.addWidget(self.scope)
        self.note(layout,'1. Floor geometry','Level index is a floor label. Elevation is a site datum offset; it is not added to floor-local telemetry Z.')
        g=profile.floor_geometry or dict(origin_x=0,origin_y=0,length=4,width=4,height=2,elevation=0,level_index=0,meters_per_pixel=.01)
        grid=W.QGridLayout();layout.addLayout(grid);self.geometry={}
        for n,(key,title,default) in enumerate([('origin_x','Origin X (m)',0),('origin_y','Origin Y (m)',0),('length','Length X (m)',4),('width','Width Y (m)',4),('height','Height Z (m)',2),('elevation','Elevation (m)',0),('level_index','Level index',0),('meters_per_pixel','Metres per pixel',.01)]):
            spin=self.spin(g.get(key) if g.get(key) is not None else default);self.geometry[key]=spin
            if key in ('length','width','height','meters_per_pixel'):spin.setMinimum(.0001)
            grid.addWidget(W.QLabel(title),2*(n//4),n%4);grid.addWidget(spin,2*(n//4)+1,n%4)
        self.note(layout,'2. Registration','The A4 preset makes A4 X/Y zero and keeps its existing Z. Confirm whether those Z values already represent height above the floor.')
        row=W.QHBoxLayout();layout.addLayout(row);self.mode=W.QComboBox();self.mode.addItems(['Anchor reference','Survey origin','Paired reference points']);row.addWidget(self.mode)
        self.anchor=W.QComboBox()
        for a in self.source.anchors:self.anchor.addItem(a.id,a.mac)
        self.anchor.setCurrentIndex(len(self.source.anchors)-1);row.addWidget(self.anchor)
        row.addWidget(W.QLabel('Yaw to floor (deg)'));self.yaw=self.spin(0);self.yaw.setRange(-180,180);row.addWidget(self.yaw)
        row=W.QHBoxLayout();layout.addLayout(row);self.target=[]
        for axis in 'XYZ':
            row.addWidget(W.QLabel('Reference floor '+axis+' (m)'));spin=self.spin(0);self.target.append(spin);row.addWidget(spin)
        self.keep_z=W.QCheckBox('Keep existing Z (already floor-relative)');self.keep_z.setChecked(True);layout.addWidget(self.keep_z)
        self.anchor.currentIndexChanged.connect(self.reference_changed);self.keep_z.toggled.connect(self.reference_changed);self.mode.currentIndexChanged.connect(self.reference_changed);self.reference_changed()
        self.refs_toggle=W.QPushButton('Optional paired references');self.refs_toggle.setCheckable(True);layout.addWidget(self.refs_toggle)
        self.refs_body=W.QWidget();refs_layout=W.QVBoxLayout(self.refs_body);refs_layout.setContentsMargins(0,0,0,0);layout.addWidget(self.refs_body)
        self.refs_toggle.toggled.connect(self.refs_body.setVisible);self.refs_body.hide()
        self.note(refs_layout,'Paired reference points','Enter at least two paired XYZ points with horizontal separation. +Z must already be vertical. Three or more points are recommended. Scale is fixed at 1.')
        self.references=W.QTableWidget(4,6);self.references.setHorizontalHeaderLabels(['Survey X','Survey Y','Survey Z','Floor X','Floor Y','Floor Z']);self.references.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch);self.references.setFixedHeight(152);refs_layout.addWidget(self.references)
        row=W.QHBoxLayout();refs_layout.addLayout(row);fit=W.QPushButton('Fit reference points');fit.clicked.connect(self.fit_points);row.addWidget(fit);row.addStretch();self.fit_status=W.QLabel('No reference fit');row.addWidget(self.fit_status)
        self.note(layout,'3. Preview and independent check','Coordinates are not clamped to the floor. Out-of-floor Anchors are listed as warnings. Frame confirmation does not prove RF positioning accuracy.')
        self.table=W.QTableWidget(0,7);self.table.setHorizontalHeaderLabels(['Anchor','Survey X','Survey Y','Survey Z','Floor X','Floor Y','Floor Z']);self.table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch);self.table.setFixedHeight(196);layout.addWidget(self.table)
        self.check_source=W.QLineEdit();self.check_source.setPlaceholderText('Independent check: Survey X,Y,Z (optional)')
        self.check_target=W.QLineEdit();self.check_target.setPlaceholderText('Measured Floor X,Y,Z for that point')
        row=W.QHBoxLayout();layout.addLayout(row);row.addWidget(self.check_source);row.addWidget(self.check_target)
        self.confirm=W.QCheckBox('I confirm this floor, axis direction and Z reference match the physical installation');root.addWidget(self.confirm)
        self.status=W.QLabel();self.status.setWordWrap(True);self.status.setMaximumHeight(90);root.addWidget(self.status)
        buttons=W.QDialogButtonBox();preview=buttons.addButton('Preview alignment',W.QDialogButtonBox.ActionRole);save=buttons.addButton('Use aligned profile',W.QDialogButtonBox.AcceptRole);buttons.addButton(W.QDialogButtonBox.Cancel)
        preview.clicked.connect(self.calculate);save.clicked.connect(self.apply);buttons.rejected.connect(self.reject);root.addWidget(buttons)
        self.references.itemChanged.connect(self.invalidate_fit)
        self.calculate()
        if parent and hasattr(parent,'tr'):
            from .i18n import localize_widgets
            localize_widgets(self,parent.tr)
    def spin(self,value):
        spin=W.QDoubleSpinBox();spin.setRange(-10000,10000);spin.setDecimals(4);spin.setValue(float(value));return spin
    def note(self,layout,title,text):
        label=W.QLabel(title);label.setObjectName('CardTitle');layout.addWidget(label);label=W.QLabel(text);label.setWordWrap(True);label.setObjectName('BodyText');layout.addWidget(label)
    def reference_changed(self,*args):
        origin=self.mode.currentIndex()==1
        self.anchor.setEnabled(self.mode.currentIndex()==0)
        if self.keep_z.isChecked():self.target[2].setValue(0 if origin else self.source.anchors[self.anchor.currentIndex()].position[2])
        self.target[2].setEnabled(not self.keep_z.isChecked())
        paired=self.mode.currentIndex()==2;self.yaw.setEnabled(not paired)
        if paired and hasattr(self,'refs_toggle'):self.refs_toggle.setChecked(True)
        for spin in self.target:spin.setEnabled(not paired and (spin is not self.target[2] or not self.keep_z.isChecked()))
    def invalidate_fit(self,*args):
        self.fit=None;self.fit_status.setText('Reference points changed; fit again')
    def fit_points(self):
        try:
            rows=[]
            for row in range(self.references.rowCount()):
                texts=[self.references.item(row,col).text().strip() if self.references.item(row,col) else '' for col in range(6)]
                if not any(texts):continue
                if not all(texts):raise ValueError('Complete all six values for each reference row')
                rows.append(list(map(float,texts)))
            self.fit=fit_references([r[:3] for r in rows],[r[3:] for r in rows]);self.fit['references']=[dict(survey=r[:3],floor=r[3:]) for r in rows]
            self.yaw.setValue(self.fit['yaw_deg']);self.mode.setCurrentIndex(2);self.fit_status.setText('RMS '+f"{self.fit['rms_m']:.4f}"+' m');self.calculate()
        except Exception as e:self.fit=None;self.status.setText(str(e))
    def settings(self):
        geometry=dict(self.profile.floor_geometry)
        geometry.update({key:spin.value() for key,spin in self.geometry.items()});geometry['level_index']=int(geometry['level_index']);geometry['id']=self.profile.floor_id
        yaw=self.yaw.value();target=np.array([s.value() for s in self.target])
        if self.mode.currentIndex()==2:
            if not self.fit:raise ValueError('Fit paired references first')
            yaw=self.fit['yaw_deg'];offset=np.array(self.fit['translation_m'])
        elif self.mode.currentIndex()==1:offset=target
        else:offset=target-matrix(yaw)@np.array(self.source.anchors[self.anchor.currentIndex()].position)
        return geometry,yaw,offset
    def calculate(self):
        try:
            geometry,yaw,offset=self.settings()
            self.preview=align_profile(self.profile,yaw,offset,geometry,self.confirm.isChecked(),self.fit.get('references') if self.fit else [])
            self.table.setRowCount(len(self.preview.anchors))
            for n,(s,f) in enumerate(zip(self.source.anchors,self.preview.anchors)):
                for col,value in enumerate([f.id]+list(s.position)+list(f.position)):
                    item=W.QTableWidgetItem(value if isinstance(value,str) else f'{value:.4f}');item.setFlags(item.flags()&~QtCore.Qt.ItemIsEditable);self.table.setItem(n,col,item)
            message=f'Floor transform: yaw {yaw:.4f} deg; offset {offset.tolist()} m. Original survey retained. Elevation is not added to Z.'
            outside=outside_floor(self.preview)
            if outside:message+=' WARNING outside floor: '+', '.join(outside)
            if bool(self.check_source.text().strip())!=bool(self.check_target.text().strip()):raise ValueError('Enter both independent check coordinates')
            if self.check_source.text().strip():
                s=list(map(float,self.check_source.text().split(',')));f=list(map(float,self.check_target.text().split(',')))
                if len(f)!=3 or not np.all(np.isfinite(f)):raise ValueError('Independent check requires finite XYZ')
                error=float(np.linalg.norm(np.array(transform(s,yaw,offset))-f));self.preview.alignment['independent_check']=dict(survey=s,floor=f,error_m=error)
                message+=f' Independent check error: {error:.4f} m.'
                if error>.10:raise ValueError(message+' Check exceeds 0.10 m; review registration.')
            else:message+=' Independent physical check not recorded.'
            self.status.setText(message);return True
        except Exception as error:self.preview=None;self.status.setText(str(error));return False
    def apply(self):
        if not self.confirm.isChecked():self.status.setText('Confirm the floor, axes and Z reference before applying');return
        if self.calculate():self.result_profile=self.preview;self.accept()
