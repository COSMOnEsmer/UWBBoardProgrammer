# คู่มือ Standalone BLE Preview — รุ่น 3

ปรับปรุง 28 ตุลาคม 2026 ใช้ firmware **1.3.4-pilot** และ GUI
`standalone_bench_gui_v8.py` แยกจากโปรแกรม 2.0.1 เดิม ทุก revision และ backup
ยังเก็บไว้ ไม่มีการแก้ vendor originals หรือ RTLSSimulator

## เปิดโปรแกรม

Double-click shortcut **UWB Board Programmer - BLE Preview** บน Desktop
หรือ `Start_Standalone_BLE_Bench_Preview_v5.cmd` ในโฟลเดอร์โครงการ
เลือก English/ไทย ได้ โปรแกรมเริ่มโดยยังไม่เปิด COM, BLE หรือ RTLS เอง

Shortcut **UWB Board Programmer 2.0.1** เป็นโปรแกรมรุ่นเดิมและใช้ firmware
bundle คนละชุดกับ BLE Preview ให้ใช้ shortcut ที่มีคำว่า **BLE Preview**
สำหรับการทดลอง Standalone รอบนี้

## ผลที่ทดสอบกับบอร์ดจริงแล้ว

| การทดสอบ | ผล |
| --- | --- |
| Backup Tag/Anchor | อ่าน host FLASH สองชุด ขนาดและ SHA-256 ตรงกัน |
| Tag setup 1.3.4 | Program/Verify, provisioned MAC/CRC และ UWB running ผ่าน |
| Tag BLINK → Anchor | USB รับ 60 ชุดใน 60 วินาที สถานะสำเร็จทั้งหมด |
| อัตรา BLINK จาก RF timestamps | ช่วง 0.9948–1.0018 s; median 0.9988 s ในรอบ 60 ชุด |
| BLE → PC | 342 fragments รวมเป็น 57 records สมบูรณ์ |
| เทียบ BLE กับ USB | จับคู่ครบ 57 records; timestamps และ protocol fields ตรงกันทั้งหมด มุมตรงภายในความละเอียดข้อความ UART |
| Tag battery | ใช้ปุ่ม Flash backend จริง: backup สองชุด, Program/Verify และ configuration ACK ผ่าน |
| หลัง Tag แจ้ง battery_sleep | UART Tag เงียบ 45 s; Anchor ยังรับ BLINK 65 ชุดใน 65 s |
| GUI กับ Tag battery | รับจริง 41 ชุด, แสดง Tag age, ตัด BLE และปิดเรียบร้อย; ไม่มี cloud publishing |
| Software regression | 84 tests ผ่าน รวม solver, transport, GUI, single-board Flash และ localhost RTLS |

ตัวเลขเป็นผล bench แบบหนึ่ง Anchor กับหนึ่ง Tag บนไฟ USB ยังไม่ใช่ผลวัด
ความแม่นยำ 3D หรืออายุถ่าน การเงียบของ UART หลัง `battery_sleep` และ BLINK
ที่ต่อเนื่องยังต้องเสริมด้วยการวัดกระแสและทดลอง CR2032 จริง

## Flash ทีละบอร์ด

1. ปิดการรับ BLE ใน Preview ก่อนเริ่ม Flash
2. เสียบ EVK ที่ต้องการ Flash เพียงตัวเดียวก็ได้ เปิดแหล่งจ่ายที่ USB ตามคู่มือ
3. กด **Flash one board** แล้วเลือก firmware/model/role และ COM port เอง
4. ตรวจป้ายบอร์ด A1–A4 ให้ตรงกับ image อย่าใช้ slot เดียวกันกับสองบอร์ด
5. รออ่าน backup สองชุด ตรวจ SHA-256, Program/Verify และ configuration ACK
6. ดู report แยกผล Flash/ACK ออกจากผลรับ RF จริง การ Flash ผ่านอย่างเดียวไม่ยืนยัน RF
7. เมื่อเสร็จแล้ว ถอดและเสียบบอร์ดถัดไป ใช้ USB port เดิมซ้ำได้

| Image | บอร์ด/บทบาท | UWB MAC |
| --- | --- | --- |
| master | Type2BP / A1 Master | 0200000000000001 |
| slave2 | Type2BP / A2 Slave | 0200000000000002 |
| slave3 | Type2BP / A3 Slave | 0200000000000003 |
| slave4 | Type2BP / A4 Slave | 0200000000000004 |
| tag_setup | Type2DK / MCU awake | 0200000000000101 |
| tag_battery | Type2DK / MCU sleep candidate | 0200000000000101 |

หน้า Flash เลือกเฉพาะ bundle แบบ pilot ที่มีครบหก images และตรง model/slot/role
ไม่ใช้ชุด diagnostic หรือชุด build บางส่วนแทนเมนูหลักโดยอัตโนมัติ
ระบบตรวจ USB identity ก่อน backup และก่อน program ไม่ยึด COM number เพียงอย่างเดียว

Firmware ผูก identity กับ image แล้วตรวจ config record `0xE2E3`/CRC ก่อนเริ่ม UWB
ไม่เขียน record ซ้ำทุก heartbeat และไม่ใช้คำสั่ง UART CONFIG เปลี่ยน slot ระหว่างรัน
Tag setup และ battery ใช้ identity เดียวกัน ให้เลือกอย่างใดอย่างหนึ่งสำหรับ Tag ตัวนี้

