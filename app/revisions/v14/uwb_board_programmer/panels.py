"""Collapsible panels whose live widgets can move into resizable windows."""
from PySide6 import QtCore,QtWidgets as W

class Panel(W.QFrame):
    def __init__(self,title,owner):
        super().__init__();self.setObjectName('Card');self.title=title;self.owner=owner;self.dialog=None;self.collapsed=False
        layout=W.QVBoxLayout(self);layout.setContentsMargins(12,8,12,10)
        header=W.QHBoxLayout();layout.addLayout(header)
        label=W.QLabel(title);label.setObjectName('CardTitle');header.addWidget(label);header.addStretch()
        self.collapse=W.QPushButton('Collapse');self.collapse.clicked.connect(self.toggle);header.addWidget(self.collapse)
        self.detach=W.QPushButton('Detach');self.detach.clicked.connect(self.float_or_dock);header.addWidget(self.detach)
        self.placeholder=W.QLabel('Panel is open in a separate window. Click Attach to restore.');self.placeholder.setWordWrap(True);self.placeholder.hide();layout.addWidget(self.placeholder)
        self.body=W.QWidget();self.body_layout=W.QVBoxLayout(self.body);self.body_layout.setContentsMargins(6,5,6,6);self.body_layout.setSpacing(10);layout.addWidget(self.body)
    def toggle(self):
        self.collapsed=not self.collapsed;self.body.setVisible(not self.collapsed);self.collapse.setText('Expand' if self.collapsed else 'Collapse')
    def float_or_dock(self):
        if self.dialog:self.dialog.close();return
        panel=self
        class Floating(W.QDialog):
            def closeEvent(self,event):panel.restore();event.accept()
        dialog=Floating(self.owner);dialog.setAttribute(QtCore.Qt.WA_DeleteOnClose);dialog.setWindowTitle('UWB Board Programmer · '+self.title)
        dialog.setWindowFlags(dialog.windowFlags()|QtCore.Qt.WindowMinMaxButtonsHint)
        box=W.QVBoxLayout(dialog);tools=W.QHBoxLayout();tools.addStretch();attach=W.QPushButton('Attach');attach.clicked.connect(dialog.close);tools.addWidget(attach);box.addLayout(tools);box.addWidget(self.body);self.body.show();self.placeholder.show()
        self.collapse.setEnabled(False);self.detach.setText('Attach');self.dialog=dialog
        dialog.resize(max(560,min(self.width(),1200)),max(350,min(self.height()+80,900)));dialog.show()
    def restore(self):
        if not self.dialog:return
        self.dialog.layout().removeWidget(self.body);self.layout().addWidget(self.body);self.body.setVisible(not self.collapsed)
        self.placeholder.hide();self.detach.setText('Detach');self.collapse.setEnabled(True);self.dialog=None

