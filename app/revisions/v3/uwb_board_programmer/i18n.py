"""Translate presentation text without translating protocol values or user data."""
import json, re
from pathlib import Path
from PySide6 import QtWidgets as W
from .models import save_new

class Translator:
    def __init__(self, root):
        self.root=Path(root)
        self.th=json.loads((self.root/'resources/i18n/th.v1.json').read_text(encoding='utf8'))
    def settings(self):
        result=[]
        for file in (self.root/'data/ui-settings').glob('language-*.json'):
            try:
                data=json.loads(file.read_text(encoding='utf8'))
                if data.get('language') in ('en','th'):result.append((int(data.get('sequence',0)),file.stat().st_mtime_ns,data['language']))
            except (ValueError,KeyError,OSError,TypeError):pass
        return result
    def load_language(self):
        settings=self.settings()
        return max(settings,key=lambda row:row[:2])[2] if settings else 'en'
    def save_language(self, language):
        if language not in ('en','th'):raise ValueError('Unknown UI language')
        # Windows clocks can produce identical UTC stamps in rapid toggles.
        # Append a sequence to each NEW file instead of replacing a settings file.
        sequence=max((row[0] for row in self.settings()),default=0)+1
        return save_new(self.root/'data/ui-settings','language',{'language':language,'sequence':sequence})
    def translate(self, text, language):
        text=str(text)
        if language!='th':return text
        if text in self.th:return self.th[text]
        if text.startswith('ERROR: '):return 'ข้อผิดพลาด: '+self.translate(text[7:],language)
        patterns=[
            (r'(\d+) x Type2BP anchors\n1 x Type2DK tag',r'Anchor Type2BP \1 ตัว\nTag Type2DK 1 ตัว'),
            (r'(\d+) serial ports found\. Board model/revision must be identified physically\.',r'พบพอร์ตอนุกรม \1 พอร์ต ต้องตรวจรุ่นและ Revision ที่บอร์ดจริง'),
            (r'(\d+) verified-build manifests found',r'พบชุดเฟิร์มแวร์ที่ตรวจสอบแล้ว \1 ชุด'),
            (r'Enter the surveyed coordinates for (.+)',r'กรอกพิกัดที่สำรวจจริงของ \1'),
            (r'The selected mode requires (\d+) anchors with exactly one master\.',r'โหมดที่เลือกต้องใช้ Anchor \1 ตัว โดยมี Master 1 ตัว'),
            (r'(\d+) references for (.+)',r'จุดอ้างอิง \1 จุดสำหรับ \2'),
            (r'(\d+) imported references',r'นำเข้าจุดอ้างอิง \1 จุด'),
            (r'(.+) • (\d+) Anchors • horizontal 95% (.+) m • Z 95% ±(.+) m • residual (.+) m',r'\1 • \2 Anchors • แนวราบ 95% \3 m • Z 95% ±\4 m • Residual \5 m'),
            (r'RTLS connected=(.+) \| config verified=(.+) \| ACK OK=(.+) \| errors=(.+) \| dropped=(.+)',r'RTLS เชื่อมต่อ=\1 | ยืนยันการตั้งค่า=\2 | ACK สำเร็จ=\3 | ผิดพลาด=\4 | ตกหล่น=\5'),
        ]
        for pattern, replacement in patterns:
            if re.fullmatch(pattern,text):return re.sub(pattern,replacement,text)
        prefixes={
            'Saved new profile ':'บันทึกโปรไฟล์ใหม่ ',
            'Loaded profile without editing source ':'โหลดโปรไฟล์แล้ว ',
            'RTLS surveyed anchor setup ':'ไฟล์พิกัด Anchor สำหรับ RTLS ',
            'Saved user-scoped DPAPI credential ':'บันทึกข้อมูลเข้าระบบแบบ DPAPI สำหรับผู้ใช้นี้ ',
            'Credential could not be loaded: ':'โหลดข้อมูลเข้าระบบไม่ได้: ',
            'Reference captured ':'บันทึกจุดอ้างอิงแล้ว ',
            'RTLS token/site/floor/anchor coordinates verified: ':'ตรวจสอบ Token, Site, Floor และพิกัด Anchor แล้ว: ',
            'Offline replay ':'เล่นย้อนหลัง ',
            'Firmware bundle does not contain ':'ชุดเฟิร์มแวร์ไม่มี ',
            'Missing firmware ':'ไม่พบเฟิร์มแวร์ ',
        }
        for prefix, replacement in prefixes.items():
            if text.startswith(prefix):return replacement+text[len(prefix):]
        if text.startswith(('LIVE | ','DIAGNOSTIC — no position publishing | ')):
            return text.replace('DIAGNOSTIC — no position publishing | ','ตรวจสอบ — ไม่ส่งตำแหน่ง | ').replace('LIVE | ','รับข้อมูลสด | ').replace('\nClock ','\nนาฬิกา ').replace(' | fixes ',' | ตำแหน่ง ').replace(' | rejected ',' | ปฏิเสธ ')
        return text

def _localized(obj,key,current,setter,translate):
    # A widget may receive a new English status from acquisition after a toggle.
    source=obj.property(key+'_source');last=obj.property(key+'_last')
    if source is None or (current!=last and current!=source):source=current;obj.setProperty(key+'_source',source)
    value=translate(source);setter(value);obj.setProperty(key+'_last',value)

def localize_widgets(window, translate):
    for widget in window.findChildren(W.QWidget):
        if isinstance(widget,(W.QLabel,W.QPushButton,W.QCheckBox)):
            _localized(widget,'i18n_text',widget.text(),widget.setText,translate)
        elif isinstance(widget,W.QLineEdit):
            _localized(widget,'i18n_placeholder',widget.placeholderText(),widget.setPlaceholderText,translate)
        elif isinstance(widget,W.QComboBox):
            # Technical roles, paths, firmware bundle IDs and COM ports are
            # unchanged because only catalogued labels have translations.
            for i in range(widget.count()):
                role=0x1000;source=widget.itemData(i,role)
                if source is None:source=widget.itemText(i);widget.setItemData(i,source,role)
                widget.setItemText(i,translate(source))
            _localized(widget,'i18n_placeholder',widget.placeholderText(),widget.setPlaceholderText,translate)
        elif isinstance(widget,W.QListWidget):
            for i in range(widget.count()):
                item=widget.item(i);source=item.data(0x1000)
                if source is None:source=item.text();item.setData(0x1000,source)
                item.setText(translate(source))
        elif isinstance(widget,W.QTableWidget):
            for i in range(widget.columnCount()):
                item=widget.horizontalHeaderItem(i)
                if item is None:continue
                source=item.data(0x1000)
                if source is None:source=item.text();item.setData(0x1000,source)
                item.setText(translate(source))
            if widget is getattr(window,'device_table',None):
                for row in range(widget.rowCount()):
                    for col in (0,3):
                        item=widget.item(row,col)
                        if item is None:continue
                        source=item.data(0x1000)
                        if source is None:source=item.text();item.setData(0x1000,source)
                        item.setText(translate(source))