## ใช้งาน Standalone

- Anchor ทั้งสี่รับไฟ USB 5 V จาก Power Banks แล้วเริ่ม UWB เอง
- A1 ส่ง UWB SYNC; A2–A4 รับ SYNC และ BLINK พร้อมส่ง measurements ผ่าน BLE
- Tag ใช้ battery image แล้วเปลี่ยนไปใช้ CR2032 ตามขั้นตอนแหล่งจ่ายของ EVK
- Laptop รับ BLE/GATT จาก Anchors จึงไม่ต้องใช้ USB data กับ Anchors ใน deployment
- Tag ไม่ต้องเชื่อม Laptop และไม่มีการส่งข้อมูล Tag ผ่าน BLE ไปยัง PC ในระบบนี้
- Disconnect BLE หรือปิด Preview ไม่ส่ง STOP ให้ radio

Master ยังจำเป็น เพราะการใช้ไฟจาก Power Bank ไม่ทำให้นาฬิกา UWB ตรงกัน
PC ใช้ RF timestamps และระยะ Master–Slave ชดเชย offset/drift; เวลาที่ BLE มาถึง
ใช้ตรวจ freshness และ timeout เท่านั้น

Tag เวอร์ชันนี้ตั้งทั้ง RANGING_INTERVAL และ UL_TDOA_TX_INTERVAL เป็น 1000 ms
Anchor ใช้คิวส่ง BLE แบบมี pacing, เก็บ fragment เดิมเมื่อ stack ยังไม่พร้อม
และทิ้ง record ที่ค้างเกิน 500 ms การทดสอบอัตราที่สูงกว่านี้ต้องวัด throughput ใหม่

## จาก Capture ไปคำนวณ 3D

เริ่มด้วย **Connect BLE** ในโหมด capture เพื่อเช็ก identity, RF frames และ Tag age
ก่อน ยังไม่ต้องมีพิกัดครบและไม่คำนวณตำแหน่งจากบอร์ดเพียงตัวเดียว

ก่อนเลือก **Calculate 3D with four anchors** ต้องโหลด profile ที่สำรวจจริง:
Anchor IDs/MAC/roles, X/Y/Z หน่วยเมตร, RX bias, ขอบเขตพื้นที่, site/floor และ Tag ID
ให้จัดอย่างน้อยหนึ่ง Anchor ต่างระดับจน geometry ไม่อยู่ในระนาบเดียวกัน
โปรแกรมไม่ทราบพิกัดหรือทิศการติดตั้งเองจาก USB/BLE

Pure four-anchor TDoA ไม่ใช้ yaw/pitch/roll หรือ AoA ช่วยแก้ความสูง แต่ยังต้องตรวจ
geometry, calibration และ uncertainty จริง โปรแกรมรวม shared-master covariance
และปฏิเสธข้อมูล stale, clocks ไม่พร้อม, physical-baseline ผิด หรือคำตอบกำกวม
ยังต้องประเมิน clock prediction uncertainty และทดสอบหลายความสูงเทียบ ground truth

## เชื่อม RTLS Platform

ใช้ Edge Socket.IO connector ใส่ **hardware Gateway ID** และ **gateway bearer token**
บน Preview; ไม่ใช่รหัสผ่าน dashboard และโปรแกรมไม่บันทึก token ลง repository
ก่อนส่งต้องให้ site/floor, Anchor IDs/roles และพิกัดตรงกับข้อมูล gateway บน server

ส่งเฉพาะ fresh accepted fixes จาก RF จริง หลัง BLE หลุดไม่ส่ง backlog เก่าเข้าแผนที่
การทดสอบ localhost ที่ผ่านแล้วไม่ใช่การยืนยัน production RTLS ครั้งนี้ยังไม่ส่ง
ตำแหน่งจริงขึ้นแผนที่ เพราะยังต้องทดสอบ clock กับหลาย Anchors และพิกัดสำรวจ

## Backup และการกู้คืน

Reports/backups อยู่ใน `verification/` และ recordings อยู่ใน `data/sessions/`
สร้างไฟล์ใหม่ทุกครั้งและไม่ Push ข้อมูลเฉพาะบอร์ดขึ้น GitHub
ใช้ `tools/restore_host_backup_v1.py` กับ manifest ของ USB device เดียวกันเท่านั้น

Backup ครอบคลุม host FLASH `[0,0x9DC00)` ไม่รวม protected tail, radio NVM หรือ OTP/EFUSE
SDK ของ SR040 มีขั้นจัดการ persisted ranging sessions ใน radio NVM แยกต่างหาก
การ restore host backup จึงไม่ใช่การคืน radio NVM ทุก byte กลับโรงงาน

ขั้นต่อไป: เพิ่ม Type2BP อีกหนึ่งตัวเพื่อพิสูจน์ Master TX / Slave RX และ clock fit
แล้วขยายครบสี่ตัว ก่อนทำ 3D, Power Bank/CR2032 และ production RTLS ตาม
`plans/Standalone_TDoA_BLE_Plan.v4.th.md`
