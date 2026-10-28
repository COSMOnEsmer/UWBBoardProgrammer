# UWB Board Programmer — ready-to-run Windows package

**Current application: 2.1.0, full workspace with USB Flash and Standalone BLE.**

## ภาษาไทย

1. Clone repo นี้ หรือ Pull branch **main** ให้ครบ
2. ดับเบิลคลิก **START_HERE.cmd** ในโฟลเดอร์ repo
3. ครั้งแรก ตัวเปิดจะตรวจ SHA-256 และแตกโปรแกรมให้อัตโนมัติ จากนั้นเปิดหน้าต่างโปรแกรมเต็มรูปแบบ พร้อมสร้าง Shortcut ชื่อ **UWB Board Programmer - GitHub** ที่ Desktop

ไม่ต้องติดตั้ง Python, pip, SDK, compiler หรือคัดลอก firmware จากเครื่องเดิม
ไฟล์ ZIP ประมาณ 95 MB อยู่ใน Git ตามปกติ ไม่ใช้ Git LFS และไม่ต้องดาวน์โหลด runtime เพิ่มเมื่อเปิดโปรแกรม
ถ้าใช้ GitHub Download ZIP ให้ Extract ทั้ง repo ก่อนเปิด START_HERE.cmd

ใช้กับ **Windows 10/11 แบบ 64-bit (x64)** ที่มี .NET Framework 4.8 ซึ่งมากับ Windows รุ่นปัจจุบัน
การรับ BLE/GATT ต้องมี Bluetooth adapter ที่รองรับ BLE พร้อม driver และเปิด Bluetooth ไว้ ส่วนการ Flash ผ่าน USB ต้องมี FTDI driver เพื่อให้บอร์ดปรากฏเป็น COM port (ปกติ Windows Update จัดหาให้)
คอมพิวเตอร์ที่ไม่มี BLE ยังเปิดโปรแกรมและ Flash ผ่าน USB ได้; เพิ่ม USB BLE adapter เมื่อต้องการรับข้อมูลแบบไร้สาย

ในชุดมีโปรแกรม 6 หน้า, ภาษาไทย/อังกฤษ, runtime, DK6 พร้อม DLL, firmware เดิมสำหรับ USB และชุด Standalone BLE สำหรับ A1 Master, A2–A4 Slave, Tag Setup และ Tag Battery
Flash ทีละบอร์ดได้ แล้วนำ Anchors ไปใช้ไฟแยกและรับข้อมูลผ่าน BLE บนแลปทอป
โปรแกรมไม่เริ่ม Flash, รับข้อมูล หรือส่ง RTLS เองทันทีที่เปิด ผู้ใช้ต้องเลือกบอร์ด/โหมด, สำรวจพิกัด Anchors และตั้งค่าบัญชี RTLS บนเครื่องนั้น

เครื่องใหม่จะไม่รับ token, รหัสผ่าน, ข้อมูลสำรองบอร์ด, log หรือผลการวัดจากเครื่องเดิมผ่าน GitHub
ตั้งค่า Site/Floor และเข้าสู่ระบบ RTLS ด้วยบัญชีของคุณบนเครื่องใหม่
การใช้งานต่อหลัง Pull ให้เปิด START_HERE.cmd หรือ Shortcut ชื่อ GitHub นี้; ตัวเปิดจะตรวจชุดที่มากับ repo ก่อนเลือกโปรแกรมให้
ไฟล์ต้นฉบับและ Shortcut รุ่นเก่ายังคงอยู่

โปรแกรมและข้อมูลการใช้งานถูกเก็บภายใน `%LOCALAPPDATA%\UWBBoardProgrammer\Git\<repo-hash>\uwb-2.1.0-<package-hash>\UWB_Board_Programmer_2_1_0\` ในโฟลเดอร์ `config`, `data` และ `verification` และไม่ถูก commit ขึ้น Git โดยแต่ละตำแหน่งที่ Clone จะมีพื้นที่แยกกัน
อย่าลบโฟลเดอร์นี้หากต้องการเก็บข้อมูลเหล่านี้ ให้ใช้ Save/Load Profile ในโปรแกรมเพื่อย้ายการตั้งค่าไปอีกเครื่อง โดยไม่คัดลอก token ที่ผูกกับ Windows เครื่องเดิม
หากไฟล์โปรแกรมใน cache เสีย ตัวเปิดจะสร้างชุดซ่อมในโฟลเดอร์ใหม่และเก็บชุดเดิมไว้ ข้อมูลในชุดเดิมจึงยังอยู่และเปิด Load Profile กลับมาได้

พร้อมใช้งานข้ามเครื่องในที่นี้หมายถึงชุดซอฟต์แวร์ครบและเปิดได้โดยไม่ต้องเตรียม Python ส่วนการยืนยัน clock sync, ตำแหน่ง 3D จาก Anchors จริงครบ 4 ตัว และการส่งผลการวัดจริงเข้า RTLS ยังคงต้องทดสอบกับอุปกรณ์จริง

## English

Clone/pull **main**, then double-click **START_HERE.cmd**. The included launcher verifies and extracts the complete Windows x64 application, starts the full workspace, and creates **UWB Board Programmer - GitHub** on the Desktop. No Python, pip, vendor SDK, compiler, Git LFS or first-run internet download is required.

Windows 10/11 x64 and .NET Framework 4.8 are required. BLE acquisition requires a working BLE adapter/driver with Bluetooth enabled. USB programming requires the EVK's FTDI COM-port driver, normally installed by Windows Update. Hardware drivers and a Bluetooth radio cannot be supplied by the application runtime.

The repository includes runtime libraries, USB programmer/DLLs, legacy USB firmware and Standalone BLE firmware for Master A1, Slaves A2–A4, Tag Setup and Tag Battery. Boards may be flashed one at a time. No board activity or cloud transmission starts automatically.

Credentials, recordings, original-board backups and local profiles are excluded from Git. Configure anchor coordinates and RTLS sign-in on the new machine; use Save/Load Profile to transfer survey settings. Windows-protected tokens must be entered again on a different computer.

The installation and local state are under `%LOCALAPPDATA%\UWBBoardProgrammer\Git\<repo-hash>\uwb-2.1.0-<package-hash>\UWB_Board_Programmer_2_1_0\`. Keep this folder to retain local state. Each clone location has a separate workspace. A damaged installation is preserved and a separate repair installation is created. Use Load Profile to recover settings from the older installation if necessary. Old launchers and source revisions are preserved; use START_HERE or the GitHub shortcut for this distribution.

Actual four-anchor synchronization, 3D RF accuracy and live RTLS delivery still require hardware acceptance testing. A successful portable launch does not certify those measurements.

Developer packaging/verification: [deployment/BUILD_AND_VERIFY.v1.md](deployment/BUILD_AND_VERIFY.v1.md).
