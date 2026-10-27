# แผนพัฒนา Standalone UL-TDoA ผ่าน BLE/GATT

ปรับแผนรุ่น 2 วันที่ 28 ตุลาคม 2026 พัฒนาต่อจาก UWB Board Programmer 2.0.1 โดยเก็บต้นฉบับทุกไฟล์ไว้ ผลที่วัดจริงต้องแยกจากเป้าหมายที่ยังไม่ผ่าน

## เป้าหมาย

- Type2BP EVK Rev4.1 จำนวน 4 ตัว: A1 UWB Sync Anchor/Master, A2–A4 Slaves
- Type2DK EVK ที่ผู้ใช้ยืนยัน Rev4.1 จำนวน 1 ตัว: UL-TDoA Tag ใช้ CR2032
- Anchor รับไฟผ่านช่อง USB ของ EVK จาก Power Bank แล้วเริ่มและกู้คืน UWB เอง ไม่รอ PC
- Master ส่ง UWB SYNC ทุก 500 ms ในเฟสแรก; Tag เริ่ม BLINK 1 Hz แล้ววัดสมรรถนะก่อนเพิ่มอัตรา
- Anchor เป็น BLE peripheral/GATT server; PC เป็น BLE central รับ 4 ลิงก์พร้อมกัน
- PC ชดเชยนาฬิกา คำนวณ TDoA 3D บันทึก session และส่ง fresh accepted fixes ไป RTLS
- ปิดโปรแกรม/PC หรือ BLE หลุดแล้ว Anchor ยังต้องทำงาน UWB ต่อ
- USB ยังคงใช้ Flash/commissioning/diagnostic ทีละบอร์ดได้ ขณะใช้งานจริงไม่ใช้ USB data กับ PC

~~~mermaid
flowchart LR
  T[Type2DK / CR2032] -->|UWB BLINK| M[Type2BP A1 Master]
  T -->|UWB BLINK| S[Type2BP A2-A4 Slaves]
  M -->|UWB SYNC| S
  M -->|BLE/GATT| P[PC]
  S -->|BLE/GATT| P
  P --> C[Clock correction / 3D TDoA]
  C --> L[Local recording]
  C -->|fresh accepted positions| R[RTLS Edge Socket.IO]
~~~

## สถานะเริ่มต้นที่ยืนยันแล้ว

| รายการ | ข้อเท็จจริง |
| --- | --- |
| ฮาร์ดแวร์ | ผู้ใช้ยืนยัน Type2BP ครบ 4 ตัว, EVK Rev4.1 |
| บอร์ดที่ต่อ | Tag และ Anchor อย่างละหนึ่งบอร์ดต่อผ่าน USB; ตัวตน USB จริงเก็บเฉพาะ verification ภายในเครื่อง |
| สิทธิ์ทดลอง | ผู้ใช้ออกคำอนุญาต Flash และทดสอบจริงแล้ว |
| PC Bluetooth | Intel Wireless Bluetooth, BLE/Central supported, Radio On |
| BLE RF bench | Bleak รับ advertisements จริง 113 ครั้งใน 8 วินาที; ไม่ใช่ผลทดสอบ GATT ของ Anchor |
| โปรแกรม 2.0.1 | มี USB, Flash ทีละบอร์ด, solver, replay, RTLS connector; เคยผ่าน 47 software tests |
| Anchor firmware ปัจจุบัน | รุ่น 1.0.0 เดิมรอ E2E START; pilot ใหม่ auto-start และเพิ่ม custom BLE/GATT แยกจากชุด release |
| Tag battery image | มีโค้ด auto-start/sleep แต่ยังต้องพิสูจน์ BLINK บน CR2032 |
| เฟิร์มแวร์ที่ติดตั้งจริง | ทดลอง master pilot หลาย revision; อ่าน UCI active/running และ BLE advertising ได้ ยังไม่ผ่าน RF/GATT acceptance ครบ |
| SDK/DK6 | Anchor สำรอง host FLASH 646144 bytes สองครั้ง SHA-256 ตรงกันแล้ว; Tag ยังไม่ตอบ bootloader จึงยังไม่เขียน Flash |

## การเก็บต้นฉบับและการทดลอง

