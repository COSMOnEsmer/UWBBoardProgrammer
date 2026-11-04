# เชื่อม RTLS ด้วยกรอบ Floor ใน 2.8.0

ดู [คู่มือ 2.8.0](INTEGRATED_STANDALONE_GUIDE.v10.th.md) สำหรับขั้น Align เต็มรูปแบบ

ลำดับหลัก: เลือก Gateway/Site/Floor → จับคู่ Anchor IDs → Auto Survey → Align survey to floor → ยืนยันแกนและ Z → Check configuration → Connect RTLS

พิกัด Anchor ที่ใช้ตรวจเซิร์ฟเวอร์ และ x_m/y_m/z_m ของ Tag เป็น Floor frame เดียวกัน Level index ไม่ใช่ความสูง และ Elevation ไม่ถูกบวกซ้ำกับ z_m

หากแก้ Origin/ขนาด Floor หรือแก้ตำแหน่ง Anchors ให้ตรวจ registration ใหม่ ข้อมูลโปรไฟล์และ Token ของผู้ใช้ไม่รวมในชุดแจก การส่งข้อมูลยังจำกัดเฉพาะพิกัดสดที่ผ่านเกณฑ์คุณภาพ
