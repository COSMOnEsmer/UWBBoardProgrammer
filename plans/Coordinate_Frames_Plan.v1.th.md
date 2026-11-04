# แผนทำมาตรฐานพิกัด Auto Survey → Floor → RTLS

วันที่ตรวจสอบ: 4 พฤศจิกายน 2026 โปรแกรมปัจจุบัน 2.7.0

## ข้อค้นพบ

- Auto Survey กำหนดจุดเสาอากาศ Tag อ้างอิงเป็น S=(0,0,0) และวัด +X/+Y/+Z อีกสามจุด ค่า Z ของ Anchors จึงอ้างอิงระดับเสาอากาศ Tag ที่จุดกำเนิด ไม่ได้รับประกันว่าเป็นความสูงจากพื้น
- Auto Survey บันทึกพิกัด S ลง Profile โดยตรง ยังไม่มีขั้นลงทะเบียนพิกัด S เข้ากับ Floor
- Cloud ปัจจุบันเปรียบเทียบพิกัดใน Profile กับ posXM/posYM/posZM ของ RTLS โดยตรง และส่ง x_m/y_m/z_m โดยไม่มีการแปลงกรอบ
- Profile ในภาพใช้ bounds [-2,-2,0] ถึง [2,2,2] แต่แผนที่ที่ Origin X/Y เป็นศูนย์และขนาด 4×4 ครอบคลุม [0,4]×[0,4] การแสดง Anchors ที่ติดลบนอกกรอบจึงสอดคล้องกับกรอบที่ต่างกัน ไม่ใช่หลักฐานว่า TDoA คำนวณผิด
- Edge integration guide ระบุว่า levelIndex เป็นลำดับชั้น; elevationM เป็นระดับพื้นเทียบ datum ของ Site; Anchor และ Tag telemetry ต้องอยู่ใน floor-local frame เดียวกัน
- ตรวจ public dashboard bundle index-4wUCnQe-.js: กรอบสี่เหลี่ยมคำนวณจาก originXM/originYM ถึง originXM+lengthM/originYM+widthM และ footprint บวก origin ก่อนแสดง ดังนั้นต้องแยกขอบเขตแผนที่ออกจากจุดอ้างอิงการสำรวจ
- ชื่อ Site/Floor ในภาพกับโปรไฟล์เก่าต้องตรวจผ่าน ID จริง รวมทั้งแยก UWB MAC, BLE address และ RTLS Anchor ID ให้ชัดเจน ชื่อหรือที่อยู่ BLE ไม่ใช่พิกัดหรือหลักฐานว่าจับคู่ไซต์ถูกแล้ว

## มาตรฐานที่เสนอ

| กรอบ | จุดกำเนิดและแกน | หน้าที่ |
| --- | --- | --- |
| Survey S | เสาอากาศ Tag ณ จุด Origin; X/Y ที่วัดตั้งฉาก; Z ขึ้น | เก็บระยะดิบ หาพิกัด Anchors และคำนวณ TDoA ในกรอบติดตั้ง |
| Floor F | มุมอ้างอิงของพื้นชั้น; X ขวา Y ขึ้นบนแผนที่ Z สูงจากพื้นชั้น | มาตรฐานพิกัด Anchor, Tag, bounds และ telemetry ที่ใช้กับ RTLS |
| Site/world W | datum ของอาคารหรือ Site | รวมชั้น/ตำแหน่งอาคาร; ใช้ elevationM เพื่อแปลง Z ตามนิยามที่ยืนยัน |
| Image | พิกเซล u ขวา v ลง | แสดงภาพแปลนเท่านั้น; metersPerPixel ไม่ปรับระยะ TDoA |

สำหรับการติดตั้งปัจจุบันให้กำหนด Floor Origin X/Y=0, ขนาด 4×4, Z จากพื้น และเลือก elevation ของพื้นจริง แยกจาก levelIndex=0 หากพื้นนี้เป็น datum ให้ elevation=0 เลขชั้นไม่ใช่เมตรและไม่ใช้คูณความสูงชั้น

ใช้การแปลง rigid ระหว่าง S กับ F:

    p_F = Rz(theta) p_S + t
    x_F = cos(theta)*x_S - sin(theta)*y_S + t_x
    y_F = sin(theta)*x_S + cos(theta)*y_S + t_y
    z_F = z_S + h_origin