1. Source/SDK work copy/binaries/logs/profiles/launcher ใหม่ทั้งหมด ไม่แก้ vendor originals, RTLSSimulator หรือ 2.0.1 เดิม
2. ตรวจ USB identity ก่อนเขียนทุกครั้ง ไม่เชื่อ COM number เพียงอย่างเดียว
3. อ่าน host FLASH สองครั้งและตรวจขนาด/SHA-256 ให้ตรง พร้อมเก็บ configuration ที่อ่านได้ก่อนทดลอง
4. ไม่ mass erase, เขียน OTP/EFUSE, unlock หรือเปลี่ยน protection/authentication settings
5. Host FLASH backup ไม่ใช่ snapshot ของ radio NVM ทั้งหมด ต้องบันทึกและยกเลิก SR040 test-session NVM แยกตาม API
6. SDK/backups/configuration เฉพาะบอร์ด/credentials เก็บ local และไม่ Push
7. ทดสอบ UWB ผ่าน USB ก่อนเพิ่ม BLE เพื่อแยกปัญหา RF กับ transport
8. ไม่ส่ง replay/synthetic fixes ไป RTLS เพื่อใช้แทนการทดสอบจริง

## Firmware Anchor ใหม่

- ใช้ Master image สำหรับ A1 และ Slave image เดียวกันสำหรับ A2–A4
- Commissioning เก็บ stable Anchor ID, unique UWB MAC, cluster/master MAC, role, radio profile, auto-start และ schema/CRC ของ config
- บอร์ดที่ยังไม่มี valid unique config ต้องแสดง commissioning-required ไม่เริ่มด้วย Slave MAC ซ้ำกัน
- Boot sequence: init -> validate config -> radio/calibration init -> auto-start -> BLE advertise -> RF ต่อเนื่อง
- แยกคิว RF/BLE มี sequence/drop counters จำกัด RAM และไม่บล็อก RF callback ด้วย GATT/ข้อความยาว
- Radio failure มี backoff/recovery; BLE disconnect ไม่หยุด radio
- ใช้ QN9090 BLE stack และ GATT APIs ของ SDK; ไม่ใช้ Apple Nearby Interaction service แทน telemetry ของเรา
- เก็บ USB diagnostic ไว้เปรียบเทียบ RF fields กับ BLE แบบ byte-exact
- ไม่เขียน NVM ทุก heartbeat/BLINK

## Firmware Tag

- ขั้น USB commissioning บันทึก MAC/interval แล้วติดตั้ง battery image และตรวจค่าที่เก็บจริง
- Power-on ส่ง BLINK เอง พิสูจน์ว่าเมื่อ MCU พัก SR040 ยังส่งตามอัตราที่ตั้ง
- ตรวจ USB/CR2032, cold boot, retained settings, reset/brownout และอาการถ่านอ่อน
- วัดกระแสเฉลี่ย/พีกด้วยเครื่องมือก่อนประมาณ battery life ไม่อ้างอายุถ่านจากโค้ด sleep

## BLE/GATT draft — freeze หลัง prototype

มี binary wire contract, bounded reassembler, PC central, live pipeline และ correlated solver ใน app/ble_prototype/v1 แล้ว อ้างอิง docs/BLE_PILOT_PROTOCOL.v1.md; ทั้งหมดเป็น pilot ยังไม่ใช่ desktop release ใหม่

- Custom 128-bit service UUID ของโครงการ พร้อม protocol version และ stable characteristic UUIDs
- Device Info (Read): ID/UWB MAC, role, firmware/protocol, boot/session ID, config checksum/capabilities
- Measurement (Notify): BLINK/SYNC, peer MAC, original RX timestamp, Master TX timestamp เมื่อมี, timestamp widths, frame number, status และ quality
- Health (Read/Notify): UWB/BLE state, queue drops, sequence gaps, reset reason, uptime
- Control/ACK เฉพาะ commissioning/diagnostic มี command ID/result/timeout; การ attach อ่านข้อมูลไม่เปลี่ยน radio/config โดยปริยาย
- จับคู่ด้วย stable ID/metadata ไม่พึ่ง BLE name/address อย่างเดียว
- ระบุ endianness, field sizes, units, signedness, invalid flags และ golden vectors
- ห้ามแปลง uint40/uint64 RF epochs เป็น float หรือใช้ BLE arrival time แทน RF time
- Binary framing แบ่งชิ้นตาม ATT MTU ต้องทำงานกับ payload 20 bytes ได้
- Fragment มี session/message identity, index/count/length; ตรวจครบก่อน parse จำกัดขนาด/เวลา/จำนวนค้าง และทิ้งเก่า/ซ้ำ
- หลัง reconnect ส่ง info ใหม่ ล้าง measurement backlog และรอข้อมูลสด

## PC/GUI รุ่นใหม่

