# โปรแกรม BLE, การย้ายไปแล็ปท็อป และ Output ของ TDoA

อ้างอิงโค้ด BLE Preview GUI v8 / firmware 1.3.4-pilot ณ 28 ตุลาคม 2026

## ใช้โปรแกรมตัวไหน

เปิด shortcut **UWB Board Programmer - BLE Preview** บน Desktop
หรือ `Start_Standalone_BLE_Bench_Preview_v5.cmd` ในโฟลเดอร์โครงการ
โปรแกรมนี้ Flash ทีละบอร์ดผ่าน USB, รับ UWB observations ผ่าน BLE/GATT,
บันทึก session, คำนวณ four-anchor 3D TDoA และมี RTLS Edge connector

โปรแกรมเดิมชื่อ **UWB Board Programmer 2.0.1** ใช้ workflow และ firmware bundle
ชุดเดิม ตัวเลข **1.3.4-pilot เป็นเวอร์ชัน firmware บนบอร์ด** ส่วน BLE Preview
เป็นชื่อโปรแกรมทดลองบน PC ทั้งสองอย่างมีเลขรุ่นแยกกัน

`tools/Create_BLE_Preview_Shortcut_v1.ps1` สร้าง shortcut โดยหาตำแหน่งโครงการ
จากตำแหน่ง script หาก shortcut เดิมถูกต้องจะตรวจสอบและใช้ตัวเดิม หากชี้ผิด
จะสร้างชื่อใหม่และเก็บไฟล์เดิมไว้ ใช้ `-VerifyOnly` เพื่อตรวจโดยไม่เขียนไฟล์

## ใช้กับแล็ปท็อปที่มี BLE ได้ไหม

