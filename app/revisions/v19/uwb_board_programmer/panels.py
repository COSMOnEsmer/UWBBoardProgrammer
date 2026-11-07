"""Single-header cards in a resizable dock workspace, with native floating windows."""
from PySide6 import QtCore,QtWidgets as W

class Panel(W.QFrame):
    def __init__(self,title,owner):
        super().__init__();self.setObjectName('Card');self.title=title;self.owner=owner
        self.dialog=None;self.dock=None;self.collapsed=False
        layout=W.QVBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(0)
        self.header=W.QFrame();self.header.setObjectName('PanelHeader');header=W.QHBoxLayout(self.header);header.setContentsMargins(18,12,16,8)
        label=W.QLabel(title);label.setObjectName('CardTitle');header.addWidget(label);header.addStretch()
        self.collapse=W.QPushButton('Collapse');self.collapse.setObjectName('PanelAction');self.collapse.clicked.connect(self.toggle);header.addWidget(self.collapse)
        self.detach=W.QPushButton('Open window');self.detach.setObjectName('PanelAction');self.detach.clicked.connect(self.float_or_dock);header.addWidget(self.detach)
        layout.addWidget(self.header)
        self.placeholder=W.QLabel('Panel is open in a separate window. Click Attach to restore.');self.placeholder.hide();layout.addWidget(self.placeholder)
        self.body=W.QWidget();self.body_layout=W.QVBoxLayout(self.body);self.body_layout.setContentsMargins(18,4,18,16);self.body_layout.setSpacing(12)
        self.body_layout.setAlignment(QtCore.Qt.AlignTop);layout.addWidget(self.body)
    def toggle(self):
        self.collapsed=not self.collapsed;self.body.setVisible(not self.collapsed);self.collapse.setText('Expand' if self.collapsed else 'Collapse')
        if self.dock:
            self.dock.setMinimumHeight(50 if self.collapsed else self.dock.content_minimum)
            self.dock.setMaximumHeight(54 if self.collapsed else 16777215)
            workspace=self.dock.parentWidget()
            if isinstance(workspace,W.QMainWindow):
                if hasattr(workspace,'_update_minimum'):workspace._update_minimum()
                workspace.resizeDocks([self.dock],[54 if self.collapsed else max(160,self.sizeHint().height()+45)],QtCore.Qt.Vertical)
    def float_or_dock(self):
        if self.dock:self.dock.setFloating(not self.dock.isFloating());self.dock.show();return
        if self.dialog:self.dialog.close();return
        panel=self
        class Floating(W.QDialog):
            def closeEvent(self,event):panel.restore();event.accept()
        dialog=Floating(self.owner);dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose);dialog.setWindowTitle(self.title)
        box=W.QVBoxLayout(dialog);attach=W.QPushButton('Attach');attach.clicked.connect(dialog.close);box.addWidget(attach);box.addWidget(self.body)
        self.dialog=dialog;self.placeholder.show();dialog.resize(800,500);dialog.show()
    def restore(self):
        if self.dock:self.dock.setFloating(False);return
        if not self.dialog:return
        self.dialog.layout().removeWidget(self.body);self.layout().addWidget(self.body);self.body.setVisible(not self.collapsed)
        self.placeholder.hide();self.dialog=None

class Dock(W.QDockWidget):
    def closeEvent(self,event):
        if self.isFloating():self.setFloating(False);self.show()
        event.ignore()

def _remove(layout,widget):
    if not layout:return
    layout.removeWidget(widget)
    for index in range(layout.count()):
        if layout.itemAt(index).layout():_remove(layout.itemAt(index).layout(),widget)

