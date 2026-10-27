# แผน Standalone TDoA / BLE — รุ่น 4

สถานะ 28 ตุลาคม 2026 หลังทดสอบบอร์ดจริงหนึ่ง Anchor และหนึ่ง Tag
พัฒนาต่อในไฟล์ใหม่ทั้งหมด โปรแกรม 2.0.1, RTLSSimulator และ vendor originals คงเดิม

## ระบบเป้าหมาย

Type2DK บน CR2032 ส่ง UWB BLINK → Type2BP สี่ตัวบน Power Banks
โดย A1 เป็น Sync Master และ A2–A4 เป็น Slaves → BLE/GATT สี่ลิงก์ →
PC ชดเชยนาฬิกาและคำนวณ 3D TDoA → Edge Socket.IO → RTLS Platform

Flash/commission ทีละบอร์ดผ่าน USB ได้ หลังติดตั้งจึงใช้ BLE รับ measurements
Tag และ Anchors auto-start เอง ไม่ต้องใช้ PC ส่งคำสั่ง START ทุกครั้งที่เปิดไฟ
Master ยังจำเป็นเพื่อสร้าง time reference ของ UWB

## ผลปัจจุบันและเกณฑ์ที่เหลือ

| Task | สถานะ | ผล/เกณฑ์ที่เหลือ |
| --- | --- | --- |
| T00 Audit/backup/recovery | ผ่านสำหรับคู่ที่ต่อ | Host FLASH สองสำเนาตรงกันทั้ง Anchor/Tag; radio NVM และ protected tail อยู่นอก snapshot |
| T01 PC BLE | ผ่าน single-link | PC รองรับ central และใช้ GATT กับ Anchor จริงได้ |
| T02 USB RF baseline | ผ่าน | Tag 1.3.4 auto-start; Anchor รับ BLINK 60 ชุด/60 s, status 0; ประมาณ 1 Hz จาก RF timestamps |
| T03 Anchor auto-start | ผ่าน bench A1 | boot แล้ว UWB/BLE running และรับ BLINK โดยไม่ส่ง START; Power Bank/cold boot ยังต้องทดสอบ |
| T04 GATT/wire proof | ผ่าน single-link | 57 records/342 fragments; เปรียบเทียบกับ USB จับคู่ครบ 57, ไม่พบ field mismatch; ต้องทดสอบโหลดสี่ลิงก์ |
| T05 Single-board commissioning | ผ่าน A1/Tag | USB identity + backup สองชุด + Program/Verify + config CRC ACK; A2–A4 images พร้อม แต่ยังไม่ Flash บอร์ดจริง |
| T06 PC preview | ผ่าน bench | Native GUI รับจริง 41 ชุดแล้วปิดสะอาด; 84 software tests ผ่าน; ยังต้องประเมิน clock prediction uncertainty กับข้อมูลหลายบอร์ด |
| T07 Master + Slave | รอเพิ่ม Anchor | พิสูจน์ SYNC ที่มี TX timestamp 64-bit, Slave RX, offset/drift, freshness และ reset recovery |
| T08 Four BLE links | รอครบสี่บอร์ด | สี่ลิงก์พร้อมกัน, clocks สาม Slaves พร้อม, BLINK จับคู่ครบ; reconnect/overload ไม่เกิด false fixes |
| T09 3D validation | รอพิกัดและ RF ครบ | Survey X/Y/Z จริงแบบ non-coplanar; ทดสอบจุด/ความสูงที่ทราบจริง วัด median/P95, availability และ uncertainty coverage |
| T10 Power acceptance | ผ่านบางส่วน | Battery firmware แจ้ง sleep, Tag UART เงียบ 45 s แต่ Anchor รับต่อ 65 ชุด/65 s บน USB; ยังต้อง CR2032/Power Banks/current/brownout/soak |
| T11 Production RTLS | ยังไม่ผ่าน | Gateway/site/floor/Anchor IDs/พิกัดตรงกัน, accepted real fixes และ server ACK/dashboard |
| T12 Package/docs/source | Preview พร้อม | Shortcut/launcher TH/EN, คู่มือรุ่นใหม่และ source; EXE release ใหม่หลัง hardware acceptance |

## ลำดับปฏิบัติต่อ

