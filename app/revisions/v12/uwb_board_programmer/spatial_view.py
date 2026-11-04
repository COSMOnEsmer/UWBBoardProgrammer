"""CPU-rendered interactive 2D/3D display; never generates or publishes fixes."""
import math,time
import numpy as np
from PySide6 import QtCore,QtGui,QtWidgets as W

class FloorPlot(W.QWidget):
    def __init__(self):
        super().__init__();self.profile=None;self.trail=[];self.live=None;self.states={}
        self.three=False;self.yaw=.6;self.pitch=.6;self.zoom=1.;self.drag=None;self.last=0
        self.setMinimumHeight(260)
        self.toggle=W.QPushButton('3D',self);self.toggle.setGeometry(8,8,65,32);self.toggle.clicked.connect(self.switch)
        self.home=W.QPushButton('Reset view',self);self.home.setGeometry(80,8,110,32);self.home.clicked.connect(self.reset_view)
    def switch(self):self.three=not self.three;self.toggle.setText('2D' if self.three else '3D');self.update()
    def reset_view(self):self.zoom=1.;self.yaw=.6;self.pitch=.6;self.update()
    def set_fix(self,fix):
        self.live={**fix,'accepted':True};self.last=time.monotonic();self.trail.append((fix['x_m'],fix['y_m'],fix['z_m']));self.trail=self.trail[-300:];self.update()
    def set_live(self,preview,devices):
        self.live=preview;self.states={d['device_id']:d['status'] for d in devices}
        if preview:self.last=time.monotonic()
        self.update()
    def mouseDoubleClickEvent(self,event):self.switch()
    def mousePressEvent(self,event):self.drag=event.position()
    def mouseReleaseEvent(self,event):self.drag=None
    def mouseMoveEvent(self,event):
        if self.drag is not None and self.three:
            delta=event.position()-self.drag;self.drag=event.position();self.yaw+=delta.x()*.01;self.pitch=max(-1.5,min(1.5,self.pitch+delta.y()*.01));self.update()
    def wheelEvent(self,event):self.zoom=max(.2,min(8,self.zoom*math.exp(event.angleDelta().y()/1200)));self.update();event.accept()
    def paintEvent(self,event):
        p=QtGui.QPainter(self);p.setRenderHint(QtGui.QPainter.Antialiasing);p.fillRect(self.rect(),QtGui.QColor('white'))
        if not self.profile:p.end();return
        lo,hi=np.asarray(self.profile.bounds,float);center=(lo+hi)/2
        scale=min(max(1,self.width()-130),max(1,self.height()-100))/max(float(np.max(hi-lo)),.1)*self.zoom
        def point(value):
            x,y,z=np.asarray(value)-center
            if self.three:
                x,y=math.cos(self.yaw)*x-math.sin(self.yaw)*y,math.sin(self.yaw)*x+math.cos(self.yaw)*y
                y=math.sin(self.pitch)*y+math.cos(self.pitch)*z
            return QtCore.QPointF(self.width()/2+x*scale,(self.height()+35)/2-y*scale)
        p.setPen(QtGui.QColor('#dce5ef'))
        for n in range(11):
            x=lo[0]+(hi[0]-lo[0])*n/10;y=lo[1]+(hi[1]-lo[1])*n/10
            p.drawLine(point([x,lo[1],lo[2]]),point([x,hi[1],lo[2]]));p.drawLine(point([lo[0],y,lo[2]]),point([hi[0],y,lo[2]]))
        for axis,label,color in [(0,'X','#c04e54'),(1,'Y','#319576'),(2,'Z','#467cb8')]:
            if axis==2 and not self.three:continue
            end=lo.copy();end[axis]=hi[axis];p.setPen(QtGui.QPen(QtGui.QColor(color),2));p.drawLine(point(lo),point(end));p.drawText(point(end)+QtCore.QPointF(5,-5),label+' (m)')
        p.setFont(QtGui.QFont('Segoe UI',9))
        for a in self.profile.anchors:
            if a.position is None:continue
            q=point(a.position);online=self.states.get(a.id)=='online';color='#16a36b' if online else '#9aa4b2'
            p.setPen(QtCore.Qt.NoPen);p.setBrush(QtGui.QColor(color));p.drawEllipse(q,7,7)
            p.setPen(QtGui.QColor('#43556c'));p.drawText(q+QtCore.QPointF(10,-9),a.id+' / '+('Online' if online else 'Offline'))
        live=self.live if time.monotonic()-self.last<3 else None
        if live:
            q=point([live['x_m'],live['y_m'],live['z_m']]);color='#15958b' if live.get('accepted') else '#df940b'
            p.setPen(QtGui.QPen(QtGui.QColor(color),2));p.setBrush(QtGui.QColor(color));p.drawEllipse(q,8,8)
            p.drawText(q+QtCore.QPointF(12,20),'Tag'+(' / WARNING' if not live.get('accepted') else ''))
        else:
            p.setPen(QtGui.QColor('#75859a'));p.drawText(12,self.height()-12,'Waiting for a computable, fresh Tag position')
        p.end()
