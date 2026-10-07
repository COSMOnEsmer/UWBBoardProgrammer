"""Create revision 4 and new launch files without overwriting release 2.0.0."""
from pathlib import Path
import json

root=Path(__file__).resolve().parents[1];source=root/'app/revisions/v3';destination=root/'app/revisions/v4'
if destination.exists():raise FileExistsError(destination)
description='Flash one board at a time using the selected COM port. Other boards may stay disconnected. Wait for verification before swapping boards.'
thai='Flash ทีละบอร์ดผ่านพอร์ต COM ที่เลือกได้ โดยไม่ต้องต่อบอร์ดอื่น รอจนตรวจสอบเสร็จก่อนถอดเปลี่ยนบอร์ด'
for path in source.rglob('*.py'):
    relative=path.relative_to(source);text=path.read_text(encoding='utf8')
    # The application version changes; the firmware HELLO protocol stays 1.0.0.
    text=text.replace('2.0.0','2.0.1')
    if relative.name=='i18n.py':text=text.replace('th.v1.json','th.v2.json')
    if relative.name=='gui.py':
        start=text.index('    def flash_selected(self):');end=text.index('    def flash_all(self):',start)
        text=text[:start]+'''    def flash_selected(self):
        if self.controller:raise ValueError('Close COM ports before flashing')
        row=self.target.currentIndex();count=len(self.profile.anchors)
        if not 0<=row<=count:raise ValueError('Select a board to flash.')
        # Preparation is independent of positioning. Read only the selected
        # board's COM/revision and, for a Tag, its persistent radio settings.
        # No geometry, other port or other revision is needed for this operation.
        revision=self.revision(row)
        port=self.port_boxes[row].currentText().strip().split(' — ')[0].upper()
        if not port:raise ValueError('Select the COM port of the board to flash.')
        if not port.startswith('COM') or not port[3:].isdigit():raise ValueError('Choose a COM port')
        p=Profile.from_dict(self.profile.to_dict())
        if row==count:
            p.tag_port=port;p.tag_mac=self.tag_mac.text().strip().upper();p.blink_interval_ms=self.blink.value()
            try:valid=len(p.tag_mac)==16 and len(bytes.fromhex(p.tag_mac))==8
            except ValueError:valid=False
            if not valid:raise ValueError('Enter a valid tag MAC address.')
            if not 100<=p.blink_interval_ms<=10000:raise ValueError('BLINK interval 100..10000 ms')
        else:
            role=self.anchor_table.item(row,2).text().strip()
            if role not in ('master','slave'):raise ValueError('Invalid anchor role')
        available=self.available_images();flasher=Flasher(self.root,self.signals.log.emit)
        if row==count:self.job(lambda:flasher.setup_tag(available,port,revision,p))
        else:
            if role not in available:raise ValueError('Firmware bundle does not contain '+role)
            self.job(lambda:flasher.flash(available[role],port,revision,'Type2BP'))
''' +text[end:]
        text=text.replace('The app checks image hashes, verifies the flash, then reads the board identity over USB.',description)
        text=text.replace('USER_GUIDE_TH.v1.md','USER_GUIDE_TH.v2.md').replace('USER_GUIDE_EN.v1.md','USER_GUIDE_EN.v2.md')
    compile(text,str(relative),'exec');target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x',encoding='utf8',newline='\n') as f:f.write(text)
catalog=json.loads((root/'resources/i18n/th.v1.json').read_text(encoding='utf8'));catalog[description]=thai
catalog['VERSION 2.0.1\nFirmware validation pending']='เวอร์ชัน 2.0.1\nรอทดสอบเฟิร์มแวร์บนบอร์ดจริง'
catalog['Select a board to flash.']='เลือกบอร์ดที่จะ Flash'
catalog['Choose a COM port']='เลือกพอร์ต COM ที่ถูกต้อง'
catalog['Invalid anchor role']='หน้าที่ของ Anchor ต้องเป็น Master หรือ Slave'
with (root/'resources/i18n/th.v2.json').open('x',encoding='utf8') as f:json.dump(catalog,f,ensure_ascii=False,indent=2)

package=(root/'tools/package_desktop_v2.py').read_text(encoding='utf8').replace('desktop-v2','desktop-v3').replace('work-v2','work-v3').replace('spec-v2','spec-v3').replace('app/revisions/v3','app/revisions/v4')
with (root/'tools/package_desktop_v3.py').open('x',encoding='utf8',newline='\n') as f:f.write(package)
launch=(root/'Start_UWB_Board_Programmer.cmd').read_text(encoding='utf8').replace('desktop-v2','desktop-v3').replace('app\\revisions\\v3','app\\revisions\\v4').replace('BUILD_EN.v1.md','BUILD_EN.v2.md')
with (root/'Start_UWB_Board_Programmer_v3.cmd').open('x',encoding='utf8',newline='\n') as f:f.write(launch)
shortcuts=(root/'tools/create_shortcuts_v1.ps1').read_text(encoding='utf8').replace('desktop-v2','desktop-v3').replace('UWB Board Programmer.lnk','UWB Board Programmer 2.0.1.lnk')
with (root/'tools/create_shortcuts_v2.ps1').open('x',encoding='utf8',newline='\n') as f:f.write(shortcuts)