1. คง A1 และ Tag ที่ทดสอบไว้ เพิ่ม Type2BP อีกตัวทาง USB แล้วระบุว่าเป็น A2
2. เก็บ USB identity และ backup สองชุด Flash `slave2`, ตรวจ MAC `...0002` และ role slave
3. ให้ A1/A2/Tag เปิดพร้อมกัน รับ BLE จากสอง Anchors และบันทึก RF จริง
4. วัดระยะ A1–A2 ใช้แก้ propagation delay ของ SYNC ตรวจ drift/RMS/clock freshness
5. เก็บข้อมูลก่อน/หลัง reboot, BLE disconnect และกลับมาเชื่อมใหม่ ทดสอบ no-fix ขณะ clock ไม่พร้อม
6. ทำเช่นเดียวกันกับ A3/A4 โดยเลือก `slave3`/`slave4` เฉพาะบอร์ดนั้น ใช้ USB port เดิมซ้ำได้
7. ย้าย Anchor ที่ Flash เสร็จไป Power Bank แล้วทดสอบ BLE พร้อมกันครบสี่ตัว
8. Survey พิกัดอ้างอิงแผนที่ RTLS ให้ครบ ทำ profile ใหม่ ไม่ใส่พิกัดสมมติแทนข้อมูลสำรวจ
9. พิสูจน์ 3D ที่ ground truth หลายจุด/ความสูง ตรวจทั้งความผิดพลาดและช่วงที่ระบบปฏิเสธ fix
10. เตรียม hardware gateway สำหรับ site/floor ที่ใช้จริง ตรวจ scope และเปิดส่ง production หลังมี valid RF fixes
11. ทดลอง CR2032 จริง วัดกระแสเฉลี่ย/พีกและพฤติกรรม Power Bank auto-off; ทำ soak test
12. จัด EXE release/shortcut รุ่นใหม่พร้อม acceptance report และคู่มือที่ตรงกับผลจริง

## การแก้ที่ได้จาก bench รอบนี้

- Tag ใช้ FreeRTOS heap 60 KB รองรับ stack ของงาน UWB ที่เพิ่มขึ้น แทน 30 KB เดิม
- Malloc-failure diagnostics ต้อง patch handler ที่ SDK link จริงใน OSAbstraction ด้วย
- ตั้ง UL_TDOA_TX_INTERVAL แยกจาก RANGING_INTERVAL เป็น 1000 ms ให้ตรงอัตราเป้าหมาย
- ส่ง BLE ทีละ fragment ตามรอบ scheduler 20 ms เก็บ fragment เดิมเมื่อ stack ยังไม่พร้อม
- จำกัด queue และอายุ record 500 ms ไม่ปล่อยข้อมูลค้างเก่ามาแสดงเป็นข้อมูลสด
- เลือก firmware bundle ที่ครบหก images และตรง model/slot/role; ข้าม partial/diagnostic builds

## ข้อกำหนดตัวคำนวณและ RTLS

ใช้ RF RX/TX timestamps เดิมเป็น integer แล้วหาผลต่างก่อนแปลงหน่วย ห้ามใช้ BLE arrival
time แทน RF time จับคู่ BLINK ด้วย corrected RF time/physical gate ไม่อาศัย frame number
อย่างเดียว clocks ต้องสดและรับ SYNC ครบก่อนคำนวณ

Four-anchor TDoA มีสามสมการอิสระและอาจมีสองคำตอบเชิงเรขาคณิต จึงต้องรักษา geometry,
ambiguity และ uncertainty gates ค่า shared-master covariance มีแล้ว ส่วน prediction
uncertainty จาก clock regression และพฤติกรรม oscillator ยังต้องประเมินจาก RF สองบอร์ดขึ้นไป

พิกัด Anchor ไม่ calibrate ขึ้นมาเองจาก USB/BLE ต้องสำรวจในกรอบเดียวกับแผนที่
Pure TDoA ไม่ต้องใช้ orientation/AoA สำหรับแก้ 3D; หากใช้ AoA ในงานอื่นต้องสอบเทียบแยก

RTLS ใช้ Edge Socket.IO ของโครงการ ไม่ใช่ MQTT จาก Type2BP โดยตรง
PC เก็บ gateway token เฉพาะ runtime ส่งเฉพาะ accepted fresh real fixes และทิ้ง backlog
เมื่อขาดการเชื่อมต่อ ไม่มี replay/synthetic fixes ใช้แทน production acceptance

## ไฟล์ที่ใช้

- Launcher: `Start_Standalone_BLE_Bench_Preview_v5.cmd`
- GUI: `app/ble_prototype/v1/standalone_bench_gui_v8.py`
- Flasher: `app/ble_prototype/v1/uwb_ble_flasher_v2.py`
- Firmware source: `firmware/source/v20-paced-telemetry-pilot/`
- Builder: `tools/build_firmware_provisioned_pilot_v6.py`
- Guide: `docs/STANDALONE_BLE_PREVIEW.v3.th.md`
- Protocol: `docs/BLE_PILOT_PROTOCOL.v3.md`

Vendor SDKs/toolchain/binaries/runtime, backup/session logs และ credentials เก็บในเครื่อง
ไม่ Push ขึ้น repository การเปลี่ยน host firmware ไม่ใช่ snapshot/restore radio NVM ทั้งหมด