- สร้าง source revision ใหม่จาก 2.0.1 คง USB backend ไว้สำหรับ debug/rollback
- USB/BLE แปลงเป็น Observation/board-state รูปแบบเดียว เว้น interface สำหรับ MQTT ในอนาคต
- BLE ใช้ asyncio worker thread ที่ถูกต้องกับ WinRT/MTA ไม่บล็อก Qt หรือ solver
- ใช้ scanner instance เดียว จัดการ connect/subscribe/reconnect แยก 4 Anchor IDs ตาม profile
- แยกเริ่มประมวลผลจากคำสั่งเริ่ม/หยุด radio; ปิดโปรแกรมไม่ส่ง STOP ให้ autonomous Anchors อัตโนมัติ
- ตรวจ boot/session/sequence, stale/reordered/duplicate/overflow ก่อนเข้าคำนวณ
- Session บันทึก raw BLE, decoded data, radio state, clock fits, fixes และ rejection reasons พร้อม transport metadata
- UI TH/EN: scan/assign A1–A4, link health, compatibility, flash/commission selected, profile, recording, RTLS และ recovery guide
- แสดง PC version/firmware version แยกกัน มี launcher รุ่นใหม่ชื่อชัดเจน

## Clock และ TDoA

- Master เป็น UWB time reference; BLE central ไม่ใช่ UWB Master
- ใช้ SYNC Master TX/Slave RX ประมาณ offset/drift พร้อม propagation delay จากพิกัด Master–Slave และ calibration bias
- ตรวจ sample count/time span, age, fit residual และ clock jumps ก่อนใช้
- RF reset/BLE gap ที่ unwrap ไม่แน่นอนต้อง invalidate clock/pending frames และเรียนรู้ใหม่
- จับ BLINK เดียวกันด้วย corrected RF time และ frame identity; ไม่ใช้ frame counter อย่างเดียวเพราะ SDK อาจให้เลขซ้ำ
- Pure 4-anchor TDoA ไม่ใช้ AoA; พิกัดต้อง non-coplanar และ bounds มาจากพื้นที่จริง
- pilot เพิ่ม covariance ของ Master RX ที่แชร์กันแล้ว และรวม Slave clock RMS เป็นพจน์อิสระ; ยังต้องเพิ่ม prediction uncertainty ของ clock fit ตามอายุ/ช่วงข้อมูลและพิสูจน์ด้วย RF จริง
- รักษา physical-baseline, geometry/conditioning, analytic roots/multi-start, ambiguity และ uncertainty gates
- 4 Anchors เป็นขั้นต่ำ มี 3 independent TDoAs จึงใช้ residual ต่ำอย่างเดียวรับรองความถูกต้องไม่ได้ ต้องวัด ground truth และยอมรับ no-fix เมื่อไม่แน่นอน

## Tasks / เกณฑ์ผ่าน

| Task | ผลส่งมอบ | เกณฑ์ก่อนขยับขั้น |
| --- | --- | --- |
| T00 | Audit/backup/recovery | identity ตรง, host FLASH สองครั้งตรงกัน, logs/manifest |
| T01 | BLE PC bench | รับ advertisements จริงได้ — ผ่านเบื้องต้น 113 events/8 s |
| T02 | USB RF baseline, 1 Anchor + Tag | Flash/verify/HELLO, radio init OK, รับ BLINK จาก Tag MAC จริงและ RF timestamps สมเหตุผล |
| T03 | Anchor Auto-start | boot/reset เริ่ม RF โดยไม่ส่ง START และไม่มี PC client ก็ยังรับ BLINK |
| T04 | GATT proof/schema | scan/read/connect/notify/fragmentation; BLE data ตรง USB trace |
| T05 | Commissioning ทีละบอร์ด | A1–A4 IDs/MAC ไม่ซ้ำ, config persist, ไม่ต้องมีพอร์ตอื่นครบ |
| T06 | PC BLE/GUI candidate | USB/BLE regression ผ่าน, attach autonomous radio ได้, ปิดแอปไม่หยุด RF |
| T07 | Master + Slave | ต้องต่อเพิ่ม 1 Anchor; SYNC/BLINK ทั้งคู่, fit offset/drift และ reset recovery |
| T08 | 4 Anchors BLE พร้อมกัน | 4 links, 3 fresh Slave fits, BLINK ครบ, reconnect ไม่สร้าง false fixes |
| T09 | 3D validation | measured non-coplanar geometry, จุดหลายตำแหน่ง/ความสูง, error median/P95 และ availability |
| T10 | Power acceptance | Power Banks/CR2032 จริง, cold boot/reconnect, ตรวจ auto-off ของ Power Bank และ retained settings |
| T11 | RTLS E2E จริง | gateway/site/floor/พิกัดตรง, fresh real fixes, ACK และ dashboard ยืนยันได้ |
| T12 | Package/docs/release | EXE/shortcut ใหม่, TH/EN guides, manifests, source Push โดยไม่รวม vendor/backups/credentials |

