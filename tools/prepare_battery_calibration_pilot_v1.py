"""Create a new, experimental BLE-controlled Tag source/build; no original edits."""
from pathlib import Path
import re
import shutil
ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    target=ROOT/'firmware/source/v24-battery-calibration-ble'
    if target.exists():raise FileExistsError(target)
    target.mkdir()
    for source in (ROOT/'firmware/source/v23-auto-survey-tag').iterdir():
        if source.suffix in ('.h','.c'):shutil.copy2(source,target/source.name)
    console=target/'uwb_programmer_console.c'
    text=console.read_text().replace('1.4.2-pilot','1.5.0-pilot')
    begin=text.index('unsigned UbpInfoJson(');end=text.index('static void hello(',begin)
    info=r'''unsigned UbpInfoJson(char *out,unsigned size) {
    char mac[17];hex_mac(mac,gUbpConfig.mac,8);
    return snprintf(out,size,"{\"v\":1,\"model\":\"%s\",\"role\":\"%s\",\"mac\":\"%s\",\"boot\":\"%08lx\",\"sequence\":%lu,\"firmware\":\"1.5.0-pilot\",\"autonomous\":true,\"radio_state\":\"%s\",\"interval_ms\":%lu,\"config_crc\":\"%08lx\",\"provisioned\":%s,\"survey\":1,\"battery_calibration\":true,\"ble_window_s\":900,\"battery_runtime_validated\":false}",gModel,gRole,mac,gBoot,(unsigned long)gSequence,gRunState,(unsigned long)gUbpConfig.interval_ms,(unsigned long)gProvisionCrc,gUbpConfigReady?"true":"false");
}
'''
    text=text[:begin]+info+text[end:]
    console.write_text(text,encoding='utf8')
    tag=target/'tag_auto_survey.c';text=tag.read_text()
    text=text.replace('#include "task.h"','#include "task.h"\n#include "ubp_tag_ble.h"\n#include "UWBT_PowerMode.h"\n#include "PWR_Interface.h"')
    text=text.replace('    (void)unused;UbpConsoleInit();','    (void)unused;UbpConsoleInit();\n    extern uint8_t ucHeap[configTOTAL_HEAP_SIZE];\n    PWR_Init();PWR_vAddRamRetention((uint32_t)&ucHeap[0],sizeof(ucHeap));\n    UWBT_PowerModeEnter(UWBT_RUN_MODE);')
    text=text.replace('    for(;;){\n        int legacy=UbpPoll();','    UbpTagBleStart();TickType_t window_start=xTaskGetTickCount();int closing=0;\n    for(;;){\n        if(!closing && (TickType_t)(xTaskGetTickCount()-window_start)>=pdMS_TO_TICKS(900000)){closing=1;UbpTagBleClose();UbpSurveyDisconnect();}\n        int legacy=UbpPoll();')
    text=text.replace('        phOsalUwb_Delay(10);\n    }','        if(closing && current.mode==0 && UbpTagBleClosed()){\n            UbpState("battery_sleep",0);phOsalUwb_Delay(100);\n            PWR_ChangeDeepSleepMode(cPWR_PowerDown_RamOffOsc32kOff);\n            UWBT_PowerModeEnter(UWBT_POWER_DOWN_MODE);vTaskSuspend(NULL);\n        }\n        phOsalUwb_Delay(10);\n    }')
    tag.write_text(text,encoding='utf8')
    value=(ROOT/'tools/build_firmware_auto_survey_v4.py').read_text()
    value=value.replace('v23-auto-survey-tag','v24-battery-calibration-ble').replace('1.4.2-pilot','1.5.0-pilot')
    value=value.replace("if role=='tag_setup':text=", "if role=='tag_ble_calibration':text=")
    begin=value.index("        if role=='tag_battery':\n            pre=")
    end=value.index('\n    else:\n        folder=',begin)
    value=value[:begin]+'''        pre=host/'app_preinclude.h';derived(pre,re.sub(r'(#define USE_SHELF_MODE\\s+)0',r'\\g<1>1',pre.read_text(encoding='utf-8')))
'''+value[end:]
    # The Finder SDK already contains the QN9090 BLE host/controller sources.
    marker="    proot=ET.parse(project/'.project').getroot();links={}"
    additions='''    if tag:
        common_ble=work/'ext/boards/qn9090/bluetooth/bluetooth/common'
        derived(common_ble/'gatt_db.h',(ROOT/'firmware/source/v24-battery-calibration-ble/gatt_db_ubp.h').read_text())
        derived(common_ble/'gatt_uuid128.h',(ROOT/'firmware/source/v24-battery-calibration-ble/gatt_uuid_ubp.h').read_text())
        database=work/'demos/SR040/demo_nearby_interaction/src/gatt_database.c'
        text=database.read_text().replace('#ifdef UWBIOT_APP_BUILD__DEMO_NEARBY_INTERACTION','#if 1').replace('gatt_alloc_x_uwb_ble_sr040.h','gatt_alloc_x.h')
        begin=text.index('    /* Update char_qpps_rx');end=text.index('#if (!gGattDbDynamic_d',begin)
        derived(database,text[:begin]+text[end:])
        for filename in ('ubp_tag_ble.c','ubp_tag_ble.h'):derived(host/filename,(ROOT/'firmware/source/v24-battery-calibration-ble'/filename).read_text())
'''
    value=value.replace(marker,additions+marker)
    value=value.replace("            if not tag and path.name=='private_profile_service.c':continue", "            if path.name=='private_profile_service.c':continue\n            if tag and path==work/'demos/SR040/demo_ultdoa_tag_sr040/app_config.c':continue")
    value=value.replace("    objects=[]; object_dir=", "    if tag:sources[host/'ubp_tag_ble.c']='boards/Host/FinderV3/ubp_tag_ble.c'\n    objects=[]; object_dir=")
    value=value.replace("    entry['auto_survey']=(not tag or role=='tag_setup')", "    entry.update(auto_survey=True,battery_calibration=True,battery_runtime_validated=False,eligible_for_default_bundle=False,ble_window_s=900)")
    value=value.replace("choices=['master','slave2','slave3','slave4','tag_setup','tag_battery'],default=['master','slave2','slave3','slave4','tag_setup','tag_battery']", "choices=['tag_ble_calibration'],default=['tag_ble_calibration']")
    with (ROOT/'tools/build_firmware_battery_calibration_v1.py').open('x',encoding='utf8') as output:output.write(value)
    print('Created experimental v24 sources and battery BLE build tool; no firmware was flashed.')
