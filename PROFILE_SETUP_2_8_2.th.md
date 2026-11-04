# ใช้งาน Profile บนเครื่องใหม่

Pull หรือ Clone repository ให้ครบ แล้วเปิด START_HERE_2_8_2.cmd ตัว Launcher จะคัดลอกไฟล์ Profile ใน config/profiles ไปยังโฟลเดอร์โปรแกรมและโหลดไฟล์ล่าสุดให้อัตโนมัติ

Profile ที่แชร์จากระบบซึ่งทำงานจริงเมื่อ 4 พฤศจิกายน 2026 คือ config/profiles/technopark-floor-shared-20261104T105535861665Z.json มีพิกัด Floor ที่ Align แล้ว, TP-A1–TP-A4, TP-T1, UWB MAC, Site/Floor ID และข้อมูล Survey/Alignment เดิมครบ

Gateway ID: 5ec624b9-bbee-4846-ae04-2cd116f6964c

กรอก Gateway Token ในหน้า RTLS Platform บนเครื่องใหม่และกด Save encrypted token อีกครั้ง Token ไม่ได้อยู่ใน GitHub และไฟล์ที่เข้ารหัสบนเครื่องเดิมใช้ข้าม Windows user/เครื่องไม่ได้

ปิดการเชื่อมต่อ BLE/RTLS บนเครื่องเดิมก่อนใช้งานเครื่องใหม่ เปิด Bluetooth และจ่ายไฟให้บอร์ด จากนั้น Connect BLE + record → Start positioning → Connect RTLS ไม่ต้อง Pair บอร์ดใน Windows ล่วงหน้าหากโปรแกรมเชื่อมต่อได้ตามปกติ

ถ้าต้องการเลือกไฟล์เอง ให้เปิด Survey & calibration → Load profile แล้วเลือกไฟล์ข้างต้น หากเครื่องที่เคยใช้งานมี Profile ใหม่กว่า Launcher อาจเลือกไฟล์นั้น จึงให้เลือกไฟล์แชร์นี้ด้วยตนเองในกรณีนั้น

Profile นี้ใช้กับตำแหน่งติดตั้ง Anchors และแผนที่ TechnoPark เดิม หากย้าย Anchors ต้องสำรวจและ Align ใหม่ ไม่ควรใช้พิกัดเดิมกับสถานที่ใหม่