## Acceptance matrix

- Functional: readback/verify, valid config, auto boot, BLINK/SYNC, GATT fields, 4 links, replay, RTLS ACK
- Recovery: init failure, BLE drop, Master/Slave power-cycle, PC restart, missing Tag, invalid fragments
- Integrity: uint64 > 2^53, 40-bit wrap, duplicates/reordering, boot/session changes, bounded queues
- RF/geometry: LOS/NLOS, ขอบพื้นที่, หลาย Z, poor geometry, two-root ambiguity
- Power: USB vs Power Bank vs CR2032, MCU sleep ที่ไม่หยุด BLINK, restart หลังไฟตก
- Soak: bench 10 นาที -> 1 ชั่วโมง -> 8 ชั่วโมงเมื่อขั้นสั้นผ่าน บันทึก loss/reset/clock/latency/queue health
- UI: TH/EN, missing adapter, incompatible firmware/wrong identity, flash พอร์ตเดียว และ legacy USB profiles

เป้าหมายแรก 1 fix/s เมื่อข้อมูลครบ ส่วนเกณฑ์ latency/accuracy/availability จะ freeze จาก pilot measurements และขนาดพื้นที่จริง รายงาน error เทียบ ground truth แยกจาก covariance ของ solver ไม่อ้างความแม่นยำระดับเซนติเมตรจาก software fixtures

## อุปกรณ์ตามเฟส

- คู่ COM7/COM9 ใช้ T00–T04 ได้ แต่ยังพิสูจน์ 3D ไม่ได้
- T07 ต้องเปิด Master กับ Slave พร้อมกันเพิ่มอีกหนึ่งตัว
- T08–T11 ต้องเปิดครบ 4 Anchors + Tag, มี Power Banks/ถ่าน, พิกัดสำรวจ และ RTLS hardware Gateway token
- ระหว่างพิสูจน์ BLE หาก USB ใช้จ่ายไฟ ต้องไม่เปิด COM data แล้วจึงทดสอบ Power Banks จริงอีกครั้ง
- ถ้าไม่มีเครื่องวัดกระแสยังทำ firmware/BLE/positioning ต่อได้ แต่ยังสรุป battery life ไม่ได้

## อ้างอิง

- SDK เดิม: demo_ultdoa_sync_anchor, demo_ultdoa_anchor, demo_ultdoa_tag_sr040, QN9090 BLE server/GATT APIs
- [Bleak WinRT/MTA](https://bleak.readthedocs.io/en/stable/backends/windows.html)
- [Bleak scanner/multiple devices](https://bleak.readthedocs.io/en/stable/api/scanner.html)
- [NXP QN9090 resources](https://www.nxp.com/products/QN9090-30)

ชื่อเวอร์ชัน UUID และ wire schema จะ freeze หลัง prototype ผ่าน แผนนี้ไม่ใช่คำยืนยันว่าทุกเฟสผ่านฮาร์ดแวร์แล้ว


## ผล pilot ล่าสุด 28 ตุลาคม 2026

- A1: Flash ผ่าน workflow ใหม่แล้ว สำรองสองชุด, Program/Verify, autonomous HELLO
  version 1.3.1-pilot, MAC/role/config CRC ตรง manifest และ UWB state running
- รีเซ็ต A1 แบบไม่เขียน Flash แล้ว GATT อ่าน MAC/CRC เดิมได้ พร้อม boot ID ใหม่และ running
  ไม่ได้ส่ง START หรือ CONFIG จาก PC
- Native GUI เชื่อม A1 ผ่าน BLE ได้และ disconnect สะอาด ไม่มี radio STOP หรือ cloud connection
- สร้างครบ A1–A4 ที่ MAC ต่างกัน และ Tag setup/battery; A2–A4/Tag ยังไม่ผ่าน bench RF
- Tag ที่ต่ออยู่ยังไม่ตอบ bootloader หลังทดสอบ USB/reset จึงยังไม่เขียน Flash ของ Tag
- ยังไม่มี BLINK/SYNC measurement stream จากชุดครบ, 4-link test, measured 3D fix,
  Power Bank/CR2032 acceptance หรือ production RTLS ACK ของ real fixes
- หน้าจอใหม่เป็น Preview แยกจาก 2.0.1; production EXE release รอ hardware acceptance
