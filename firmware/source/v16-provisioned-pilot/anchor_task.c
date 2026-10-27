/* UWB_PROGRAMMER application based on the NXP UL-TDoA demo API; vendor originals preserved. */
#include "phUwb_BuildConfig.h"
#include "AppRecovery.h"
#include "UwbApi.h"
#include "AppInternal.h"
#include "uwb_programmer_console.h"
#include <string.h>
#include "ubp_ble.h"
#include "FreeRTOS.h"
#include "task.h"
#include "fsl_debug_console.h"
static void UbpDiagnostic(void *unused) { (void)unused; for(;;) { PRINTF("{\"v\":1,\"kind\":\"diag\",\"tick\":%lu,\"free_heap\":%lu}\r\n",(unsigned long)xTaskGetTickCount(),(unsigned long)xPortGetFreeHeapSize()); vTaskDelay(pdMS_TO_TICKS(2000)); } }
AppContext_t appContext;
OSAL_TASK_RETURN_TYPE StandaloneTask(void *args) {
    UbpConsoleInit();
    if(!gUbpConfigReady){for(;;){UbpPoll();phOsalUwb_Delay(10);}}
    xTaskCreate(UbpDiagnostic,"UbpDiag",384,0,1,0);
    UbpState("radio_init_begin",0);
    tUWBAPI_STATUS status=UWBAPI_STATUS_FAILED;
    for(unsigned attempt=0;attempt<3;attempt++){status=UwbApi_Init(UbpCallback);if(status==UWBAPI_STATUS_OK)break;UbpState("radio_init_retry",status);phOsalUwb_Delay(1500);}
    if(status!=UWBAPI_STATUS_OK) {UbpState("radio_init_failed",status);goto fail;}
    int otp=UbpApplyOtp();if(otp) {UbpState("otp_calibration_failed",otp);goto fail;}
    UbpState("ready",0);
    int boot_autostart=1;
    for(;;) {
        if(boot_autostart) { UbpState("autostart",0); phOsalUwb_Delay(200); boot_autostart=0; }
        else while(UbpPoll()!=1) phOsalUwb_Delay(5);
        uint32_t handle=0;
        status=UwbApi_SessionInit(0x22334455,UWBD_RANGING_SESSION,&handle);
        if(status!=UWBAPI_STATUS_OK) {UbpState("session_init_failed",status);continue;}
        const UWB_AppParams_List_t params[]={
            UWB_SET_APP_PARAM_VALUE(RFRAME_CONFIG,kUWB_RfFrameConfig_Sfd_Sts),
            UWB_SET_APP_PARAM_VALUE(STS_CONFIG,kUWB_StsConfig_StaticSts),
            UWB_SET_APP_PARAM_VALUE(RANGING_DURATION,200),
            UWB_SET_APP_PARAM_VALUE(SESSION_INFO_NTF,1),
            UWB_SET_APP_PARAM_VALUE(SFD_ID,0),
            UWB_SET_APP_PARAM_VALUE(CHANNEL_NUMBER,9),
            UWB_SET_APP_PARAM_VALUE(PREAMBLE_CODE_INDEX,10),
            UWB_SET_APP_PARAM_VALUE(MAC_FCS_TYPE,0),
            UWB_SET_APP_PARAM_VALUE(NO_OF_CONTROLEES,1),
            UWB_SET_APP_PARAM_VALUE(AOA_RESULT_REQ,1),
#if UWB_PROGRAMMER_MASTER
            UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_INTERVAL,500),
            UWB_SET_APP_PARAM_VALUE(UL_TDOA_TX_TIMESTAMP,2),
#endif
        };
        status=UwbApi_SetAppConfigMultipleParams(handle,sizeof(params)/sizeof(params[0]),params);
        phRangingParams_t ranging;memset(&ranging,0,sizeof(ranging));
        ranging.deviceRole=UWB_PROGRAMMER_MASTER?kUWB_DeviceRole_UT_Sync_Anchor:kUWB_DeviceRole_UT_Anchor;
        ranging.multiNodeMode=kUWB_MultiNodeMode_OnetoMany;
        ranging.macAddrMode=EXTENDED_MAC_ADDRESS_MODE_WITH_HEADER;
        ranging.deviceType=kUWB_DeviceType_Controlee;
        ranging.scheduledMode=kUWB_ScheduledMode_TimeScheduled;
        ranging.rangingRoundUsage=kUWB_RangingMethod_TDoA;
        memcpy(ranging.deviceMacAddr,gUbpConfig.mac,8);
        if(status==UWBAPI_STATUS_OK) status=UwbApi_SetRangingParams(handle,&ranging);
        if(status==UWBAPI_STATUS_OK) status=UwbApi_StartRangingSession(handle);
        if(status!=UWBAPI_STATUS_OK) {UbpState("start_failed",status);UwbApi_SessionDeinit(handle);continue;}
        UbpState("running",0);
        UbpBleStart();
        while(UbpPoll()!=2) phOsalUwb_Delay(10);
        status=UwbApi_StopRangingSession(handle);UbpState("stopped",status);
        UwbApi_SessionDeinit(handle);
    }
fail:
    for(;;){UbpPoll();phOsalUwb_Delay(100);}
}
UWBOSAL_TASK_HANDLE uwb_demo_start(void) {
    phOsalUwb_ThreadCreationParams_t params;UWBOSAL_TASK_HANDLE task;
    memset(&params,0,sizeof(params));params.stackdepth=1024;params.priority=4;params.pContext=0;
    PHOSALUWB_SET_TASKNAME(params,"UWBProgrammer");
    if(phOsalUwb_Thread_Create((void**)&task,&StandaloneTask,&params)!=0) return 0;
    return task;
}