t คือพิกัดของเสาอากาศ Tag ที่จุด Origin ของ Survey เมื่อระบุใน Floor; h_origin คือความสูงเสาอากาศจุดนั้นจากพื้นจริง ต้องวัด ไม่อนุมานจากภาพ θ เป็นมุมทวนเข็มนาฬิการะหว่าง +X ของ Survey และ +X ของ Floor วิธี yaw+translation ใช้เมื่อ +Z ของ Survey ถูกวัดให้ตั้งตรงแล้ว หากต้องรองรับแกนเอียงให้ใช้ full 3D rigid registration ที่มีจุดอ้างอิงเพียงพอ

scale=1 หน่วยเมตร การลงทะเบียนกรอบไม่ควรปรับ scale เพื่อกลบข้อผิดพลาดการวัดหรือ antenna delay ไม่กลับแกน Y ใน solver; การกลับพิกเซล Y ลงทำเฉพาะตัววาดภาพ

## ตัวอย่างสำหรับภาพที่ส่งมา

สมมติเสาอากาศ Origin ของ Survey อยู่ตรงกลางพื้นที่ Floor ที่ (2,2,h_origin) และแกน X/Y ขนานกันจริง:

| Anchor | X_S | Y_S | X_F | Y_F | Z_F |
| --- | --- | --- | --- | --- | --- |
| A1 | -0.444 | 0.452 | 1.556 | 2.452 | 0.891+h_origin |
| A2 | 0.881 | 0.469 | 2.881 | 2.469 | 1.891+h_origin |
| A3 | 1.318 | -0.389 | 3.318 | 1.611 | 0.779+h_origin |
| A4 | -1.132 | -0.426 | 0.868 | 1.574 | 0.518+h_origin |

ตารางเป็นตัวอย่างของสมมติฐาน ไม่ใช่พิกัดที่ยืนยันให้บันทึกทับ หาก h_origin=1 เมตร A2 จะสูง 2.891 เมตร ซึ่งเกิน Height=2 ในภาพ ต้องตรวจระดับอ้างอิงและความสูงพื้นที่จริง ไม่ตัด Z ให้เข้า bounds และไม่ใช้ h_origin=0 เพียงเพื่อให้ภาพดูถูกต้อง

การเลื่อนกรอบแผนที่ไป Origin=(-2,-2) อาจทำให้ XY เดิมอยู่ในกรอบ แต่ไม่ได้แก้ความสูง/การหมุน หรือทำให้การสำรวจที่วัดผิดถูกต้อง จึงไม่ใช่วิธีหลักที่เสนอสำหรับมาตรฐานนี้

## แผนพัฒนา

### Task 1 — Coordinate contract และข้อมูลโปรไฟล์

- เพิ่ม schema/version ของ coordinate frame; เก็บ survey geometry ดิบ, floor mapping, rotation, translation, จุดอ้างอิงและผลตรวจสอบแยกกัน
- แสดงกรอบ/หน่วยชัดเจนในทุกหน้า เช่น Survey coordinates และ Floor coordinates
- เก็บไฟล์เก่าครบ โปรไฟล์เก่าที่ไม่ระบุกรอบขึ้นสถานะ Unmapped ไม่เดาว่าพิกัดติดลบหมายถึงอยู่ตรงกลางหรือว่าต้องบวก 2 เมตร
- เก็บ Site ID/Floor ID และ config version กับ mapping ป้องกันนำ mapping เดิมไปใช้ข้ามชั้น

### Task 2 — Floor setup จาก RTLS

- อ่าน Site/Floor ID, origin, dimensions, footprint, elevation และ image scale จาก configuration ที่ API ส่งจริง หากขาดมิติให้กรอก/นำเข้าเองและระบุแหล่งข้อมูล
- วาดกรอบพื้นและลูกศร X/Y/Z ชัดเจน จับคู่ UWB MAC → RTLS Anchor ID แยกจาก BLE address
- ใช้ Floor bounds [0,0,0] ถึง [4,4,H] สำหรับตัวอย่าง Origin=0 โดย H ต้องตรงการติดตั้งจริง; แยก operational bounds ของ solver จาก viewport/ขอบแปลน

### Task 3 — Align survey to floor wizard

- ให้ผู้ใช้ระบุพิกัด Floor ของจุด Origin ของ Survey และความสูงเสาอากาศจากพื้น
- ถ้าแกนขนาน ให้เลือก aligned axes และ translation พร้อมภาพซ้อนพิกัดก่อน/หลัง
- ถ้าแกนไม่ขนาน ใช้จุดอ้างอิง XY อย่างน้อยสองจุดที่ไม่ซ้ำเพื่อหาทิศทาง เมื่อ Z ตั้งตรงอยู่แล้ว; แนะนำสามจุดขึ้นไปเพื่อตรวจ residual และอีกจุดอิสระเพื่อยืนยัน
- ตรวจ baseline, ทิศทางแกน, การสะท้อน, ความไม่แน่นอน และการวัดผิด; scale คงที่ 1
- ปุ่ม Preview alignment → Validate → Save new aligned profile โดยไม่ต้องเก็บ TWR ใหม่หากบอร์ดและจุดสำรวจเดิมไม่ได้ย้าย

