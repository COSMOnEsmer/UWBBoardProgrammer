/* Experimental Type2DK calibration control. No claim of verified coin-cell life.
 * The finite commissioning window is closed before the host sleeps; the UWB
 * BLINK session is restored by tag_auto_survey.c. */
#include "phUwb_BuildConfig.h"
#include "ubp_tag_ble.h"
#include "uwb_programmer_console.h"
#include "ubp_survey.h"
#include "FreeRTOS.h"
#include "task.h"
#include "gap_interface.h"
#include "gatt_server_interface.h"
#include "gatt_db_app_interface.h"
#include "gatt_database.h"
#include "gatt_db_handles.h"
#include "ApplMain.h"
#include "ble_conn_manager.h"
#include "fsl_debug_console.h"
#include <string.h>
#define UUID128(name, ...) uint8_t name[16]={__VA_ARGS__};
#include "gatt_uuid128.h"
#undef UUID128
gapSmpKeys_t gSmpKeys={0};
static const uint16_t read_handles[]={value_ubp_info,value_ubp_survey_status};
static const uint16_t write_handles[]={value_ubp_survey_control};
static deviceId_t peer=gInvalidDeviceId_c;
static volatile int closing,advertising_active,ready;
static TickType_t window_start;
static TaskHandle_t ble_task;
static uint8_t identity[26],flags=6;
static gapAdStructure_t fields[2],response_fields[2];
static gapAdvertisingData_t advertising={2,fields};
static gapScanResponseData_t response={2,response_fields};
static gapAdvertisingParameters_t parameters={320,480,gAdvConnectableUndirected_c,
    gBleAddrTypePublic_c,gBleAddrTypePublic_c,{0},gGapAdvertisingChannelMapDefault_c,gProcessAll_c};

static void refresh_info(void){
    char text[512];unsigned length=UbpInfoJson(text,sizeof(text));
    if(length<sizeof(text))GattDb_WriteAttribute(value_ubp_info,length,(uint8_t*)text);
}
static void advertise_event(gapAdvertisingEvent_t *event){
    if(event->eventType==gAdvertisingStateChanged_c)advertising_active=closing?0:!advertising_active;
    PRINTF("UBP_TAG_BLE adv=%u closing=%u\r\n",event->eventType,closing);
}
static void connection(deviceId_t id,gapConnectionEvent_t *event){
    BleConnManager_GapPeripheralEvent(id,event);
    if(event->eventType==gConnEvtConnected_c){peer=id;advertising_active=0;refresh_info();}
    else if(event->eventType==gConnEvtDisconnected_c){
        peer=gInvalidDeviceId_c;UbpSurveyDisconnect();
        if(!closing)Gap_SetAdvertisingParameters(&parameters);
    }
}
static void server(deviceId_t id,gattServerEvent_t *event){
    if(event->eventType==gEvtAttributeWritten_c && event->eventData.attributeWrittenEvent.handle==value_ubp_survey_control){
        gattServerAttributeWrittenEvent_t *write=&event->eventData.attributeWrittenEvent;
        int ok=!closing && UbpSurveySubmit(write->aValue,write->cValueLength);
        GattServer_SendAttributeWrittenStatus(id,write->handle,ok?gAttErrCodeNoError_c:0x0d);
    }else if(event->eventType==gEvtAttributeRead_c){
        uint16_t handle=event->eventData.attributeReadEvent.handle;
        if(handle==value_ubp_survey_status){uint8_t data[24];UbpSurveyStatus(data);GattDb_WriteAttribute(handle,24,data);}
        GattServer_SendAttributeReadStatus(id,handle,gAttErrCodeNoError_c);
    }
}
void BleApp_Init(void){}
void BleApp_HandleKeys(key_event_t events){(void)events;}
void BleApp_GenericCallback(gapGenericEvent_t *event){
    BleConnManager_GenericEvent(event);
    if(event->eventType==gInitializationComplete_c){
        BleConnManager_GapCommonConfig();
        GattServer_RegisterHandlesForReadNotifications(2,read_handles);
        GattServer_RegisterHandlesForWriteNotifications(1,write_handles);
        App_RegisterGattServerCallback(server);refresh_info();ready=1;
        PRINTF("UBP_TAG_BLE initialized\r\n");
    }else if(event->eventType==gAdvertisingParametersSetupComplete_c){
        if(!closing)Gap_SetAdvertisingData(&advertising,&response);
    }else if(event->eventType==gAdvertisingDataSetupComplete_c){
        if(!closing)App_StartAdvertising(advertise_event,connection);
    }
}
static void app_task(void *unused){(void)unused;main_task(0);vTaskDelete(0);}
void UbpTagBleStart(void){
    if(ble_task)return;
    window_start=xTaskGetTickCount();
    memcpy(identity,uuid_service_ubp,16);identity[16]=1;identity[17]=2; /* Tag, never an anchor. */
    memcpy(identity+18,gUbpConfig.mac,8);
    fields[0]=(gapAdStructure_t){2,gAdFlags_c,&flags};
    fields[1]=(gapAdStructure_t){27,gAdServiceData128bit_c,identity};
    response_fields[0]=(gapAdStructure_t){17,gAdComplete128bitServiceList_c,uuid_service_ubp};
    response_fields[1]=(gapAdStructure_t){8,gAdShortenedLocalName_c,(uint8_t*)"UBP TAG"};
    if(xTaskCreate(app_task,"UbpTagBle",1024,0,3,&ble_task)!=pdPASS)UbpState("ble_task_failed",-1);
}
int UbpTagBleReady(void){return ready;}
static void advertise_callback(appCallbackParam_t unused){(void)unused;if(ready && !closing)Gap_SetAdvertisingParameters(&parameters);}
void UbpTagBleAdvertise(void){if(ready && !closing)App_PostCallbackMessage(advertise_callback,0);}
unsigned UbpTagBleWindowRemaining(void){
    TickType_t elapsed=(TickType_t)(xTaskGetTickCount()-window_start);
    if(!ble_task || closing || elapsed>=pdMS_TO_TICKS(900000))return 0;
    return 900-(unsigned)(elapsed/pdMS_TO_TICKS(1000));
}
static void close_callback(appCallbackParam_t unused){
    (void)unused;
    if(peer!=gInvalidDeviceId_c)Gap_Disconnect(peer);
    if(advertising_active)Gap_StopAdvertising();
}
void UbpTagBleClose(void){
    closing=1;
    if(ble_task && App_PostCallbackMessage(close_callback,0)!=gBleSuccess_c)UbpState("ble_close_pending",-1);
}
int UbpTagBleClosed(void){return closing && peer==gInvalidDeviceId_c && !advertising_active;}
