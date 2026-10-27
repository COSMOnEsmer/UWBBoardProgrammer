# UWB Board Programmer — Standalone BLE Preview

คู่มือรุ่นทดลอง พัฒนาต่อโดยเก็บโปรแกรม 2.0.1, RTLSSimulator, SDK และไฟล์ต้นฉบับไว้ทั้งหมด
ไฟล์ทดลองไม่ใช่ release ที่ผ่านการวัด 3D หรือการทดสอบ CR2032 แล้ว

## เปิดหน้าจอใหม่

Double-click `Start_Standalone_BLE_Bench_Preview_v4.cmd` ในโฟลเดอร์โปรแกรม
เลือก English/ไทย มุมขวาบน โปรแกรมไม่เปิด USB, BLE หรือ RTLS เองเมื่อเริ่มต้น
Shortcut และ EXE 2.0.1 เดิมยังเป็นโปรแกรมเดิม ส่วนหน้าจอใหม่นี้ใช้ชื่อ BLE Pilot ชัดเจน

หน้าจอใหม่ทำได้:

- ระบุ Anchor ID, UWB MAC และ Master/Slave ของ A1–A4
- เชื่อม BLE ด้วย scanner ร่วมตัวเดียวและแยกการเชื่อมต่อแต่ละ Anchor
- ตรวจ Device Info และรับ binary measurements พร้อมตรวจ boot, sequence, CRC และความสด
- บันทึก raw BLE, ข้อมูลที่ถอดรหัส, การ reset clock, fixes และข้อผิดพลาดใน session ใหม่
- โหลดโปรไฟล์สำรวจแบบ 4 Anchors แล้วคำนวณ 3D TDoA บน PC
- เชื่อม RTLS ด้วย hardware gateway ID/token และส่งเฉพาะ accepted fresh fixes
- ตัด BLE หรือปิดหน้าจอโดยไม่ส่ง STOP ไปยัง UWB radio

ปุ่ม Flash ทีละบอร์ดในหน้าจอใหม่รองรับ A1 Master, A2–A4 Slaves, Tag setup และ Tag battery
ต้องเลือก firmware/model/role และ USB port เองทุกครั้ง ไม่เลือกคู่เริ่มต้นให้โดยอัตโนมัติ
ใช้บอร์ดที่เลือกเพียงตัวเดียว ไม่ต้องกรอกพิกัดหรือเสียบบอร์ดอื่นครบ ระบบตรวจ USB identity,
อ่าน host FLASH สองชุดให้ SHA-256 ตรงกัน แล้ว Program/Verify และอ่าน HELLO/config CRC
พอร์ตเดียวกันนำกลับมาใช้ Flash บอร์ดถัดไปได้หลังขั้นตอนเดิมเสร็จ

Firmware 1.3.1-pilot ผูก MAC กับ image ที่เลือก บันทึก record 0xE2E3 พร้อม role/CRC และ
ตรวจอ่านกลับก่อนเริ่ม UWB ไม่เขียนซ้ำทุก heartbeat ติดป้าย A1–A4 ให้บอร์ดจริง และเลือก
slot ละหนึ่งบอร์ด อย่าใช้ preset เดียวกันกับสองบอร์ดที่จะเปิดพร้อมกัน

| Image label | บทบาท | UWB MAC |
| --- | --- | --- |
| master | A1 Master | 0200000000000001 |
| slave2 | A2 Slave | 0200000000000002 |
| slave3 | A3 Slave | 0200000000000003 |
| slave4 | A4 Slave | 0200000000000004 |
| tag_setup | Tag / MCU awake | 0200000000000101 |
| tag_battery | Tag / sleep candidate | 0200000000000101 |

Tag เริ่มต้น BLINK 1 Hz; setup image เก็บ MCU ไว้รับ diagnostics ส่วน battery image
มี USB diagnostic window ก่อนพัก MCU ยังต้องพิสูจน์ BLINK บน CR2032 และวัดกระแสจริง
โปรแกรม 2.0.1 ใช้ firmware bundle เดิม ส่วน BLE Preview ใช้ชุดทดลองที่แยกไว้

## ลำดับทดลอง

1. ปิดโปรแกรมที่อาจถือ COM port ก่อนทำ readback หรือ Flash
2. ตรวจรุ่น EVK และ USB identity ของบอร์ดที่เลือก สำรอง host FLASH สองครั้งให้ SHA-256 ตรงกัน
3. ทดสอบ pilot บน Master ตัวเดียวก่อน: boot, UWB initialization, BLE identity และ GATT
4. เริ่มในโหมด capture โดยยังไม่เลือกคำนวณ 3D ตรวจว่ามี BLINK จาก Tag จริงและ SYNC จาก Master
5. เพิ่ม Slave ทีละตัว ทำ provisioning ให้ MAC ไม่ซ้ำ แล้วพิสูจน์ Master TX / Slave RX และ clock fit
6. เชื่อมครบ 4 Anchors ผ่าน BLE พร้อมกัน ทดสอบ disconnect/reconnect และ power cycle
7. โหลดพิกัดสำรวจ เลือกคำนวณ 3D แล้ววัดหลายจุดและหลายระดับความสูงเทียบ ground truth
8. ต่อ RTLS หลังยืนยัน gateway scope/ID/พิกัดและได้ valid fixes จาก RF จริง
9. ทดสอบ Power Bank และ CR2032 จริง รวมถึง current measurement และ soak test