ใช้งานได้ตามการออกแบบบน Windows ที่รองรับ BLE/GATT central แต่ต้องตรวจจริง
กับ adapter/driver ของแล็ปท็อปนั้น การมี Bluetooth อย่างเดียวไม่รับรองว่ารับ
สี่ Anchors พร้อมกันและ scan ไปด้วยได้ดีเท่ากันทุกเครื่อง
Bleak รองรับ Windows 10 build 16299 ขึ้นไป และระบุว่าจำนวนลิงก์พร้อมกันขึ้นกับ
Bluetooth adapter hardware: [ระบบที่รองรับ](https://bleak.readthedocs.io/en/stable/),
[ข้อจำกัดลิงก์พร้อมกัน](https://bleak.readthedocs.io/en/stable/api/client.html)

ชุด Flash/launcher ปัจจุบันเตรียมและทดสอบบน Windows ยังไม่ได้จัดชุดสำหรับ macOS/Linux
Laptop ใช้ BLE กับ Anchors; ใช้ USB เฉพาะตอน Flash/diagnostic และใช้ Internet
เมื่อส่งขึ้น RTLS ส่วน Tag ส่ง UWB ไป Anchors และไม่ต้องต่อกับ Laptop

### สิ่งที่ต้องเตรียมบนเครื่องใหม่

1. Source จาก branch `standalone-ble-pilot-20261028` บน GitHub
2. Python 3.12 x64 และ environment ที่สร้างใหม่บนแล็ปท็อป ห้ามอาศัยการ copy
   `runtime/python-v1` จากเครื่องพัฒนาแล้วคาดว่าจะ portable เพราะ pyvenv.cfg
   ของเครื่องพัฒนามี path ของ base Python เฉพาะเครื่อง
3. สร้าง runtime ใหม่ที่ `runtime/python-v1` ใน checkout ใหม่ที่ไม่มีโฟลเดอร์นี้
   แล้วติดตั้ง `requirements-ble-pilot.v1.txt` ไลบรารี BLE จะอยู่ใน environment ใหม่นั้น
   และ launcher สามารถ import ได้ แม้ไม่มีโฟลเดอร์ BLE dependencies แยกของเครื่องพัฒนา
4. สำหรับ Flash ให้ copy โฟลเดอร์ `tools/dk6/` และเฉพาะ firmware bundle 1.3.4 ที่ตรวจแล้ว
   จากเครื่องพัฒนาไปยัง relative paths เดิม พร้อม manifest และ images ทั้งหก
   `firmware/releases/_experimental/20261027T224756320889Z/`
5. เตรียม FTDI USB driver ให้ EVK แสดงเป็น COM port และสร้าง shortcut บนแล็ปท็อปใหม่
6. เปิด BLE capture กับหนึ่ง Anchor ก่อน แล้วเพิ่ม Master/Slave และครบสี่ลิงก์
   ย้าย surveyed profile ที่ต้องการใช้และตรวจ site/floor/gateway scope

ตัวอย่างเตรียม environment ใน checkout ใหม่บน Windows ที่ติดตั้ง Python 3.12 แล้ว:

```powershell
py -3.12 -m venv runtime/python-v1
& runtime/python-v1/Scripts/python.exe -m pip install -r requirements-ble-pilot.v1.txt
```

GitHub ไม่มี runtime, SDK, DK6 binaries, firmware binaries, backups หรือ sessions
จึงไม่ใช่ชุดติดตั้ง portable ที่ clone แล้ว Flash ได้ทันที หากบอร์ดถูก Flash ไว้แล้ว
การรับ BLE/คำนวณตำแหน่งไม่ต้องใช้ SDK หรือ compiler บนแล็ปท็อป

## โปรแกรมคำนวณ TDoA อย่างไร

1. **โหลดพิกัดสำรวจ:** X/Y/Z ของ A1–A4 เป็นเมตรในกรอบพิกัดเดียวกัน พร้อม role,
   MAC, RX bias และขอบเขตพื้นที่ 3D Anchor geometry ต้องไม่อยู่ในระนาบเดียวกัน
2. **สร้าง clock model:** Master ส่ง UWB SYNC ที่มี TX timestamp 64-bit Slaves
   รายงาน RX timestamp โปรแกรมใช้ระยะ Master–Slave ชดเชยเวลาคลื่นเดินทาง
   แล้ว fit slope/offset ของนาฬิกาแต่ละ Slave ให้เป็นกรอบเวลาของ Master
   ใช้หน้าต่างสูงสุด 40 samples; ต้องมีอย่างน้อย 6 samples ที่ผ่านเกณฑ์และยังสด
3. **จับคู่ BLINK เดียวกัน:** รับ RX timestamps จากทุก Anchor ตรวจ MAC, status,
   boot epoch และความสด จับคู่จาก corrected RF time ภายใน physical gate
   เวลาที่ข้อมูล BLE มาถึงใช้ตรวจความสดเท่านั้น ไม่ใช้แทนเวลาคลื่น UWB มาถึง
4. **หาความต่างระยะ:** สำหรับ i = A2, A3, A4 เทียบกับ A1:

   `delta_d_i = c * (t_i_corrected - t_A1)`

   โดย c คือความเร็วแสง delta_d เป็นความต่างระยะทาง ไม่ใช่ระยะ Tag–Anchor แต่ละตัว
   Timestamp คงเป็น integer จนหาผลต่างแล้วจึงแปลงเป็นวินาที/เมตร
5. **แก้พิกัด:** หาจุด p = (x,y,z) ที่ทำให้

   `||p - A_i|| - ||p - A1|| = delta_d_i`

   ใช้ bounded nonlinear least squares, Huber loss และ shared-master covariance
   รวม clock residual RMS ใน covariance ตรวจ analytic roots/multiple starts,
   geometry, ambiguity, residual และ uncertainty ก่อนยอมรับ fix

Pure four-anchor mode ไม่ใช้ AoA ช่วยแก้พิกัด แม้ raw observations จะมี azimuth/elevation
อยู่ด้วย Four-anchor TDoA มีเพียงสามสมการอิสระ จึงยังต้องวัด ground truth
และประเมิน clock prediction uncertainty ก่อนอ้างความแม่นยำจริง

## ได้ Output อะไร

| Output | ความหมาย |
| --- | --- |
| `x_m`, `y_m`, `z_m` | พิกัด Tag หน่วยเมตรในกรอบที่สำรวจ ไม่ใช่ GPS; z เป็นความสูงเทียบ origin ของ profile |
| `accuracy_m` | ค่าประมาณ horizontal uncertainty ประมาณ 95% จากแบบจำลอง ไม่ใช่ค่าผิดพลาดที่วัดเทียบ ground truth |
| `z_uncertainty_m` | ค่าประมาณ vertical uncertainty ประมาณ 95% จากแบบจำลอง |
| `residual` | RMS ของความต่างระยะที่โมเดลอธิบายไม่ได้ หน่วยเมตร |
| `normalized_rms` | Residual หลังถ่วงด้วย covariance ใช้ตรวจความสอดคล้อง |
| `num_anchors_used` | จำนวน Anchors ที่ร่วมคำนวณ; โหมดนี้ต้องครบ 4 |
| `time`, `tag_id`, `site_id`, `floor_id` | เวลาอ้างอิงการรับข้อมูลบน PC และตัวระบุ deployment |
| `frame_numbers`, `aoa_anchors_used` | ข้อมูลตรวจย้อนหลัง; AoA list ว่างใน pure TDoA |

แสดง X/Y/Z และสถานะบนหน้าจอ พร้อมบันทึก `data/sessions/ble-pilot-*.jsonl`
ซึ่งมี raw BLE fragments, decoded observations, clock resets, rejections และ accepted fixes
ไฟล์เป็น JSON หนึ่ง record ต่อบรรทัด ไม่ใช่ CSV export อัตโนมัติ

เมื่อเปิด RTLS connector โปรแกรมส่ง accepted fixes ผ่าน Socket.IO namespace `/edge`
event `edge:position` ประกอบด้วย site/floor/tag, x/y/z, accuracy_m,
num_anchors_used, residual, time และ engine_id ซึ่งใน cloud payload เป็น Gateway ID
`z_uncertainty_m` และ `normalized_rms` ยังอยู่ใน local fix/session แต่ไม่ได้อยู่ใน
position payload ปัจจุบัน ต้องมี Gateway ID/token และ scope/พิกัดตรงกับ server

เมื่อ clock ไม่พร้อม, BLINK ไม่ครบ, geometry/uncertainty ไม่ผ่าน หรือคำตอบกำกวม
โปรแกรมไม่สร้าง/ไม่ส่ง accepted position และบันทึกเหตุผลไว้ เมื่ออยู่ใน capture mode
หรือมี Anchor ตัวเดียว จะได้ observations/status ไม่ใช่ตำแหน่ง 3D

## ขอบเขตที่พิสูจน์แล้ว

บนเครื่องพัฒนา: single-anchor RF/BLE จริง, BLE–USB matching 57 records,
native GUI 41 records, Tag MCU-sleep path บน USB และ 84 software tests ผ่าน
ยังไม่ได้พิสูจน์แล็ปท็อปเครื่องอื่น, Master–Slave RF clock, สี่ลิงก์พร้อมกัน,
ความแม่นยำ 3D กับ ground truth, CR2032 จริง หรือ production RTLS ด้วย accepted real fixes
