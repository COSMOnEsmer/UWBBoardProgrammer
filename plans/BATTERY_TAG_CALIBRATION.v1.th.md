# Calibration โดย Tag ใช้ CR2032 — ต้นแบบใหม่

เป้าหมาย: Anchors ทั้งสี่รับไฟจาก USB/Power Bank ตามการติดตั้งเดิม ส่วน Tag ใช้
CR2032 และไม่ต้องต่อ USB ระหว่างสอบเทียบ ไม่ต้องเพิ่มแหล่งจ่ายไฟสำหรับบอร์ดที่ห้า

## ข้อจำกัดของรุ่นที่มีอยู่

- โปรแกรม 2.2.1 ควบคุม Tag ระหว่าง Auto Survey ผ่าน USB UART
- Tag 1.4.2-pilot เป็น image สำหรับ USB calibration ที่ตั้ง MCU ให้ตื่นตลอด
  ไม่ใช่ image สำหรับประหยัดถ่านในการใช้งานระยะยาว
- Tag 1.3.4-pilot เป็น image สำหรับ BLINK/พัก MCU แต่ยังไม่เปิด BLE calibration control
- ข้อกำหนด USB จึงเกิดจาก firmware/control path ของโครงการ ไม่ใช่ข้อจำกัดพื้นฐานของ TWR

## วิธีใหม่

1. Flash Tag image ใหม่ผ่าน USB ชั่วคราว โดยเสียบเพียง Tag ก็ได้ ไม่ต้องเปิดทั้งห้าบอร์ด
2. ถอดสาย Tag ตั้งสวิตช์เป็นถ่าน แล้วเปิดไฟ Anchors ทั้งสี่ตามปกติ
3. หลัง Reset Tag เปิดหน้าต่างควบคุม BLE จำกัดเวลาประมาณ 15 นาที
4. PC ตรวจ Type2DK/MAC/version/config CRC แล้วสั่ง Tag เป็น TWR responder ผ่าน GATT
5. PC สั่ง Anchor ทีละตัวผ่าน BLE และรับระยะจาก Anchor เช่นเดิม ไม่อ่าน COM ของ Tag
6. แต่ละคำสั่งมี request/session/peer binding และ lease ไม่เกิน 30 วินาที
   หลังวัด/ขาดการเชื่อมต่อให้คืน UWB BLINK
7. เมื่อหมดหน้าต่าง ให้หยุดการเชื่อมต่อ/โฆษณา BLE ก่อนเข้าโหมดพัก MCU
   Reset Tag เพื่อเปิดหน้าต่างใหม่ได้ โดยยังใช้ถ่าน

ฝั่ง PC ใช้ไม่เกินสาม GATT links ต่อการวัด: Tag, Master A1 และ Slave ที่กำลังวัด
จึงไม่ต้องเชื่อม Tag เพิ่มเป็นลิงก์ที่ห้าพร้อม Anchors ทั้งสี่ในรอบ Calibration
โหมดใช้งาน TDoA ปกติยังรับข้อมูล Anchors ทั้งสี่ โดยไม่ต้องคง BLE connection กับ Tag

การหาพิกัดยังใช้ Tag อ้างอิงสี่จุดที่วัดจริง และ Anchors อยู่จุดติดตั้งเดิมตลอด
การเปลี่ยนแหล่งจ่ายไม่ได้เปลี่ยนสมการหรือยกเลิกการตรวจคุณภาพ LOS/geometry

## สถานะและสิ่งที่ต้องพิสูจน์

สร้าง source ใหม่ `firmware/source/v24-battery-calibration-ble` และ experimental
Tag 1.5.0-pilot แยกจาก image เดิม พร้อม PC BLE control ใน `app/battery_calibration/v1`
และเพิ่มหน้า Auto Survey โหมด BLE Tag ในโปรแกรมรุ่นใหม่ 2.3.0 โดยเก็บ 2.2.1 ไว้

ต้องทดสอบตามลำดับก่อนเผยแพร่เป็นรุ่นใช้งาน:

- Flash/boot/advertise/INFO/GATT บน USB โดยสำรองบอร์ดและตรวจตัวตนก่อน Flash
- TWR และการคืน BLINK ผ่าน GATT แทน UART
- ถอด USB แล้วทำซ้ำบน CR2032 พร้อม Anchors ทั้งสี่เปิดไฟ
- BLE disconnect/lease expiry, Reset และการหมดหน้าต่าง BLE
- ยืนยัน BLINK ยังต่อเนื่องหลังปิด BLE และตรวจโหมดพัก/กระแสจริง
- ตรวจถ่านอ่อน/อาการ reset จากแรงดันตก ไม่อ้างอายุถ่านจากการ compile ผ่าน
- จึงเพิ่มตัวเลือก Tag BLE calibration ในหน้าจอ Auto Survey และสร้างแพ็กเกจรุ่นใหม่

ทดสอบบน CR2032 ที่ถอด USB แล้วผ่านกับ A1/A2 ได้ระยะประมาณ 0.83/1.36 เมตร
โดยบอร์ดตอบรับการคืนโหมดครบ จากนั้นสังเกตการปิดโฆษณา BLE ตามเวลาและรับ BLINK
ร่วมกันผ่าน Anchors ทั้งสี่ได้ 246 เฟรม ดู `deployment/BATTERY_WINDOW_ACCEPTANCE.v1.md`
ผลนี้ไม่ใช่การวัดกระแสหรืออายุถ่าน และยังไม่ใช่ Calibration/3D acceptance ครบทั้งระบบ

Manifest ของต้นแบบเดิมยังเก็บไว้ตามเดิม ส่วน bundle เจ็ด image ใหม่สำหรับ 2.3.0
เพิ่มผล RF บนถ่านแล้ว และยังคง `battery_runtime_validated=false` ตามขอบเขตที่ทดสอบจริง