ยังต้องผ่านขั้นตอนเหล่านี้ตามแผนก่อนจัดทำ EXE release ใหม่ ไม่มีการส่งตำแหน่งจำลองไปใช้แทน
การพิสูจน์ระบบจริง

## พิกัดและ Clock

พิกัด Anchor ไม่ได้ทราบเองจาก USB หรือ BLE ต้องสำรวจ X/Y/Z เป็นเมตรในกรอบพิกัดเดียวกับ
แผนที่ RTLS และบันทึกในโปรไฟล์ ต้องจัด 4 จุดให้ไม่อยู่ในระนาบเดียวกัน โปรแกรมตรวจ rank
ของ geometry ก่อนคำนวณ โหมด pure four-anchor TDoA ไม่ใช้ AoA และไม่ใช้ yaw/pitch/roll
เป็นข้อมูลช่วยหาความสูง

Master ยังจำเป็นแม้ทำงาน Standalone เพราะต้องส่ง UWB SYNC ให้ Slaves เรียนรู้ offset/drift
PC ใช้ RF timestamps และระยะ Master–Slave ชดเชยนาฬิกา เวลาที่ BLE packet มาถึง PC
ใช้ตรวจความสดเท่านั้น ไม่ใช้แทนเวลาคลื่น UWB มาถึง Anchor

ตัวคำนวณ pilot รวมความสัมพันธ์ของความคลาดเคลื่อน Master ที่ใช้ร่วมกันในทุก TDoA แล้ว
ยังต้องประเมิน clock prediction error, calibration bias และความแม่นยำจากการวัดจริง
4 Anchors มีเพียง 3 TDoA อิสระ จึงต้องตรวจสองคำตอบที่เป็นไปได้และ uncertainty ด้วย

## RTLS Platform

ใช้ Edge Socket.IO connector ของโครงการ ไม่มี Wi-Fi/MQTT อยู่ใน Type2BP firmware นี้
บนหน้าจอให้ใส่ hardware Gateway ID และ bearer token ของ gateway ไม่ใช่รหัสผ่าน dashboard
โปรแกรมไม่บันทึก token ที่กรอกลงไฟล์หรือ repository

ก่อนส่ง โปรแกรมตรวจ site/floor, Anchor IDs, roles และพิกัดที่ server ให้มาตรงกับโปรไฟล์
รวมถึงความสดและผลรับรอง fix จากตัวคำนวณ ถ้าเชื่อมต่อขาดจะทิ้งข้อมูลเก่าและไม่ backfill
ตำแหน่งที่ค้างไปยังแผนที่ การทดสอบ Socket.IO บน localhost ไม่ใช่การยืนยัน production RTLS

## ไฟล์และการกู้คืน

- Source รุ่นทดลอง: `app/ble_prototype/v1/`
- Firmware source แต่ละ revision: `firmware/source/v*-pilot/`
- Binary ทดลอง: `firmware/releases/_experimental/` แยกจาก bundle ที่ 2.0.1 เลือกใช้
- Readback/logs/report: `verification/` เก็บในเครื่องและไม่ Push
- Sessions: `data/sessions/` เก็บใหม่ทุกครั้งและไม่เขียนทับ session เดิม
- Readback helper: `tools/backup_host_flash_v1.py`
- Restore helper: `tools/restore_host_backup_v1.py`

Backup มีขอบเขต host FLASH [0, 0x9DC00) เท่านั้น ไม่ใช่ snapshot ของ protected tail,
SR150/SR040 radio NVM หรือ OTP/EFUSE ทั้งหมด Restore helper ตรวจสองสำเนาและ USB identity
ก่อนเขียน และไม่เขียน protected tail ห้ามนำ backup ของอีกบอร์ดมาใช้

## สิ่งที่ต้องมีสำหรับขั้นถัดไป

- Tag ที่ติดต่อ MCU/bootloader ได้ เพื่อสำรองก่อน Flash และพิสูจน์ BLINK
- Master + Slave อย่างน้อยสองตัวสำหรับทดสอบ clock จริง และครบสี่ตัวสำหรับ 3D
- พิกัดสำรวจที่วัดจริง, Power Banks/ถ่าน และ gateway สำหรับ hardware deployment

รายละเอียด tasks และเกณฑ์ผ่านอยู่ใน `plans/Standalone_TDoA_BLE_Plan.v3.th.md`
และรายละเอียด wire format อยู่ใน `docs/BLE_PILOT_PROTOCOL.v3.md`
