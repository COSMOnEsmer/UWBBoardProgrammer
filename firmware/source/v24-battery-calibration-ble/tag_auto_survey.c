/* BLE-controlled calibration pilot with a finite host-awake control window.
 * Restores autonomous BLINK and requests host sleep after BLE shutdown. */
#include "phUwb_BuildConfig.h"
#include "UwbApi.h"
#include "AppInternal.h"
#include "AppRecovery.h"
#include "app_Ranging_Cfg.h"
#include "uwb_programmer_console.h"
#include "ubp_survey.h"
#include "FreeRTOS.h"
#include "task.h"
#include "ubp_tag_ble.h"
#include "UWBT_PowerMode.h"
#include "PWR_Interface.h"
#include <string.h>

static tUWBAPI_STATUS start_tag(const UbpSurveyCommand *command,uint32_t *session){
    int twr=command->mode>=2;*session=twr?command->session:0x22334455;
    tUWBAPI_STATUS status=UwbApi_SessionInit(*session,UWBD_RANGING_SESSION);
    if(status!=UWBAPI_STATUS_OK)return status;
    if(twr){
        const UWB_AppParams_List_t params[]={
            UWB_SET_APP_PARAM_VALUE(RANGING_ROUND_USAGE,kUWB_RangingRoundUsage_DS_TWR),
            UWB_SET_APP_PARAM_VALUE(RFRAME_CONFIG,kUWB_RfFrameConfig_SP3),
            UWB_SET_APP_PARAM_VALUE(STS_CONFIG,kUWB_StsConfig_StaticSts),
            UWB_SET_APP_PARAM_VALUE(RANGING_INTERVAL,100),UWB_SET_APP_PARAM_VALUE(SLOTS_PER_RR,25),
            UWB_SET_APP_PARAM_VALUE(TX_POWER_ID,30),UWB_SET_APP_PARAM_VALUE(MAX_RR_RETRY,0),
            UWB_SET_APP_PARAM_VALUE(SFD_ID,2),UWB_SET_APP_PARAM_VALUE(CHANNEL_NUMBER,9),
            UWB_SET_APP_PARAM_VALUE(PREAMBLE_CODE_INDEX,10),UWB_SET_APP_PARAM_VALUE(MAC_FCS_TYPE,0),
            UWB_SET_APP_PARAM_VALUE(RNG_DATA_NTF,1),
        };
        status=UwbApi_SetAppConfigMultipleParams(*session,sizeof(params)/sizeof(params[0]),params);
    }else{
        const UWB_AppParams_List_t params[]={
            UWB_SET_APP_PARAM_VALUE(RFRAME_CONFIG,kUWB_RfFrameConfig_Sfd_Sts),
            UWB_SET_APP_PARAM_VALUE(STS_CONFIG,kUWB_StsConfig_StaticSts),
            UWB_SET_APP_PARAM_VALUE(RANGING_ROUND_USAGE,kUWB_RangingMethod_TDoA),
            UWB_SET_APP_PARAM_VALUE(RANGING_INTERVAL,1000),UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_INTERVAL,1000),
            UWB_SET_APP_PARAM_VALUE(RNG_DATA_NTF,0),UWB_SET_APP_PARAM_VALUE(SLOTS_PER_RR,25),
            UWB_SET_APP_PARAM_VALUE(CHANNEL_NUMBER,9),UWB_SET_APP_PARAM_VALUE(PREAMBLE_CODE_INDEX,10),
            UWB_SET_APP_PARAM_VALUE(TX_POWER_ID,30),UWB_SET_APP_PARAM_VALUE(SFD_ID,0),
            UWB_SET_APP_PARAM_VALUE(MAC_FCS_TYPE,0),UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_TIMESTAMP,0),
        };
        status=UwbApi_SetAppConfigMultipleParams(*session,sizeof(params)/sizeof(params[0]),params);
    }
    phRangingParams_t params;memset(&params,0,sizeof(params));params.noOfControlees=1;
    params.deviceRole=twr?(command->mode==3?kUWB_DeviceRole_Initiator:kUWB_DeviceRole_Responder):kUWB_DeviceRole_UT_Tag;
    params.multiNodeMode=twr?kUWB_MultiNodeMode_UniCast:kUWB_MultiNodeMode_OnetoMany;
    params.macAddrMode=twr?SHORT_MAC_ADDRESS_MODE:EXTENDED_MAC_ADDRESS_MODE_WITH_HEADER;
    params.deviceType=twr?(command->mode==3?kUWB_DeviceType_Controller:kUWB_DeviceType_Controlee):kUWB_DeviceType_Controller;
    memcpy(params.deviceMacAddr,gUbpConfig.mac,8);
    if(twr){memset(params.deviceMacAddr,0,8);memcpy(params.deviceMacAddr,gUbpConfig.mac+6,2);memcpy(params.dstMacAddr,command->peer+6,2);}
    if(status==UWBAPI_STATUS_OK)status=UwbApi_SetRangingParams(*session,&params);
    if(status==UWBAPI_STATUS_OK)status=UwbApi_StartRangingSession(*session);
    if(status!=UWBAPI_STATUS_OK){UwbApi_SessionDeinit(*session);*session=0;}
    return status;
}
OSAL_TASK_RETURN_TYPE StandaloneTask(void *unused){
    (void)unused;UbpConsoleInit();
    extern uint8_t ucHeap[configTOTAL_HEAP_SIZE];
    PWR_Init();PWR_vAddRamRetention((uint32_t)&ucHeap[0],sizeof(ucHeap));
    UWBT_PowerModeEnter(UWBT_RUN_MODE);
    UbpTagBleStart();
    for(unsigned i=0;i<1500 && !UbpTagBleReady();i++)phOsalUwb_Delay(10);
    if(!UbpTagBleReady()){UbpState("ble_init_failed",-1);UbpTagBleClose();}
    if(!gUbpConfigReady){for(;;){UbpPoll();phOsalUwb_Delay(10);}}
    tUWBAPI_STATUS status=UwbApi_Init(UbpCallback);
    if(status!=UWBAPI_STATUS_OK){UbpState("radio_init_failed",status);goto fail;}
    status=RadioConfigFull_GroupDelay(FALSE);
    if(status!=UWBAPI_STATUS_OK){UbpState("radio_config_failed",status);goto fail;}
    status=demo_sr040_swup_update_safe();
    if(status!=UWBAPI_STATUS_OK){UbpState("radio_update_failed",status);goto fail;}
    UwbApi_SessionNvmManage(SESSION_NVM_MANAGE_DELETE_ALL,0);
    uint32_t session=0;UbpSurveyCommand current;memset(&current,0,sizeof(current));
    status=start_tag(&current,&session);UbpState(status==UWBAPI_STATUS_OK?"running":"start_failed",status);
    UbpTagBleAdvertise();int closing=0;
    for(;;){
        if(!closing && !UbpTagBleWindowRemaining()){closing=1;UbpTagBleClose();UbpSurveyDisconnect();}
        int legacy=UbpPoll();UbpSurveyCommand command;int have=UbpSurveyTake(&command);
        if(!have && (UbpSurveyExpired() || legacy)){memset(&command,0,sizeof(command));command.request=current.request?current.request:1;command.mode=legacy==2?1:0;command.lease_ms=legacy==2?30000:0;command.received_tick=xTaskGetTickCount();have=1;}
        if(have){
            if(session){UwbApi_StopRangingSession(session);UwbApi_SessionDeinit(session);session=0;}
            status=command.mode==1?UWBAPI_STATUS_OK:start_tag(&command,&session);
            if(status!=UWBAPI_STATUS_OK){uint16_t error=status;command.mode=0;command.session=0;start_tag(&command,&session);status=error;}
            current=command;UbpSurveyResult(&command,status,session);UbpState(command.mode==0?"running":command.mode==1?"survey_hold":"survey_twr",status);
        }
        if(closing && current.mode==0 && UbpTagBleClosed()){
            UbpState("battery_sleep",0);phOsalUwb_Delay(100);
            PWR_ChangeDeepSleepMode(cPWR_PowerDown_RamOffOsc32kOff);
            UWBT_PowerModeEnter(UWBT_POWER_DOWN_MODE);vTaskSuspend(NULL);
        }
        phOsalUwb_Delay(10);
    }
fail:for(;;){UbpPoll();phOsalUwb_Delay(100);}
}
UWBOSAL_TASK_HANDLE uwb_demo_start(void){
    phOsalUwb_ThreadCreationParams_t params;UWBOSAL_TASK_HANDLE task;memset(&params,0,sizeof(params));params.stackdepth=2048;params.priority=4;PHOSALUWB_SET_TASKNAME(params,"UbpTagSurvey");
    if(phOsalUwb_Thread_Create((void**)&task,&StandaloneTask,&params)!=0)return 0;return task;
}