### Task 4 — เชื่อม Auto Survey เข้ากับ mapping

- ผู้เริ่มใหม่สามารถตั้ง Floor ก่อน แล้วเลือกจุด Origin และแกน Survey ให้ตรงกับ Floor ตั้งแต่ต้น
- ผล Auto Survey ต้องผ่านหน้า Align to floor ก่อน export/sync กับ RTLS
- เก็บผล Survey S ไว้ตลอด การแก้แผนที่หรือเปลี่ยน Origin ไม่บวก offset ซ้ำลงค่าที่แปลงแล้ว
- การสอบเทียบพิกัด Anchors ไม่เท่ากับการสอบเทียบ clock, antenna delay หรือ AoA ให้แสดงสถานะแยกกัน

### Task 5 — ใช้ transform เดียวกันทั้งระบบ

- คง solver/clock/ระยะและ orientation calibration ใน S แล้วแปลงผลเพื่อแสดงและส่งใน F การเลื่อน/หมุนแบบ rigid ไม่เปลี่ยนระยะระหว่าง Anchors
- แปลง Anchor overlay, Tag ทั้ง accepted/diagnostic, เส้น Path 30 วินาที, reference markers และ exports ด้วย transform เดียวกัน
- ตัวตรวจ cloud ต้องเปรียบเทียบพิกัด Anchor ที่แปลงเป็น F แล้วกับ server ไม่เปรียบเทียบ S กับ F โดยตรง
- ส่ง x_m/y_m/z_m ใน F ตาม Edge contract โดยไม่บวก elevation ของ Site ซ้ำ; ถ้าต้องแสดง Site Z ให้แสดงเป็นช่องแยกพร้อมนิยาม
- หมุน covariance/velocity เมื่อมีค่าเหล่านี้; คง metadata และเกณฑ์ accepted/display-only เดิม
- หากแปลง bounds แบบ AABB ต้องแปลงมุมครบแปดจุด; ไม่แปลงเฉพาะ min/max สองจุดแล้วถือว่าเป็นขอบเขตเดิม

### Task 6 — ตรวจความถูกต้องก่อนใช้จริง

- Unit checks: identity, translation, yaw 90°, inverse/round-trip, ระยะ invariance, Z origin, ไม่มี elevation/offset ซ้ำ, แยกชั้น, covariance และ profile migration
- วาง Tag ที่จุดตรวจอิสระอย่างน้อยสามจุดและต่างความสูง ตรวจ error เชิง XYZ พร้อมแยก registration error กับ RF positioning error
- เปรียบเทียบ Anchor และ Tag บนโปรแกรม/RTLS ว่าอยู่มุมและด้านเดียวกัน แสดงรหัสอุปกรณ์ตรงกันและมี ACK จาก cloud
- จุดอยู่นอกพื้นให้เตือนและแสดงตามจริง ไม่ clamp เข้ากรอบให้ดูเหมือนถูกต้อง

## สิ่งที่ต้องทราบก่อนกำหนด transform จริง

1. จุด Origin เดิมของ Auto Survey อยู่ที่ใดเมื่อวัดจากมุมอ้างอิง Floor
2. เสาอากาศ Tag ณ Origin นั้นสูงจากพื้นเท่าใด
3. +X/+Y ของ Survey ชี้ตรงกับแกนใดของแปลน และมีการย้ายบอร์ดหลังสำรวจหรือไม่
4. Site/Floor และ Anchor IDs ที่เลือกใน RTLS เป็นชุดใดจริง

การเก็บช่วงนี้ใช้ Tag บน CR2032 ได้ตามขั้นตอน BLE เดิม การแปลงกรอบเป็นงานฝั่ง PC ไม่ต้อง Flash Firmware เพื่อเปลี่ยน Origin ของแผนที่

## แหล่งตรวจสอบ

- Experiments/RTLSPlatform/05.edge-integration-guide.md: floors field reference และ edge:position payload
- app/revisions/v15/uwb_board_programmer/survey_wizard.py: reference_positions, save_survey
- app/revisions/v15/uwb_board_programmer/cloud.py: validate_scope, position_payload
- https://uwb.mangosgo.com/assets/index-4wUCnQe-.js: public dashboard rendering bundle ที่อ่านได้ขณะตรวจสอบ (ไม่ได้เปลี่ยนการตั้งค่าเซิร์ฟเวอร์)