def _dock(workspace,panel):
    dock=Dock(panel.title,workspace);dock.setObjectName('Dock-'+panel.title)
    dock.setFeatures(W.QDockWidget.DockWidgetMovable|W.QDockWidget.DockWidgetFloatable)
    panel.layout().removeWidget(panel.header);dock.setTitleBarWidget(panel.header);dock.setWidget(panel);panel.dock=dock
    dock.setMinimumWidth(220);dock.content_minimum=max(90,panel.minimumSizeHint().height()+panel.header.sizeHint().height()+10);dock.setMinimumHeight(dock.content_minimum)
    def floating(value):
        panel.detach.setText('Attach' if value else 'Open window')
        if value:dock.resize(max(850,dock.width()),max(350,dock.height()))
        if hasattr(workspace,'_update_minimum'):workspace._update_minimum()
    dock.topLevelChanged.connect(floating);workspace.addDockWidget(QtCore.Qt.TopDockWidgetArea,dock)
    panel.show();dock.show();return dock

def enable_free_layout(owner):
    """Purposeful default layouts; divider resizing and floating remain available."""
    owner.panel_workspaces=[];owner.workspace_panels=[]
    for index in range(owner.tabs.count()):
        scroll=owner.tabs.widget(index);page=scroll.widget();panels=page.findChildren(Panel)
        for panel in panels:
            _remove(panel.parentWidget().layout(),panel);panel.setParent(None)
        layout=page.layout();actions=[]
        while layout.count():
            item=layout.takeAt(0)
            if isinstance(item.widget(),W.QPushButton):actions.append(item.widget())
            elif item.widget():item.widget().hide()
        if actions:
            controls=Panel('Workspace actions',owner)
            for button in actions:controls.body_layout.addWidget(button)
            panels.append(controls)
        workspace=W.QMainWindow();workspace.setObjectName('DockWorkspace');workspace.setDockNestingEnabled(True)
        workspace.setDockOptions(W.QMainWindow.AnimatedDocks|W.QMainWindow.AllowNestedDocks)
        workspace.setMinimumHeight(700 if index==2 else 660);layout.addWidget(workspace,1)
        if index==3:
            metrics=[p for p in panels if p.title.startswith(('X  /','Y  /','Z  /'))]
            combined=Panel('Tag coordinates',owner);combined.header.hide()
            row=W.QHBoxLayout();row.setContentsMargins(0,0,0,0);row.setSpacing(8);combined.body_layout.setContentsMargins(0,0,0,0);combined.body_layout.addLayout(row)
            for metric in metrics:
                panels.remove(metric);metric.collapse.hide();metric.detach.hide();row.addWidget(metric,1);metric.show()
            panels.append(combined)
        docks={panel.title:_dock(workspace,panel) for panel in panels}
        owner.panel_workspaces.append(workspace);owner.workspace_panels.append(docks)
        for dock in docks.values():workspace.removeDockWidget(dock)
        if index==2:
            for title,area in [('Anchor geometry',QtCore.Qt.TopDockWidgetArea),('Workspace profile',QtCore.Qt.LeftDockWidgetArea),('Auto Survey',QtCore.Qt.RightDockWidgetArea),('Orientation calibration',QtCore.Qt.BottomDockWidgetArea),('Measurement quality',QtCore.Qt.BottomDockWidgetArea)]:workspace.addDockWidget(area,docks[title])
            workspace.splitDockWidget(docks['Orientation calibration'],docks['Measurement quality'],QtCore.Qt.Vertical)
        elif index==3:
            for title,area in [('Acquisition',QtCore.Qt.TopDockWidgetArea),('Tag coordinates',QtCore.Qt.TopDockWidgetArea),('Floor view',QtCore.Qt.LeftDockWidgetArea),('Clock synchronization',QtCore.Qt.RightDockWidgetArea)]:workspace.addDockWidget(area,docks[title])
            workspace.splitDockWidget(docks['Acquisition'],docks['Tag coordinates'],QtCore.Qt.Vertical)
            dock=docks['Tag coordinates'];dock.setTitleBarWidget(W.QWidget());dock.content_minimum=110;dock.setMinimumHeight(110);dock.setMaximumHeight(120)
        else:
            last=None
            for dock in docks.values():
                if last:workspace.splitDockWidget(last,dock,QtCore.Qt.Vertical)
                else:workspace.addDockWidget(QtCore.Qt.TopDockWidgetArea,dock)
                last=dock
        if index==2:
            workspace.resizeDocks([docks['Workspace profile'],docks['Auto Survey']],[650,430],QtCore.Qt.Horizontal)
            for title in ('Orientation calibration','Measurement quality'):docks[title].widget().toggle()
            workspace.resizeDocks([docks['Anchor geometry'],docks['Workspace profile']],[310,260],QtCore.Qt.Vertical)
        elif index==3:
            workspace.resizeDocks([docks['Floor view'],docks['Clock synchronization']],[750,400],QtCore.Qt.Horizontal)
            workspace.resizeDocks([docks['Acquisition'],docks['Tag coordinates'],docks['Floor view']],[220,110,430],QtCore.Qt.Vertical)
            for title,dock in docks.items():
                if title.startswith(('X  /','Y  /','Z  /')):dock.setMaximumHeight(120);dock.widget().collapse.hide();dock.widget().detach.hide()
        else:workspace.resizeDocks(list(docks.values()),[max(150,p.sizeHint().height()+45) for p in panels],QtCore.Qt.Vertical)
        def settle(w=workspace,d=docks,i=index):
            if i==2:w.resizeDocks([d['Anchor geometry'],d['Workspace profile']],[320,320],QtCore.Qt.Vertical)
            elif i==3:
                w.resizeDocks([d['Acquisition'],d['Tag coordinates'],d['Floor view']],[230,110,470],QtCore.Qt.Vertical)
                w.resizeDocks([d['Floor view'],d['Clock synchronization']],[max(400,w.width()-380),370],QtCore.Qt.Horizontal)
        def update_minimum(w=workspace,d=docks,i=index):
            def height(title):return 0 if d[title].isFloating() else d[title].minimumHeight()
            if i==2:required=height('Anchor geometry')+max(height('Workspace profile'),height('Auto Survey'))+height('Orientation calibration')+height('Measurement quality')+32
            elif i==3:required=height('Acquisition')+height('Tag coordinates')+max(height('Floor view'),height('Clock synchronization'))+24
            else:required=sum(v.minimumHeight() for v in d.values() if not v.isFloating())+8*(len(d)-1)
            w.setMinimumHeight(max(400,required))
        workspace._update_minimum=update_minimum;update_minimum()
        for dock in docks.values():dock.show()
        workspace._settle=settle
        workspace.installEventFilter(LayoutSettle(workspace))
    for panel in owner.findChildren(Panel):
        if panel.title=='Activity log' and panel.dock is None:
            _remove(panel.parentWidget().layout(),panel);dock=_dock(owner,panel)
            owner.addDockWidget(QtCore.Qt.BottomDockWidgetArea,dock);panel.toggle();owner.activity_dock=dock

