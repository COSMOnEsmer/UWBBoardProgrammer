"""Explicit local mapping of a gateway's site/floor/anchor configuration."""
from PySide6 import QtCore,QtWidgets as W
from .models import Profile

class GatewaySetup(W.QDialog):
    def __init__(self,profile,config,parent=None):
        super().__init__(parent);self.profile=profile;self.config=config;self.result_profile=None
        self.setWindowTitle('Gateway configuration · review local mapping');self.resize(900,560)
        layout=W.QVBoxLayout(self);site=config.get('site',{})
        layout.addWidget(W.QLabel('Site: '+str(site.get('name',''))+' / '+str(site.get('id',''))))
        layout.addWidget(W.QLabel('Select the floor and map each physical UWB board to its registered server Anchor ID.'))
        self.floor=W.QComboBox()
        for floor in config.get('floors',[]):self.floor.addItem(str(floor.get('name',floor['id']))+' / '+floor['id'],floor['id'])
        index=self.floor.findData(profile.floor_id)
        if index>=0:self.floor.setCurrentIndex(index)
        layout.addWidget(self.floor);self.table=W.QTableWidget(len(profile.anchors),3)
        self.table.setHorizontalHeaderLabels(['Physical board MAC','Current local ID','Server Anchor ID']);self.table.horizontalHeader().setSectionResizeMode(W.QHeaderView.Stretch);layout.addWidget(self.table)
        self.tag=W.QLineEdit(profile.tag_id);layout.addWidget(W.QLabel('Registered Tag ID'));layout.addWidget(self.tag)
        self.coordinates=W.QCheckBox('Use selected server anchor coordinates');layout.addWidget(self.coordinates)
        self.confirm=W.QCheckBox('I confirm these server coordinates match the measured physical installation');layout.addWidget(self.confirm)
        note=W.QLabel('This saves a NEW local profile. It does not modify server settings or rename devices on the server.');note.setWordWrap(True);layout.addWidget(note)
        self.error=W.QLabel();self.error.setWordWrap(True);layout.addWidget(self.error)
        buttons=W.QDialogButtonBox(W.QDialogButtonBox.Save|W.QDialogButtonBox.Cancel);buttons.accepted.connect(self.apply);buttons.rejected.connect(self.reject);layout.addWidget(buttons)
        self.floor.currentIndexChanged.connect(self.populate);self.populate()
    def populate(self,*args):
        self.combos=[]
        for row,anchor in enumerate(self.profile.anchors):
            for col,text in enumerate((anchor.mac,anchor.id)):
                item=W.QTableWidgetItem(text);item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable);self.table.setItem(row,col,item)
            combo=W.QComboBox();combo.addItem('Select registered anchor',None)
            for remote in self.config.get('anchors',[]):
                if remote.get('floorId')==self.floor.currentData() and remote.get('role')==anchor.role:combo.addItem(remote['id'],remote['id'])
            direct=combo.findData(anchor.id)
            if direct>=0:combo.setCurrentIndex(direct)
            self.table.setCellWidget(row,2,combo);self.combos.append(combo)
    def apply(self):
        ids=[box.currentData() for box in self.combos]
        if not all(ids) or len(set(ids))!=len(ids):self.error.setText('Select a different matching server anchor for every physical board.');return
        if not self.tag.text().strip():self.error.setText('Enter the registered Tag ID.');return
        profile=Profile.from_dict(self.profile.to_dict());profile.site_id=self.config['site']['id'];profile.floor_id=self.floor.currentData();profile.tag_id=self.tag.text().strip()
        from .coordinates import floor_geometry,floor_bounds
        if profile.alignment:profile.survey_archive=profile.alignment['source_profile']
        profile.floor_geometry=floor_geometry(next(f for f in self.config['floors'] if f['id']==profile.floor_id))
        profile.floor_geometry['config_version']=self.config.get('configVersion')
        if profile.site_id!=self.profile.site_id or profile.floor_id!=self.profile.floor_id:
            profile.alignment={};profile.coordinate_frame='unmapped';profile.floor_verified=False
        remote={row['id']:row for row in self.config['anchors']}
        for anchor,aid in zip(profile.anchors,ids):
            anchor.id=aid
            if self.coordinates.isChecked():
                values=[remote[aid].get(key) for key in ('posXM','posYM','posZM')]
                if any(value is None for value in values):self.error.setText('Server anchor coordinates are incomplete.');return
                anchor.position=values
        if self.coordinates.isChecked():
            import numpy as np
            xyz=np.array([a.position for a in profile.anchors],float);margin=max(1.,float(np.ptp(xyz,axis=0).max())*.2)
            lo=xyz.min(axis=0)-margin;hi=xyz.max(axis=0)+margin;lo[2]=min(0.,lo[2]);hi[2]=max(3.,hi[2]);profile.bounds=[lo.tolist(),hi.tolist()]
            profile.survey_verified=self.confirm.isChecked();profile.coordinate_frame='floor';profile.floor_verified=self.confirm.isChecked();profile.alignment={}
            try:profile.bounds=floor_bounds(profile.floor_geometry)
            except (ValueError,TypeError):pass
        profile.name='Gateway workspace';self.result_profile=profile;self.accept()
