"""Reproducible build in a NEW SDK copy per image; never builds in vendor/originals."""
from pathlib import Path
import struct, zlib
import argparse, concurrent.futures, fnmatch, hashlib, json, os, re, shutil, subprocess, sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
ROOT=Path(__file__).resolve().parents[1]
STAMP=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
GCC_BIN=next((ROOT/'tools/arm-gcc-10.3-2021.10').rglob('arm-none-eabi-gcc.exe')).parent
ENV=dict(os.environ,PATH=str(GCC_BIN)+os.pathsep+os.environ.get('PATH',''))

def run(args,cwd,log):
    if sum(len(str(a)) for a in args)>20000:
        response=Path(cwd)/'link-response.txt'
        with response.open('x',encoding='utf-8') as f:f.write('\n'.join(chr(34)+str(a).replace(chr(92),'/')+chr(34) for a in args[1:]))
        args=[args[0],'@'+str(response)]
    p=subprocess.run([str(a) for a in args],cwd=cwd,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
    log.write(p.stdout);log.flush()
    if p.returncode: raise RuntimeError('Command failed: '+str(args[0])+'\n'+p.stdout[-5000:])
    return p.stdout

def derived(path,text):
    # Target is in a fresh work directory; preserve the unmodified copied file too.
    if path.exists():
        baseline=path.with_name(path.name+'.vendor-original')
        if baseline.exists(): raise FileExistsError(baseline)
        path.rename(baseline)
    with path.open('x',encoding='utf-8',newline='\n') as out:out.write(text)

def resolve(value,project,build,links):
    value=value.strip('"').replace('${ProjDirPath}',str(project)).replace('${ProjName}',project.name)
    m=re.match(r'^\$\{workspace_loc:/[^/]+/(.*)\}$',value)
    if m:
        name=m.group(1)
        for key,target in sorted(links.items(),key=lambda x:-len(x[0])):
            if name==key or name.startswith(key+'/'):return str(target/name[len(key):].lstrip('/'))
        return str(project/name)
    return str((build/value).resolve()) if not Path(value).is_absolute() else value

def build(role):
    tag=role.startswith('tag'); module='sr040' if tag else 'sr150'; board='FinderV3' if tag else 'Rhodes4'
    work=ROOT/'firmware/work'/f'{role}-{hashlib.sha1(STAMP.encode()).hexdigest()[:8]}'/'uwbiot-top'
    if work.exists():raise FileExistsError(work)
    shutil.copytree(ROOT/f'vendor/originals/{module}/uwbiot-top',work)
    release=ROOT/'firmware/releases/_experimental'/STAMP/role;release.mkdir(parents=True)
    log=(release/'build.log').open('x',encoding='utf-8')
    patch=ROOT/('vendor/patches/2dk_prebuilt_v04.03.14.patch' if tag else 'vendor/patches/2bp_prebuilt_v04.06.05.patch')
    run(['git','apply','-p0','--check',patch],work,log)
    run(['git','apply','-p0',patch],work,log)
    pname='FinderV3' if tag else 'RhodesV4_SE';project=work/'project'/pname;build_dir=project/'ubp-build';build_dir.mkdir()
    select=project/'UWBIOT_APP_BUILD.h';text=select.read_text(encoding='utf-8')
    text=re.sub(r'^\s*#define (UWBIOT_APP_BUILD__\w+)\s*$',r'// #define \1',text,flags=re.M)
    demo='DEMO_ULTDOA_TAG' if tag else ('DEMO_ULTDOA_SYNC_ANCHOR' if role=='master' else 'DEMO_ULTDOA_ANCHOR')
    text=text.replace('// #define UWBIOT_APP_BUILD__'+demo,'#define UWBIOT_APP_BUILD__'+demo)
    derived(select,text)
    host=work/'boards/Host'/board
    for filename in ['uwb_programmer_console.h','uwb_programmer_console.c']:
        derived(host/filename,(ROOT/'firmware/source/v20-paced-telemetry-pilot'/filename).read_text(encoding='utf-8'))
    if tag:
        source=work/'demos/SR040/demo_ultdoa_tag_sr040/demo_ultdoa_sr040.c';text=source.read_text(encoding='utf-8')
        text=text.replace('#include "phUwb_BuildConfig.h"','#include "phUwb_BuildConfig.h"\n#include "uwb_programmer_console.h"\n#include "UWBT_PowerMode.h"\n#include "PWR_Interface.h"\n#include "task.h"')
        text=re.sub(r'#define MAC_ADDR_MODE\s+SHORT_MAC_ADDRESS_MODE','#define MAC_ADDR_MODE EXTENDED_MAC_ADDRESS_MODE_WITH_HEADER',text)
        text=text.replace('tUWBAPI_STATUS status = UWBAPI_STATUS_FAILED;','UbpConsoleInit();\n    if(!gUbpConfigReady){for(;;){UbpPoll();phOsalUwb_Delay(10);}}\n    tUWBAPI_STATUS status = UWBAPI_STATUS_FAILED;')
        text=text.replace('UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_INTERVAL, 10)','UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_INTERVAL, gUbpConfig.interval_ms)')
        text=text.replace('UWB_SET_APP_PARAM_VALUE(RANGING_INTERVAL, 1 * 1000)','UWB_SET_APP_PARAM_VALUE(RANGING_INTERVAL, gUbpConfig.interval_ms)')
        text=re.sub(r'(#define DEMO_ULTDOA_SR040_TASK_SIZE\s+)\d+',r'\g<1>2048',text)
        text=text.replace('#define DEMO_ULTDOA_SR040_TASK_SIZE 400','#define DEMO_ULTDOA_SR040_TASK_SIZE 2048')
        text=text.replace('UwbApi_Init(AppCallback)','UwbApi_Init(UbpCallback)')
        start=text.index('    /*Get Then Mac Address from TRNG*/');end=text.index('    inRangingParams.deviceRole',start)
        text=text[:start]+'    memset(&inRangingParams,0,sizeof(inRangingParams));\n    memcpy(inRangingParams.deviceMacAddr,gUbpConfig.mac,8);\n\n'+text[end:]
        start=text.index('#define SLEEP_DURATION_MS');end=text.index('\nexit:',start)
        battery='''
    UbpState("running",0);
#if UWB_PROGRAMMER_BATTERY
    /* Short USB diagnostic window, then MCU sleeps while SR040 continues BLINK. */
    for(unsigned i=0;i<1000;i++){UbpPoll();phOsalUwb_Delay(5);}
    UbpState("battery_sleep",0);phOsalUwb_Delay(100);
    PWR_ChangeDeepSleepMode(cPWR_PowerDown_RamOffOsc32kOff);
    UWBT_PowerModeEnter(UWBT_POWER_DOWN_MODE);
    vTaskSuspend(NULL);
#else
    for(;;){UbpPoll();phOsalUwb_Delay(5);}
#endif
'''
        text=text[:start]+battery+text[end:];derived(source,text)
        if role=='tag_battery':
            pre=host/'app_preinclude.h';derived(pre,re.sub(r'(#define USE_SHELF_MODE\s+)0',r'\g<1>1',pre.read_text(encoding='utf-8')))
    else:
        folder='demo_ultdoa_sync_anchor' if role=='master' else 'demo_ultdoa_anchor'
        source=work/'demos/SR1XX'/folder/(folder+'.c')
        text=(ROOT/'firmware/source/v20-paced-telemetry-pilot/anchor_task.c').read_text(encoding='utf-8')
        marker='        phRangingParams_t ranging;'
        text=text.replace(marker,'''
        uint8_t rx_ant[]={kUWBAntCfgRxMode_AoA_Mode,0x02,1,2};
        const UWB_VendorAppParams_List_t vendor[]={
            UWB_SET_VENDOR_APP_PARAM_VALUE(TX_ADAPTIVE_PAYLOAD_POWER,1),
            UWB_SET_VENDOR_APP_PARAM_ARRAY(ANTENNAE_CONFIGURATION_RX,rx_ant,sizeof(rx_ant)),
        };
        if(status==UWBAPI_STATUS_OK) status=UwbApi_SetVendorAppConfigs(handle,sizeof(vendor)/sizeof(vendor[0]),vendor);
'''+marker)
        derived(source,text)
    if not tag:
        # Configure only this fresh SDK copy; the vendor input remains untouched.
        common_ble=work/'ext/boards/qn9090/bluetooth/bluetooth/common'
        derived(common_ble/'gatt_db.h',(ROOT/'firmware/source/v20-paced-telemetry-pilot/gatt_db_ubp.h').read_text())
        derived(common_ble/'gatt_uuid128.h',(ROOT/'firmware/source/v20-paced-telemetry-pilot/gatt_uuid_ubp.h').read_text())
        database=work/'demos/SR1XX/demo_nearby_interaction/src/gatt_database.c'
        text=database.read_text().replace('#ifdef UWBIOT_APP_BUILD__DEMO_NEARBY_INTERACTION','#if 1')
        text=text.replace('gatt_alloc_x_uwb_ble.h','gatt_alloc_x.h')
        begin=text.index('    /* Update char_qpps_rx');end=text.index('#if (!gGattDbDynamic_d',begin)
        text=text[:begin]+text[end:]
        derived(database,text)
        for filename in ['ubp_ble.h','ubp_ble.c','ubp_newlib.c']:
            derived(host/filename,(ROOT/'firmware/source/v20-paced-telemetry-pilot'/filename).read_text())
        preinclude=host/'app_preinclude.h';text=preinclude.read_text()
        text=re.sub(r'(#define gAppConnectableAdv_d\s+)0',r'\g<1>1',text)
        text=re.sub(r'(#define gAppMaxConnections_c\s+)5',r'\g<1>1',text)
        # Keep the powered anchor awake until RF/BLE operation is validated.
        text=re.sub(r'(#define (?:cPWR_UsePowerDownMode|cPWR_FullPowerDownMode|mAppUseTickLessMode_c)\s+)1',r'\g<1>0',text)
        derived(preinclude,text)
        sizes=work/'libs/halimpl/inc/UwbCoreSDK_Internal.h'
        text=sizes.read_text(encoding='utf8')
        text=re.sub(r'(#define (?:CLIENT_STACK_SIZE|TMLREADER_STACK_SIZE)\s+)\d+',r'\g<1>1024',text)
        derived(sizes,text)
        fc=host/'FreeRTOSConfig.h'
        text=fc.read_text(encoding='utf8')
        text=text.replace('(45 * 1024)','(60 * 1024)')
        pos=text.rfind('#endif')
        text=text[:pos]+'\nextern void UbpAssert(const char *, unsigned);\n#undef configASSERT\n#define configASSERT(x) do { if(!(x)) UbpAssert(__FILE__,__LINE__); } while(0)\n'+text[pos:]
        derived(fc,text)
        for hook in (work/'ext/freertos/hooks/FreeRTOS_Hooks.c',work/'boards/Rhodes4_SPI/FreeRTOSConfig.c'):
            text=hook.read_text(encoding='utf8')
            text=text.replace('while(1);','UbpAssert("malloc_failed",0);')
            text=text.replace('for (;;)\n        ;','UbpAssert((const char *)pcTaskName,0);')
            derived(hook,text)
        derived(host/'ubp_fault.c',(ROOT/'firmware/source/v20-paced-telemetry-pilot/ubp_fault.c').read_text())
    if tag:
        sizes=work/'libs/halimpl/inc/UwbCoreSDK_Internal.h';text=sizes.read_text(encoding='utf8')
        text=re.sub(r'(#define (?:CLIENT_STACK_SIZE|TMLREADER_STACK_SIZE)\s+)\d+',r'\g<1>1024',text);derived(sizes,text)
        derived(host/'ubp_newlib.c',(ROOT/'firmware/source/v20-paced-telemetry-pilot/ubp_newlib.c').read_text())
        derived(host/'ubp_fault.c',(ROOT/'firmware/source/v20-paced-telemetry-pilot/ubp_fault.c').read_text())
        fc=host/'FreeRTOSConfig.h';text=fc.read_text().replace('(30 * 1024)','(60 * 1024)')
        pos=text.rfind('#endif')
        text=text[:pos]+'\nextern void UbpAssert(const char *, unsigned);\n#undef configASSERT\n#define configASSERT(x) do { if(!(x)) UbpAssert(__FILE__,__LINE__); } while(0)\n'+text[pos:]
        derived(fc,text)
        for hook in (work/'ext/freertos/hooks/FreeRTOS_Hooks.c',work/'boards/FinderV3_SPI/FreeRTOSConfig.c'):
            text=hook.read_text()
            text=text.replace('while(1);','UbpAssert("malloc_failed",0);')
            text=text.replace('for (;;)\n        ;','UbpAssert((const char *)pcTaskName,0);')
            derived(hook,text)
    if tag:
        actual_hook=work/'ext/boards/qn9090/bluetooth/framework/OSAbstraction/source/fsl_os_abstraction_free_rtos.c'
        text=actual_hook.read_text().replace('panic(0,(uint32_t)vApplicationMallocFailedHook,0,0);','UbpAssert("malloc_failed",0);')
        derived(actual_hook,text)
    proot=ET.parse(project/'.project').getroot();links={}
    for link in proot.findall('./linkedResources/link'):
        name,location=link.findtext('name'),link.findtext('locationURI','')
        if location.startswith('PARENT-2-PROJECT_LOC/'):links[name]=work/location.split('/',1)[1]
        elif location.startswith('PROJECT_LOC/'):links[name]=project/location.split('/',1)[1]
    cfg=ET.parse(project/'.cproject').getroot().find('.//configuration')
    compiler=next(t for t in cfg.findall('.//tool') if t.get('name')=='MCU C Compiler')
    options={o.get('name'):o for o in compiler.findall('option')}
    defs=[v.get('value').replace('\\"','"') for v in options['Defined symbols (-D)'].findall('listOptionValue')]
    includes=[resolve(v.get('value'),project,build_dir,links) for v in options['Include paths (-I)'].findall('listOptionValue')]
    lists=host/'ubp-lists';lists.mkdir()
    for name in ['fsl_component_generic_list.h','fsl_component_generic_list.c']:
        shutil.copy2(ROOT/'vendor/originals/qn9090-sdk/components/lists'/name,lists/name)
    derived(lists/'generic_list.h','#include "fsl_component_generic_list.h"\n')
    includes.extend([str(project),str(host),str(lists)])
    linker_file=work/'boards'/('FinderV3_SPI' if tag else 'Rhodes4_SPI')/'QN9090_UWB_TAG_FW.ld'
    derived(linker_file,linker_file.read_text().replace('"libcr_newlib_nohost.a"','"libnosys.a"').replace('GROUP(libcr_nohost.a libcr_c.a libcr_eabihelpers.a)','GROUP(libnosys.a libc_nano.a libgcc.a)'))
    slot=1 if role=='master' or tag else int(role[-1])
    defs.append('UBP_BOARD_SLOT='+str(slot))
    defs.extend(['UWB_PROGRAMMER_TAG='+str(int(tag)),'UWB_PROGRAMMER_MASTER='+str(int(role=='master')),'UWB_PROGRAMMER_BATTERY='+str(int(role=='tag_battery')),'SDK_COMPONENT_DEPENDENCY_FSL_COMMON=0','PRINTF_FLOAT_ENABLE=1','PRINTF_ADVANCED_ENABLE=1','DEBUG_CONSOLE_PRINTF_MAX_LOG_LEN=1024','DEBUG_CONSOLE_TRANSMIT_BUFFER_LEN=2048','DEBUG_CONSOLE_RECEIVE_BUFFER_LEN=512','DEBUG_CONSOLE_TRANSFER_NON_BLOCKING','DEBUG_CONSOLE_RX_ENABLE=1','DEBUG_CONSOLE_ENABLE_ECHO_FUNCTION=0'])
    pre=host/'app_preinclude.h'
    common=['-mcpu=cortex-m4','-mthumb','-Os','-g','-fno-common','-ffunction-sections','-fdata-sections','-ffreestanding','-fno-builtin','-specs=nano.specs','-include',str(pre)]
    common+=['-D'+d for d in defs]+['-I'+p for p in includes]
    excludes=cfg.find('.//sourceEntries/entry').get('excluding','').split('|')
    sources={}
    def excluded(name):return any(name==e or name.startswith(e+'/') or fnmatch.fnmatch(name,e) for e in excludes if e)
    for logical,target in links.items():
        paths=[target] if target.is_file() else list(target.rglob('*'))
        for path in paths:
            if path.suffix not in ('.c','.cpp','.S','.s'):continue
            if not tag and path.name=='private_profile_service.c':continue
            name=logical if target.is_file() else logical+'/'+path.relative_to(target).as_posix()
            if not excluded(name):sources[path]=name
    sources[lists/'fsl_component_generic_list.c']='ubp-lists/fsl_component_generic_list.c'
    sources[host/'uwb_programmer_console.c']='boards/Host/'+board+'/uwb_programmer_console.c'
    if not tag:
        sources[host/'ubp_fault.c']='boards/Host/Rhodes4/ubp_fault.c'
        sources[host/'ubp_ble.c']='boards/Host/Rhodes4/ubp_ble.c'
        sources[host/'ubp_newlib.c']='boards/Host/Rhodes4/ubp_newlib.c'
    if tag:
        sources[host/'ubp_newlib.c']='boards/Host/'+board+'/ubp_newlib.c'
        sources[host/'ubp_fault.c']='boards/Host/'+board+'/ubp_fault.c'
    objects=[]; object_dir=build_dir/'obj';object_dir.mkdir()
    def compile_one(item):
        source,name=item;obj=object_dir/(hashlib.sha1(name.encode()).hexdigest()[:12]+'.o')
        command=[GCC_BIN/('arm-none-eabi-g++.exe' if source.suffix=='.cpp' else 'arm-none-eabi-gcc.exe'),*common,'-c',source,'-o',obj]
        if source.name=='fsl_component_generic_list.c':command.extend(['-include','fsl_common.h'])
        if source.name=='startup_qn9090.c':command.extend(['-U__MCUXPRESSO'])
        if source.suffix in ('.S','.s'):command[1:1]=['-x','assembler-with-cpp']
        if source.suffix=='.cpp':command.extend(['-fno-exceptions','-fno-rtti'])
        proc=subprocess.run([str(a) for a in command],cwd=build_dir,env=ENV,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace')
        return obj,proc.returncode,proc.stdout,name
    print(role+': compiling '+str(len(sources))+' sources',flush=True)
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        for obj,code,output,name in executor.map(compile_one,sources.items()):
            log.write(name+'\n'+output);objects.append(obj)
            if code:errors.append((name,output))
    if errors:raise RuntimeError('Compilation errors '+str(len(errors))+':\n'+'\n'.join(n+'\n'+s[-3000:] for n,s in errors[:5]))
    linker=next(t for t in cfg.findall('.//tool') if t.get('name')=='MCU C++ Linker')
    loptions={o.get('name'):o for o in linker.findall('option')}
    libs=[v.get('value') for v in loptions['Libraries (-l)'].findall('listOptionValue')]
    elf=release/(role+'.axf')
    args=[GCC_BIN/'arm-none-eabi-gcc.exe','-mcpu=cortex-m4','-mthumb','-nostdlib','-specs=nano.specs','-Wl,--gc-sections','-Wl,--no-wchar-size-warning','-Wl,--defsym=__ram_vector_table__=1','-Wl,--defsym=gUseNVMLink_d=1','-Wl,--defsym=__app_load_address__=0','-Wl,--defsym=__app_stated_size__='+'0x90000','-Wl,--defsym=__stack_size__=0x800','-Wl,--defsym=__heap_size__=0x2000','-Wl,-Map='+str(release/(role+'.map')),'-L'+str(work/'boards'/('FinderV3_SPI' if tag else 'Rhodes4_SPI')),'-L'+str(work/'ext/boards/qn9090/bluetooth/libs'),'-T','QN9090_UWB_TAG_FW.ld','-o',elf,*objects,'-Wl,--start-group',*['-l'+l for l in libs],'-lc_nano','-lm','-lgcc','-lnosys','-Wl,--end-group']
    run(args,build_dir,log)
    run([sys.executable,work/'scripts/dk6_image_tool.py',elf.name],release,log)
    binary=release/f'murata_{"2dk" if tag else "2bp"}_{role}_ble_pilot_v1.bin'
    run([GCC_BIN/'arm-none-eabi-objcopy.exe','-O','binary',elf,binary],build_dir,log)
    size=run([GCC_BIN/'arm-none-eabi-size.exe',elf],build_dir,log);log.close()
    entry={'image_label':role,'anchor_slot':('A'+str(slot)) if not tag else 'Tag','provisioned_mac':'0200000000000101' if tag else ('020000000000000'+str(slot)),'role':('master' if role=='master' else 'slave') if not tag else role,'config_record':'0xE2E3','model':'Type2DK' if tag else 'Type2BP','version':'1.3.4-pilot','file':str(binary.relative_to(ROOT)),'sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'bytes':binary.stat().st_size,'sdk':'04.03.14' if tag else '04.06.05','baud':3000000,'minimum_evk_revision':3,'hardware_validated':False,'calibration':'Murata matching patch; SR040 vendor radio settings' if tag else 'Murata matching patch + explicit OTP for SR150','source_work':str(work.relative_to(ROOT)),'size_output':size}
    entry['interval_ms']=1000 if tag else 500
    entry['config_crc']=f"{zlib.crc32(struct.pack('<I8sII',0xE2E11001,bytes.fromhex(entry['provisioned_mac']),entry['interval_ms'],2 if tag else (1 if role=='master' else 0)))&0xffffffff:08x}"
    if entry['bytes']>0x90000:raise RuntimeError('Application exceeds its stated image allocation')
    with (release/'image-manifest.json').open('x',encoding='utf-8') as out:json.dump(entry,out,indent=2)
    print('BUILT '+str(binary),flush=True);return entry

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--roles',nargs='+',choices=['master','slave2','slave3','slave4','tag_setup','tag_battery'],default=['master','slave2','slave3','slave4','tag_setup','tag_battery']);args=parser.parse_args()
    entries=[]
    for role in args.roles:entries.append(build(role))
    destination=ROOT/'firmware/releases/_experimental'/STAMP/'bundle-manifest.json'
    with destination.open('x',encoding='utf-8') as out:json.dump({'schema':1,'created_utc':STAMP,'images':entries},out,indent=2)
    print('BUNDLE '+str(destination),flush=True)
