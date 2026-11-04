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
#include "fsl_debug_console.h"
#include <string.h>

static uint8_t radio_stage,last_api,last_rf=0xff;
static uint32_t hpd_recoveries,good_ranges,failed_ranges;
static void stage(uint8_t value,tUWBAPI_STATUS status){
    taskENTER_CRITICAL();radio_stage=value;last_api=(uint8_t)status;taskEXIT_CRITICAL();
    PRINTF("{\"v\":1,\"kind\":\"tag_radio\",\"stage\":%u,\"status\":%u}\r\n",value,status);
}
void UbpTagRadioMeasurement(uint8_t status){
    taskENTER_CRITICAL();last_rf=status;if(status==0)good_ranges++;else failed_ranges++;taskEXIT_CRITICAL();
}
void UbpTagRadioDiagnostic(uint8_t out[20]){
    uint32_t words[3];taskENTER_CRITICAL();out[0]=1;out[1]=radio_stage;out[2]=last_api;out[3]=last_rf;
    words[0]=hpd_recoveries;words[1]=good_ranges;words[2]=failed_ranges;taskEXIT_CRITICAL();
    for(unsigned j=0;j<3;j++)for(unsigned i=0;i<4;i++)out[4+j*4+i]=(uint8_t)(words[j]>>(8*i));
    uint32_t crc=0xffffffff;for(unsigned i=0;i<16;i++){crc^=out[i];for(unsigned j=0;j<8;j++)crc=(crc>>1)^((0-(crc&1))&0xedb88320);}
    crc=~crc;for(unsigned i=0;i<4;i++)out[16+i]=(uint8_t)(crc>>(8*i));
}
static tUWBAPI_STATUS recover_hpd(void){
    /* Same core-config restoration required by the SDK's BLE NI example.
     * Do not treat 0xFC as success, or change the current-limiter settings. */
    hpd_recoveries++;tUWBAPI_STATUS status=UwbApi_SetDefaultCoreConfigs();stage(7,status);return status;
}
static tUWBAPI_STATUS stop_tag(uint32_t *session){
    if(!*session)return UWBAPI_STATUS_OK;
    tUWBAPI_STATUS status=UwbApi_StopRangingSession(*session);stage(1,status);
    if(status==UWBAPI_STATUS_HPD_WAKEUP){*session=0;return recover_hpd();}
    if(status!=UWBAPI_STATUS_OK && status!=UWBAPI_STATUS_SESSION_NOT_EXIST)return status;
    status=UwbApi_SessionDeinit(*session);stage(2,status);
    if(status==UWBAPI_STATUS_HPD_WAKEUP){*session=0;return recover_hpd();}
    if(status==UWBAPI_STATUS_OK || status==UWBAPI_STATUS_SESSION_NOT_EXIST){*session=0;return UWBAPI_STATUS_OK;}
    return status; /* Retain the handle: cleanup was not acknowledged. */
}
static tUWBAPI_STATUS start_tag_once(const UbpSurveyCommand *command,uint32_t *session){
    int twr=command->mode>=2;uint32_t requested=twr?command->session:0x22334455;
    *session=0;
    tUWBAPI_STATUS status=UwbApi_SessionInit(requested,UWBD_RANGING_SESSION);stage(3,status);
    if(status!=UWBAPI_STATUS_OK)return status;
    *session=requested;
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
    stage(4,status);
    if(status==UWBAPI_STATUS_OK){status=UwbApi_StartRangingSession(*session);stage(5,status);}
    if(status==UWBAPI_STATUS_OK){
        uint8_t state=UWBAPI_SESSION_ERROR;status=UwbApi_GetSessionState(*session,&state);
        if(status==UWBAPI_STATUS_OK && state!=UWBAPI_SESSION_ACTIVATED)status=UWBAPI_STATUS_FAILED;
        stage(6,status);
    }
    if(status!=UWBAPI_STATUS_OK && status!=UWBAPI_STATUS_HPD_WAKEUP){
        tUWBAPI_STATUS cleanup=UwbApi_SessionDeinit(*session);
        if(cleanup==UWBAPI_STATUS_OK || cleanup==UWBAPI_STATUS_SESSION_NOT_EXIST)*session=0;
    }
    return status;
}
static tUWBAPI_STATUS start_tag(const UbpSurveyCommand *command,uint32_t *session){
    tUWBAPI_STATUS status=start_tag_once(command,session);
    if(status==UWBAPI_STATUS_HPD_WAKEUP){
        *session=0;status=recover_hpd();
        if(status==UWBAPI_STATUS_OK)status=start_tag_once(command,session);
        if(status==UWBAPI_STATUS_HPD_WAKEUP)*session=0; /* At most one recovery retry. */
    }
    return status;
}
static tUWBAPI_STATUS transition_tag(const UbpSurveyCommand *command,uint32_t *session){
    tUWBAPI_STATUS status=stop_tag(session);
    if(status!=UWBAPI_STATUS_OK)return status;
    return command->mode==1?UWBAPI_STATUS_OK:start_tag(command,session);
}
#ifndef UBP_RADIO_UNIT_TEST
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
    status=UwbApi_SessionNvmManage(SESSION_NVM_MANAGE_DELETE_ALL,0);
    if(status!=UWBAPI_STATUS_OK){UbpState("session_clear_failed",status);goto fail;}
    uint32_t session=0;UbpSurveyCommand current;memset(&current,0,sizeof(current));
    status=start_tag(&current,&session);UbpState(status==UWBAPI_STATUS_OK?"running":"start_failed",status);
    UbpTagBleAdvertise();int closing=0;int autonomous_ready=status==UWBAPI_STATUS_OK && session!=0;
    for(;;){
        if(!closing && !UbpTagBleWindowRemaining()){closing=1;UbpTagBleClose();UbpSurveyDisconnect();}
        int legacy=UbpPoll();UbpSurveyCommand command;int have=UbpSurveyTake(&command);
        if(!have && (UbpSurveyExpired() || legacy)){memset(&command,0,sizeof(command));command.request=current.request?current.request:1;command.mode=legacy==2?1:0;command.lease_ms=legacy==2?30000:0;command.received_tick=xTaskGetTickCount();have=1;}
        if(have){
            status=transition_tag(&command,&session);
            int restored=0;
            if(status!=UWBAPI_STATUS_OK){
                uint16_t error=status;command.mode=0;command.session=0;
                /* A failed requested transition still reports its error even
                 * when restoring autonomous BLINK succeeds. */
                restored=transition_tag(&command,&session)==UWBAPI_STATUS_OK;status=error;
            }
            current=command;UbpSurveyResult(&command,status,session);
            autonomous_ready=command.mode==0 && session!=0 && (status==UWBAPI_STATUS_OK || restored);
            UbpState(status!=UWBAPI_STATUS_OK && !restored?"radio_transition_failed":command.mode==0?"running":command.mode==1?"survey_hold":"survey_twr",status);
        }
        if(closing && UbpTagBleClosed()){
            if(autonomous_ready && current.mode==0)UbpState("battery_sleep",0);
            else{
                /* Do not stay awake forever or claim BLINK was restored after
                 * an unrecoverable transition at the end of the BLE window. */
                tUWBAPI_STATUS shutdown=UwbApi_ShutDown();UbpState("battery_radio_fault_sleep",shutdown);
            }
            phOsalUwb_Delay(100);
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
#endif
