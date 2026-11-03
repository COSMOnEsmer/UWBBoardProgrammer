# UWB Board Programmer 2.1.1 — current clock-recovery build

**เปิด START_HERE_2_1_1.cmd หรือ Shortcut UWB Board Programmer 2.1.1**

ชุด 2.1.0 และ START_HERE.cmd เดิมยังคงอยู่เพื่อรักษาไฟล์ต้นฉบับ
การทดสอบ SYNC หลังอัปเดตนี้ให้เปิดตัว 2.1.1 โดยตรง

รุ่นนี้แก้การล้าง clock fit ทุกครั้งที่ BLE telemetry ขาดหาย เพิ่มการเทียบเวลาจาก RF SYNC ที่คร่อม BLINK และตรวจความถูกต้องของ clock model โดยยังใช้เกณฑ์ 2 ns
ข้อมูลเสีย/เก่า, การเปลี่ยน boot ID, ลิงก์ขาด และช่วงเวลาที่ไม่ผ่านคุณภาพยังถูกตรวจและปฏิเสธ
Firmware บอร์ดยังคงเป็น **1.3.4-pilot** การอัปเดต PC นี้ไม่ต้อง Flash บอร์ดใหม่

สำหรับบอร์ดที่วางบนโต๊ะหรือยังใช้พิกัดทดลอง ให้ใช้ **BLE / GATT → Connect BLE + record** เพื่อดู clock model และเก็บผล
รุ่นนี้ตรวจ clock model ได้โดยไม่ต้องกรอกพิกัดสมมติ จะยังไม่มี XYZ และยังเชื่อม RTLS ไม่ได้จนกว่าจะยืนยันพิกัดจริง
เมื่อจะทดลอง 3D ให้ติดตั้ง Anchors ไม่อยู่ในระนาบเดียวกัน วัด X/Y/Z จริง แล้วเลือก **Anchor coordinates were measured at the physical antenna positions** ในหน้า Survey & calibration

คู่มือ: [ภาษาไทย](docs/INTEGRATED_STANDALONE_GUIDE.v2.th.md) / [English](docs/INTEGRATED_STANDALONE_GUIDE.v2.en.md)

แพ็กเกจ Windows x64 มี runtime, BLE libraries, USB Flash tools และ firmware ครบ ไม่ต้องติดตั้ง Python/SDK
เปิดครั้งแรกจะแตกไฟล์ใน LocalAppData เป็นโฟลเดอร์รุ่นใหม่ คัดลอกเฉพาะโปรไฟล์/การตั้งค่าภาษาจากรุ่นก่อน และสร้าง Shortcut ใหม่
token, ข้อมูลวัดจริง และ backup ไม่ถูกส่งขึ้น GitHub และไม่ถูกคัดลอกข้ามรุ่นอัตโนมัติ

Start **START_HERE_2_1_1.cmd** on Windows 10/11 x64. The full application/runtime is included; a BLE radio/driver and the EVK USB driver remain hardware prerequisites. Firmware is unchanged. Use bench diagnostics until actual non-coplanar anchor coordinates are measured and confirmed. See [validation](deployment/VALIDATION.v2.md).
