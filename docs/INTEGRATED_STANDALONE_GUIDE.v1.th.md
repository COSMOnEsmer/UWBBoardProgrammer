# UWB Board Programmer 2.1.0 — โปรแกรมเดิมพร้อม Standalone BLE

รุ่นนี้ใช้หน้าจอและขั้นตอนของ UWB Board Programmer เดิม เพิ่ม BLE/GATT เข้าในโปรแกรมเดียว
เปิด **UWB Board Programmer 2.1.0** บน Desktop หรือ launcher รุ่น v4
แอปเดิม 2.0.1, BLE Pilot เก่า, RTLSSimulator และต้นฉบับทุกไฟล์ยังเก็บไว้

## 01 บอร์ดและเฟิร์มแวร์

เลือก Connection mode เป็น **Standalone · BLE/GATT** และโหมด 4 Anchors / TDoA (3D)
ระบุ COM ของบอร์ดที่ต่อจริงและ EVK Rev4.1 เลือก A1, A2, A3, A4 หรือ Tag
แล้วกด Flash selected board ใช้เพียง USB พอร์ตเดียวและสลับบอร์ดทีละตัวได้ ไม่ต้องมีพิกัดก่อน Flash

Firmware 1.3.4-pilot มี identity ผูกกับ image: A1 master / ...0001,
A2–A4 slaves / ...0002–...0004, Tag / ...0101 ตรวจ MAC/role ของแถวให้ตรงก่อนเขียน
ระบบตรวจ USB identity อ่าน host FLASH สองชุดให้ SHA-256 ตรงกัน Program/Verify
แล้วอ่าน config ACK บันทึก report ใหม่ทุกครั้ง ไม่มี full-chip erase หรือเขียน OTP

Tag เลือก battery/standalone หรือ setup/USB diagnostics เฟิร์มแวร์ชุดนี้ผูก MAC
0200000000000101 และ interval 1000 ms การใช้ MAC/interval อื่นต้องมี image ที่ตรงกัน
หลัง Flash ต้องพิสูจน์ RF จริง การเขียน bytes และ config ACK ผ่านอย่างเดียวไม่ใช่ RF acceptance

USB · Legacy firmware ใช้ bundle และขั้นตอนเดิม แยกจากเฟิร์มแวร์ Standalone

## 02 BLE/GATT

เลือก Passive/Active scan และช่วงเวลา แล้วกด Scan BLE anchors
ตารางแสดง UWB MAC, บทบาท, BLE address และ RSSI เลือกแถวและ Anchor เป้าหมาย
กด Assign selected BLE anchor โปรแกรมตรวจ role และ MAC ซ้ำ บันทึก mapping/scan settings
ด้วย Save new profile ในหน้าสำรวจ ใช้ UWB MAC เป็น identity หลัก ไม่พึ่ง BLE address อย่างเดียว

Connect BLE + record ในหน้านี้รับข้อมูลตรวจสอบได้แม้ยังไม่มีพิกัด และมีเพียงหนึ่งบอร์ดเปิดอยู่
ตรวจ firmware/boot/config CRC, จำนวน RF frames และ Tag age ก่อนคำนวณตำแหน่ง
เมื่อเชื่อมต่อสำเร็จ PC อ่าน GATT และรับ notifications โดยไม่ส่ง radio START/STOP

## 03 สำรวจและสอบเทียบ

กรอก X/Y/Z เป็นเมตรตามที่วัดจริง ตำแหน่งสี่ Anchors ต้องไม่อยู่ในระนาบเดียวกัน
ระบุ site/floor/tag และ bounds ให้ตรงกับพื้นที่ RTLS บันทึกเป็นโปรไฟล์ใหม่
โหมด Pure TDoA ไม่ใช้ orientation/AoA ช่วยคำนวณ ส่วนโหมด 3 Anchors + AoA
ต้องสอบเทียบมุมและยืนยัน reference points ก่อนใช้คำนวณ 3D

## 04 ตำแหน่งสด

หลังกรอกพิกัดครบ กด Connect BLE + record แล้ว Start positioning
Master ส่ง UWB SYNC ให้ Slaves โปรแกรม fit clock offset/drift และชดเชย propagation
จับคู่ BLINK ด้วย corrected RF timestamps แล้วแก้ TDoA เป็น X/Y/Z
แสดงแผนที่, clock samples/drift/RMS, AoA quality และ uncertainty ในหน้าเดิม

Pause positioning หยุดการคำนวณบน PC แต่ยังบันทึกข้อมูลที่รับและไม่หยุด UWB บนบอร์ด
Disconnect BLE ปิดลิงก์และ session บน PC โดยไม่ส่ง STOP ให้ radio
USB Legacy ยังคงใช้ START/STOP แบบเดิม

Output คือ x_m/y_m/z_m หน่วยเมตร, horizontal/vertical uncertainty, residual,
จำนวน Anchors และเวลา ถ้า clock ไม่พร้อม, BLINK ไม่ครบ, geometry/ambiguity/uncertainty
ไม่ผ่าน ระบบแสดงเหตุผลและไม่สร้าง accepted fix

## 05 RTLS และ 06 Sessions

หน้า RTLS เดิมยังมี Gateway ID/token, ตรวจ configuration, DPAPI token storage
และเลือก publish positions/raw measurements ส่ง accepted fresh positions ผ่าน Edge Socket.IO
เมื่อ site/floor/Anchor IDs/roles/พิกัดตรงกับ server เท่านั้น

Session ใหม่บันทึก raw BLE, decoded observations, clocks/resets, rejections และ fixes
ใน data/sessions การ Replay อยู่ในเครื่องและไม่ส่งข้อมูลย้อนหลังไป RTLS
Session ที่เก็บก่อนสำรวจใช้ตรวจ raw data ได้ แต่ต้องมี profile สำรวจครบเพื่อ replay คำนวณตำแหน่ง

## ขอบเขตการทดสอบ

Single-anchor RF/BLE และ Tag sleep path บน USB เคยพิสูจน์แล้วใน firmware 1.3.4
ยังต้องทดสอบ Master–Slave RF clock, สี่ BLE links, ground-truth 3D, CR2032/Power Banks
และ production RTLS จริง การแสดงเมนูพร้อมใช้งานไม่ใช่การรับรองความแม่นยำทั้งระบบ

Backup host FLASH ไม่รวม protected tail, radio NVM หรือ OTP/EFUSE
ชุด EXE แบบ onedir มี runtime, DK6, resources และ firmware ที่จำเป็น ต้องย้ายทั้งโฟลเดอร์
ไม่ใช่ EXE ไฟล์เดียว จัดเก็บในเครื่องและไม่ Push licensed binaries/backups/credentials ไป GitHub