def wrap_remaining_cards(owner):
    def locate(layout,widget):
        if not layout:return None
        if layout.indexOf(widget)>=0:return layout
        for index in range(layout.count()):
            nested=layout.itemAt(index).layout();result=locate(nested,widget) if nested else None
            if result is not None:return result
        return None
    for frame in list(owner.findChildren(W.QFrame)):
        if isinstance(frame,Panel) or frame.objectName()!='Card':continue
        container=locate(frame.parentWidget().layout(),frame)
        if container is None:continue
        labels=frame.findChildren(W.QLabel);heading=next((label for label in labels if label.objectName() in ('CardTitle','MetricLabel')),None)
        title=(heading.property('i18n_text_source') or heading.text()) if heading else 'Panel'
        if heading:heading.hide()
        panel=Panel(title,owner);container.replaceWidget(frame,panel);frame.setObjectName('PanelContent')
        if frame.layout():frame.layout().setContentsMargins(0,0,0,0);frame.layout().setAlignment(QtCore.Qt.AlignTop)
        panel.body_layout.addWidget(frame)


class LayoutSettle(QtCore.QObject):
    def __init__(self,workspace):super().__init__(workspace);self.workspace=workspace;self.done=False
    def eventFilter(self,obj,event):
        if event.type()==QtCore.QEvent.Show and not self.done:
            self.done=True;QtCore.QTimer.singleShot(0,self.workspace._settle)
        return False
