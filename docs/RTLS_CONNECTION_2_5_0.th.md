# เชื่อม UWB Board Programmer 2.5.0 กับ RTLS Platform

โปรแกรมรับค่าบอร์ดผ่าน BLE คำนวณตำแหน่งบน PC แล้วส่งไป backend
https://api-uwb.mangosgo.com ผ่าน Socket.IO namespace `/edge` ส่วน
https://uwb.mangosgo.com เป็นหน้าเว็บดูแผนที่และตั้งค่าระบบ
อ้างอิงคู่มือ Edge Integration Guide ที่ผู้ใช้จัดเตรียมและโค้ด cloud client
การปรับหน้าจอรุ่นนี้ไม่ได้ทดสอบส่งพิกัดจริงเข้าระบบใหม่

1. ในเว็บ เลือก Site/Floor ที่จะใช้ เช่น KMUTNB และชั้นที่ตรงกับโปรไฟล์
   หากใช้แผนที่เดิม ต้องปรับกรอบพิกัดของการวัดจริงให้ตรงกับแผนที่
   จุดกำเนิด ทิศแกน เมตรต่อพิกเซล และระดับความสูงต้องอ้างกรอบเดียวกัน
   การใช้ค่าระยะ 1 เมตรในห้องทดลองไม่เท่ากับแผนผังจำลองขนาด 40 × 16 เมตร
2. ลงทะเบียน/เลือก Anchors และ Tag ของชุดฮาร์ดแวร์จริง ให้ Anchor ID,
   Tag ID, Site ID, Floor ID และ Master/Slave ตรงกับโปรไฟล์โปรแกรม
   UWB MAC ใช้ผูกกับบอร์ด ส่วน ID ที่ส่ง cloud ต้องตรงกับรายการบนเว็บ
3. กรอกพิกัด Anchors ที่วัดจริงในเว็บให้ตรงกับโปรแกรม โปรแกรมตรวจว่าต่างกัน
   ไม่เกิน 1 เซนติเมตร กด Export RTLS anchor setup ในหน้า Survey & calibration
   เพื่อเปิดรายการข้อมูลที่ต้องกรอก ไฟล์นี้เป็นเอกสารตั้งค่า ไม่ได้แก้เว็บอัตโนมัติ
4. สร้าง/เลือก Edge Gateway ของบอร์ดจริง และคัดลอก Gateway ID กับ Bearer Token
   ปุ่ม Register gateway ในโปรแกรมเปิดหน้าลงทะเบียนได้ Token นี้เป็นของ Gateway
   รหัสผ่านล็อกอินหน้าเว็บใช้แทน Token ไม่ได้ ไม่ควรใช้ ID/Token/Tag เดียวกับ
   Simulator ที่กำลังส่งอยู่พร้อมกัน โดยโปรแกรม RTLSSimulator เดิมไม่ถูกแก้ไข
5. ในโปรแกรม เปิดโปรไฟล์ที่สำรวจแล้ว เชื่อม BLE และเริ่ม Live positioning
   ให้มีตำแหน่งที่ผ่านเกณฑ์ก่อน ข้อมูล Warning และ Last known ในหน้าจอใช้ดูในเครื่อง
   ไม่ถือเป็นพิกัดใหม่ที่ผ่านเกณฑ์ และไม่ถูกส่งเป็นตำแหน่งใหม่ไป RTLS
6. หน้า RTLS Platform กรอก GATEWAY ID และ BEARER TOKEN แล้วกด Check configuration
   แก้ Site/Floor/Anchor ID/Role/พิกัดที่ไม่ตรงตามข้อความแจ้งก่อน
7. กด Connect RTLS และเลือก Publish live positions that pass the quality checks
   ตัวเลือก Also publish raw BLINK and SYNC measurements ใช้เมื่อต้องการข้อมูลดิบด้วย
   Save encrypted token เก็บ Token ด้วย Windows DPAPI เฉพาะผู้ใช้ Windows เครื่องนั้น
8. ตรวจ Cloud connected, config verified, ACK OK เพิ่มขึ้น และ errors ไม่เพิ่ม
   เปิดแผนที่ Site/Floor เดียวกันในเว็บ และเลือก Tag ID เดียวกับโปรแกรม

หาก Gateway online แต่ Tag ไม่ขึ้น ให้ตรวจว่ามี accepted fix ในโปรแกรมจริงหรือไม่
ตรวจ Token scope, Tag ที่ลงทะเบียน, ID และพิกัดกรอบแผนที่ รวมถึงข้อความ ACK rejected
โปรแกรมส่ง `edge:position`, heartbeat และ device status โดยไม่ backfill พิกัดเก่า
หากเน็ตหลุด การบันทึกในเครื่องยังทำต่อ และส่งเฉพาะข้อมูลใหม่หลังเชื่อมกลับ

พิกัด Warning อาจคลาดเคลื่อนมาก โดยเฉพาะค่า Z เมื่อรูปทรง Anchors ไม่เหมาะกับ 3D
การคงจุดล่าสุดและ Path ในหน้าจอช่วยให้ดูการรับข้อมูลต่อเนื่อง แต่ไม่ได้เพิ่มความแม่นยำ