for language in ('EN','TH'):
    guide=(root/f'docs/USER_GUIDE_{language}.v1.md').read_text(encoding='utf8').replace('2.0.0','2.0.1').replace('Start_UWB_Board_Programmer.cmd','Start_UWB_Board_Programmer_v3.cmd')
    if language=='EN':
        paragraph='''### Flash with only one available USB port

Choose the physical board in the target selector, assign its COM port and EVK revision, then use **Flash selected board**. Leave the other port assignments blank and their revisions Unknown. Survey coordinates, orientation and workspace bounds are not required for single-board preparation. The selected board's revision and image integrity are still checked; Tag preparation also validates its MAC and BLINK interval.

Wait for programming, verification and the final HELLO check to finish. Disconnect that board, connect the next one, refresh ports, select the next target and repeat. You may reuse the same COM port for every board. If Windows assigns a different COM name to the next EVK, select that new name. Keep the Tag connected until both setup and battery images and retained settings have been verified.

**Flash all anchors** is the batch operation and requires distinct assigned ports. For live positioning, all three or four anchors must be connected and surveyed; sequential flashing does not remove the simultaneous acquisition requirement.

'''
        guide=guide.replace('## 3. Survey the anchors',paragraph+'## 3. Survey the anchors')
    else:
        paragraph='''### Flash เมื่อมีพอร์ต USB ว่างเพียงพอร์ตเดียว

เลือกบอร์ดในช่องเป้าหมาย กำหนด COM และ EVK Revision เฉพาะบอร์ดนั้น แล้วกด **Flash บอร์ดที่เลือก** ช่องพอร์ตของบอร์ดอื่นเว้นว่างและ Revision ยังไม่ทราบได้ ไม่ต้องกรอกพิกัด ทิศทาง หรือขอบเขตพื้นที่เพื่อเตรียมบอร์ดทีละตัว โปรแกรมยังตรวจ Revision และความสมบูรณ์ของไฟล์ ส่วน Tag ต้องมี MAC และช่วง BLINK ที่ถูกต้อง

รอจนการเขียน ตรวจ Flash และตรวจ HELLO เสร็จทั้งหมดก่อนถอด เปลี่ยนเป็นบอร์ดถัดไป ค้นหาพอร์ตใหม่ เลือกเป้าหมายใหม่ แล้วทำซ้ำ ใช้พอร์ต COM เดิมซ้ำได้ ถ้า Windows กำหนดชื่อ COM ใหม่ให้เลือกชื่อใหม่ อย่าถอด Tag จนติดตั้งทั้ง image ตั้งค่าและใช้ถ่าน พร้อมตรวจค่าที่บันทึกเสร็จแล้ว

**Flash Anchors ทุกตัว** เป็นคำสั่งแบบกลุ่มและต้องมีพอร์ตที่ไม่ซ้ำกัน ส่วนตอนวัดตำแหน่งจริงยังต้องเชื่อมต่อ Anchor ให้ครบสามหรือสี่ตัวพร้อมกันและมีพิกัดที่สำรวจแล้ว

'''
        guide=guide.replace('## 3. สำรวจตำแหน่ง Anchor',paragraph+'## 3. สำรวจตำแหน่ง Anchor')
    with (root/f'docs/USER_GUIDE_{language}.v2.md').open('x',encoding='utf8',newline='\n') as f:f.write(guide)
build=(root/'docs/BUILD_EN.v1.md').read_text(encoding='utf8').replace('app\\revisions\\v3','app\\revisions\\v4').replace('package_desktop_v2.py','package_desktop_v3.py').replace('Start_UWB_Board_Programmer.cmd','Start_UWB_Board_Programmer_v3.cmd').replace('2.0.0','2.0.1').replace('-m pytest --basetemp','-m pytest -c pytest.v4.ini --basetemp')
with (root/'docs/BUILD_EN.v2.md').open('x',encoding='utf8',newline='\n') as f:f.write(build)
readme=(root/'README.md').read_text(encoding='utf8').replace('app/revisions/v3','app/revisions/v4').replace('Start_UWB_Board_Programmer.cmd','Start_UWB_Board_Programmer_v3.cmd').replace('USER_GUIDE_EN.v1.md','USER_GUIDE_EN.v2.md').replace('USER_GUIDE_TH.v1.md','USER_GUIDE_TH.v2.md').replace('BUILD_EN.v1.md','BUILD_EN.v2.md')
readme=readme.replace('# UWB Board Programmer','# UWB Board Programmer 2.0.1',1).replace('**UWB Board Programmer** on the desktop','**UWB Board Programmer 2.0.1** on the desktop')
readme+='\nSingle-board flashing accepts only the selected board\'s COM port and revision. Other boards may be unplugged, and the same COM port may be reused after each completed operation. Surveying is required for live positioning, not for firmware preparation.\n'
with (root/'README.v2.md').open('x',encoding='utf8',newline='\n') as f:f.write(readme)
print(json.dumps({'source':'app/revisions/v4','application_version':'2.0.1','single_board':'selected COM and revision only','release':'desktop-v3','previous_files_preserved':True}))