def enable_free_layout(owner):
    """Native movable/resizable subwindows, independent of box-layout sizing."""
    owner.panel_workspaces=[]
    for index in range(owner.tabs.count()):
        scroll=owner.tabs.widget(index)
        page=scroll.widget() if isinstance(scroll,W.QScrollArea) else scroll
        panels=page.findChildren(Panel)
        if not panels:continue
        for panel in panels:
            parent=panel.parentWidget()
            if parent and parent.layout():parent.layout().removeWidget(panel)
            panel.setParent(None)
        layout=page.layout()
        actions=[]
        while layout.count():
            item=layout.takeAt(0)
            if isinstance(item.widget(),W.QPushButton):actions.append(item.widget())
            elif item.widget():item.widget().setParent(page);item.widget().hide()
        if actions:
            controls=Panel("Workspace actions",owner)
            for button in actions:controls.body_layout.addWidget(button);button.show()
            panels.append(controls)
        toolbar=W.QHBoxLayout();layout.addLayout(toolbar)
        area=W.QMdiArea();area.setMinimumHeight(620);area.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded);area.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        area.setBackground(owner.palette().window());layout.addWidget(area,1);owner.panel_workspaces.append(area)
        for title,action in [('Tile panels',area.tileSubWindows),('Cascade panels',area.cascadeSubWindows),('Show all panels',lambda a=area:[s.show() for s in a.subWindowList()])]:
            button=W.QPushButton(title);button.clicked.connect(lambda checked=False,fn=action:fn());toolbar.addWidget(button)
        toolbar.addStretch();hint=W.QLabel('Drag title bars to move; drag window edges to resize.');toolbar.addWidget(hint)
        width=max(700,owner.width()-310);column=max(360,width//2-15)
        y=[0,0]
        for n,panel in enumerate(panels):
            viewport=W.QScrollArea();viewport.setWidgetResizable(True);viewport.setWidget(panel)
            sub=area.addSubWindow(viewport);sub.setAttribute(QtCore.Qt.WA_DeleteOnClose,False);sub.setWindowTitle(panel.title)
            height=500 if panel.title=='Floor view' else min(520,max(230,panel.sizeHint().height()+55))
            side=0 if y[0]<=y[1] else 1
            sub.resize(column,height);sub.move(side*(column+10),y[side]);y[side]+=height+10
            if index==3:
                if panel.title=='Acquisition':sub.setGeometry(0,0,width,260)
                elif panel.title.startswith(('X  /','Y  /','Z  /')):
                    axis='XYZ'.index(panel.title[0]);sub.setGeometry(axis*(width//3),270,width//3-7,155)
                elif panel.title=='Floor view':sub.setGeometry(0,435,int(width*.6),500)
                elif panel.title=='Clock synchronization':sub.setGeometry(int(width*.6)+10,435,int(width*.4)-10,500)
            panel.show();sub.show()

    # One shared live log follows the active workspace and is also freely resizable.
    floating=[p for p in owner.findChildren(Panel) if not any(a.isAncestorOf(p) for a in owner.panel_workspaces)]
    if floating:
        log=floating[-1];parent=log.parentWidget()
        def remove(layout):
            if not layout:return
            layout.removeWidget(log)
            for i in range(layout.count()):
                nested=layout.itemAt(i).layout()
                if nested:remove(nested)
        remove(parent.layout());viewport=W.QScrollArea();viewport.setWidgetResizable(True);viewport.setWidget(log)
        state={'area':None,'sub':None}
        def follow(index):
            if state['area'] is not None:
                state['area'].removeSubWindow(viewport);state['sub'].hide();state['sub'].deleteLater()
            area=owner.panel_workspaces[index];sub=area.addSubWindow(viewport)
            sub.setAttribute(QtCore.Qt.WA_DeleteOnClose,False);sub.setWindowTitle(log.title);sub.setGeometry(0,950,800,200)
            state.update(area=area,sub=sub);log.show();viewport.show();sub.show()
        owner.tabs.currentChanged.connect(follow);follow(owner.tabs.currentIndex())

def wrap_remaining_cards(owner):
    """Include metric, calibration and activity-log cards created outside card()."""
    def locate(layout,widget):
        if layout is None:return None
        if layout.indexOf(widget)>=0:return layout
        for i in range(layout.count()):
            nested=layout.itemAt(i).layout()
            found=locate(nested,widget) if nested else None
            if found is not None:return found
        return None
    for frame in list(owner.findChildren(W.QFrame)):
        if isinstance(frame,Panel) or frame.objectName()!='Card':continue
        container=locate(frame.parentWidget().layout(),frame)
        if container is None:continue
        labels=frame.findChildren(W.QLabel)
        title=next((label.property('i18n_text_source') or label.text() for label in labels if label.objectName() in ('CardTitle','MetricLabel')),'Panel')
        panel=Panel(title,owner);container.replaceWidget(frame,panel);frame.setObjectName('PanelContent');panel.body_layout.addWidget(frame)
