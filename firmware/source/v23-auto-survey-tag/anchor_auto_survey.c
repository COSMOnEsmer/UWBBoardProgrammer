/* Experimental dual-mode application. Vendor and 1.3.4 sources retained. */
#include "phUwb_BuildConfig.h"
#include "AppRecovery.h"
#include "UwbApi.h"
#include "AppInternal.h"
#include "uwb_programmer_console.h"
#include "ubp_ble.h"
#include "ubp_survey.h"
#include "FreeRTOS.h"
#include "task.h"
#include "fsl_debug_console.h"
#include <string.h>
AppContext_t appContext;
static void diagnostic(void *unused){(void)unused;for(;;){PRINTF("{\"v\":1,\"kind\":\"diag\",\"tick\":%lu,\"free_heap\":%lu}\r\n",(unsigned long)xTaskGetTickCount(),(unsigned long)xPortGetFreeHeapSize());vTaskDelay(pdMS_TO_TICKS(2000));}}
static tUWBAPI_STATUS start_radio(const UbpSurveyCommand *command,uint32_t *handle){
    int twr=command->mode>=2;
    tUWBAPI_STATUS status=UwbApi_SessionInit(twr?command->session:0x22334455,UWBD_RANGING_SESSION,handle);
    if(status!=UWBAPI_STATUS_OK)return status;
    if(twr){
        /* This radio firmware rejects 64-bit-header mode for DS-TWR (reason
         * 0x22). Use distinct suffix-derived 16-bit addresses only in survey.
         * The commissioned 64-bit UWB/BLE identity remains unchanged. */
        uint8_t dst[2]={command->peer[6],command->peer[7]};
        const UWB_AppParams_List_t params[]={
            UWB_SET_APP_PARAM_VALUE(RFRAME_CONFIG,3),UWB_SET_APP_PARAM_VALUE(STS_CONFIG,kUWB_StsConfig_StaticSts),
            UWB_SET_APP_PARAM_VALUE(RANGING_DURATION,100),UWB_SET_APP_PARAM_VALUE(SLOTS_PER_RR,25),
            UWB_SET_APP_PARAM_VALUE(SESSION_INFO_NTF,1),UWB_SET_APP_PARAM_VALUE(SFD_ID,2),
            UWB_SET_APP_PARAM_VALUE(CHANNEL_NUMBER,9),UWB_SET_APP_PARAM_VALUE(PREAMBLE_CODE_INDEX,10),
            UWB_SET_APP_PARAM_VALUE(MAC_FCS_TYPE,0),UWB_SET_APP_PARAM_VALUE(NO_OF_CONTROLEES,1),
            UWB_SET_APP_PARAM_VALUE(AOA_RESULT_REQ,0),UWB_SET_APP_PARAM_ARRAY(DST_MAC_ADDRESS,dst,2),
        };
        status=UwbApi_SetAppConfigMultipleParams(*handle,sizeof(params)/sizeof(params[0]),params);
    }else{
        const UWB_AppParams_List_t params[]={
            UWB_SET_APP_PARAM_VALUE(RFRAME_CONFIG,kUWB_RfFrameConfig_Sfd_Sts),UWB_SET_APP_PARAM_VALUE(STS_CONFIG,kUWB_StsConfig_StaticSts),
            UWB_SET_APP_PARAM_VALUE(RANGING_DURATION,200),UWB_SET_APP_PARAM_VALUE(SESSION_INFO_NTF,1),
            UWB_SET_APP_PARAM_VALUE(SFD_ID,0),UWB_SET_APP_PARAM_VALUE(CHANNEL_NUMBER,9),
            UWB_SET_APP_PARAM_VALUE(PREAMBLE_CODE_INDEX,10),UWB_SET_APP_PARAM_VALUE(MAC_FCS_TYPE,0),
            UWB_SET_APP_PARAM_VALUE(NO_OF_CONTROLEES,1),UWB_SET_APP_PARAM_VALUE(AOA_RESULT_REQ,1),
#if UWB_PROGRAMMER_MASTER
            UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_INTERVAL,500),UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_TIMESTAMP,2),
#endif
        };
        status=UwbApi_SetAppConfigMultipleParams(*handle,sizeof(params)/sizeof(params[0]),params);
    }
    uint8_t rx_ant[]={twr?kUWBAntCfgRxMode_ToA_Mode:kUWBAntCfgRxMode_AoA_Mode,twr?1:2,1,2};
    const UWB_VendorAppParams_List_t vendor[]={
        UWB_SET_VENDOR_APP_PARAM_VALUE(TX_ADAPTIVE_PAYLOAD_POWER,1),
        UWB_SET_VENDOR_APP_PARAM_ARRAY(ANTENNAE_CONFIGURATION_RX,rx_ant,twr?3:4),
    };
    if(status==UWBAPI_STATUS_OK)status=UwbApi_SetVendorAppConfigs(*handle,sizeof(vendor)/sizeof(vendor[0]),vendor);
    phRangingParams_t ranging;memset(&ranging,0,sizeof(ranging));
    ranging.deviceRole=twr?(command->mode==3?kUWB_DeviceRole_Initiator:kUWB_DeviceRole_Responder):(UWB_PROGRAMMER_MASTER?kUWB_DeviceRole_UT_Sync_Anchor:kUWB_DeviceRole_UT_Anchor);
    ranging.multiNodeMode=twr?kUWB_MultiNodeMode_UniCast:kUWB_MultiNodeMode_OnetoMany;
    ranging.macAddrMode=twr?SHORT_MAC_ADDRESS_MODE:EXTENDED_MAC_ADDRESS_MODE_WITH_HEADER;
    ranging.deviceType=twr?(command->mode==3?kUWB_DeviceType_Controller:kUWB_DeviceType_Controlee):kUWB_DeviceType_Controlee;
    ranging.scheduledMode=kUWB_ScheduledMode_TimeScheduled;
    ranging.rangingRoundUsage=twr?kUWB_RangingRoundUsage_DS_TWR:kUWB_RangingMethod_TDoA;
    memcpy(ranging.deviceMacAddr,gUbpConfig.mac,8);
    if(twr){memset(ranging.deviceMacAddr,0,8);ranging.deviceMacAddr[0]=gUbpConfig.mac[6];ranging.deviceMacAddr[1]=gUbpConfig.mac[7];}
    if(status==UWBAPI_STATUS_OK)status=UwbApi_SetRangingParams(*handle,&ranging);
    if(status==UWBAPI_STATUS_OK)status=UwbApi_StartRangingSession(*handle);
    if(status!=UWBAPI_STATUS_OK){UwbApi_SessionDeinit(*handle);*handle=0;}
    return status;
}
OSAL_TASK_RETURN_TYPE StandaloneTask(void *args){
    (void)args;UbpConsoleInit();
    if(!gUbpConfigReady){for(;;){UbpPoll();phOsalUwb_Delay(10);}}
    xTaskCreate(diagnostic,"UbpDiag",384,0,1,0);
    tUWBAPI_STATUS status=UWBAPI_STATUS_FAILED;
    for(unsigned i=0;i<3;i++){status=UwbApi_Init(UbpCallback);if(status==UWBAPI_STATUS_OK)break;phOsalUwb_Delay(1500);}
    if(status!=UWBAPI_STATUS_OK){UbpState("radio_init_failed",status);goto fail;}
    if(UbpApplyOtp()){UbpState("otp_calibration_failed",-1);goto fail;}
    uint32_t handle=0;UbpSurveyCommand current;memset(&current,0,sizeof(current));
    status=start_radio(&current,&handle);UbpState(status==UWBAPI_STATUS_OK?"running":"start_failed",status);UbpBleStart();
    for(;;){
        int legacy=UbpPoll();UbpSurveyCommand command;int have=UbpSurveyTake(&command);
        if(!have && (UbpSurveyExpired() || legacy)){memset(&command,0,sizeof(command));command.request=current.request?current.request:1;command.mode=legacy==2?1:0;command.lease_ms=legacy==2?30000:0;command.received_tick=xTaskGetTickCount();have=1;}
        if(have){
            if(handle){UwbApi_StopRangingSession(handle);UwbApi_SessionDeinit(handle);handle=0;}
            status=command.mode==1?UWBAPI_STATUS_OK:start_radio(&command,&handle);
            if(status!=UWBAPI_STATUS_OK){UbpState("survey_start_failed",status);uint16_t failure=status;command.mode=0;command.session=0;start_radio(&command,&handle);status=failure;}
            current=command;UbpSurveyResult(&command,status,handle);UbpState(command.mode==0?"running":command.mode==1?"survey_hold":"survey_twr",status);
        }
        phOsalUwb_Delay(10);
    }
fail:for(;;){UbpPoll();phOsalUwb_Delay(100);}
}
UWBOSAL_TASK_HANDLE uwb_demo_start(void){
    phOsalUwb_ThreadCreationParams_t params;UWBOSAL_TASK_HANDLE task;memset(&params,0,sizeof(params));params.stackdepth=1536;params.priority=4;PHOSALUWB_SET_TASKNAME(params,"UWBProgrammer");
    if(phOsalUwb_Thread_Create((void**)&task,&StandaloneTask,&params)!=0)return 0;return task;
}
