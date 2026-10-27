#include "phUwb_BuildConfig.h"
#include "ubp_ble.h"
#include "uwb_programmer_console.h"
#include "FreeRTOS.h"
#include "task.h"
#include "queue.h"
#include "gap_interface.h"
#include "gatt_server_interface.h"
#include "gatt_db_app_interface.h"
#include "gatt_database.h"
#include "gatt_db_handles.h"
#include "ApplMain.h"
#include "ble_conn_manager.h"
#include "fsl_debug_console.h"
#include <string.h>
#include <stdlib.h>

#define UUID128(name, ...) uint8_t name[16]={__VA_ARGS__};
#include "gatt_uuid128.h"
#undef UUID128
gapSmpKeys_t gSmpKeys={0}; /* Pairing/bonding disabled for this read-only bench. */
static const uint16_t read_handles[]={value_ubp_info};
static QueueHandle_t packets;
static deviceId_t peer=gInvalidDeviceId_c;
static volatile int subscribed, scheduled;
static uint32_t losses;
static TaskHandle_t ble_task;
static uint8_t advertising_identity[26], flags=6;
static gapAdStructure_t fields[2];
static gapAdvertisingData_t advertising={2,fields};
static gapAdStructure_t response_fields[2];
static gapScanResponseData_t response={2,response_fields};
static gapAdvertisingParameters_t parameters={
    160,240,gAdvConnectableUndirected_c,gBleAddrTypePublic_c,
    gBleAddrTypePublic_c,{0},gGapAdvertisingChannelMapDefault_c,gProcessAll_c};

static void refresh_info(void) {
    char text[256];unsigned length=UbpInfoJson(text,sizeof(text));
    if(length<sizeof(text))GattDb_WriteAttribute(value_ubp_info,length,(uint8_t *)text);
}
static void advertise_event(gapAdvertisingEvent_t *event) {
    PRINTF("UBP_BLE advertising event=%u\r\n",event->eventType);
}
static void connection(deviceId_t id,gapConnectionEvent_t *event) {
    PRINTF("UBP_BLE connection event=%u\r\n",event->eventType);
    BleConnManager_GapPeripheralEvent(id,event);
    if(event->eventType==gConnEvtConnected_c) {
        peer=id;subscribed=0;xQueueReset(packets);refresh_info();
        PRINTF("UBP_BLE connected\r\n");
    } else if(event->eventType==gConnEvtDisconnected_c) {
        peer=gInvalidDeviceId_c;subscribed=0;xQueueReset(packets);
        PRINTF("UBP_BLE disconnected; UWB remains active\r\n");
        Gap_SetAdvertisingParameters(&parameters);
    }
}
static void server(deviceId_t id,gattServerEvent_t *event) {
    PRINTF("UBP_GATT event=%u\r\n",event->eventType);
    if(event->eventType==gEvtCharacteristicCccdWritten_c && event->eventData.charCccdWrittenEvent.handle==cccd_ubp_data) {
        xQueueReset(packets);
        subscribed=(event->eventData.charCccdWrittenEvent.newCccd & 1)!=0;
    } else if(event->eventType==gEvtAttributeRead_c) {
        uint16_t handle=event->eventData.attributeReadEvent.handle;
        /* Info is frozen for this connection, including long ATT reads. */
        GattServer_SendAttributeReadStatus(id,handle,gAttErrCodeNoError_c);
    }
}
void BleApp_Init(void) {}
void BleApp_HandleKeys(key_event_t events) {(void)events;}
void BleApp_GenericCallback(gapGenericEvent_t *event) {
    BleConnManager_GenericEvent(event);
    if(event->eventType==gInitializationComplete_c) {
        BleConnManager_GapCommonConfig(); /* Apply SDK PHY policy (HS 2 Mbps clock is disabled). */
        void *probe=malloc(64);PRINTF("UBP_C_HEAP probe=%u\r\n",probe!=0);free(probe);
        PRINTF("UBP_GATT attributes=%u info=%u data=%u\r\n",gGattDbAttributeCount_c,value_ubp_info,value_ubp_data);
        for(unsigned i=0;i<gGattDbAttributeCount_c;i++)PRINTF("UBP_ATTR handle=%u uuidtype=%u len=%u\r\n",gattDatabase[i].handle,gattDatabase[i].uuidType,gattDatabase[i].valueLength);
        GattServer_RegisterHandlesForReadNotifications(1,read_handles);
        App_RegisterGattServerCallback(server);
        char text[256];unsigned length=UbpInfoJson(text,sizeof(text));
        PRINTF("UBP_GATT info_write=%u len=%u\r\n",GattDb_WriteAttribute(value_ubp_info,length,(uint8_t *)text),length);
        for(unsigned i=0;i<gGattDbAttributeCount_c;i++) {
            if(gattDatabase[i].valueLength==16 || gattDatabase[i].valueLength==19) {
                PRINTF("UBP_UUID handle=%u value=",gattDatabase[i].handle);
                for(unsigned j=0;j<gattDatabase[i].valueLength;j++)PRINTF("%02x",gattDatabase[i].pValue[j]);
                PRINTF("\r\n");
            }
        }
        Gap_SetAdvertisingParameters(&parameters);
        PRINTF("UBP_BLE initialized\r\n");
    } else if(event->eventType==gRandomAddressSet_c) {
        Gap_SetAdvertisingParameters(&parameters);
    } else if(event->eventType==gAdvertisingParametersSetupComplete_c) {
        Gap_SetAdvertisingData(&advertising,&response);
    } else if(event->eventType==gAdvertisingDataSetupComplete_c) {
        App_StartAdvertising(advertise_event,connection);
    } else if(event->eventType==gAdvertisingSetupFailed_c) {
        PRINTF("UBP_BLE advertising failed\r\n");
    }
}
static void app_task(void *unused) {(void)unused;main_task(0);vTaskDelete(0);}
void UbpBleStart(void) {
    if(ble_task)return;
    packets=xQueueCreate(8,64);if(!packets){UbpState("ble_queue_failed",-1);return;}
    memcpy(advertising_identity,uuid_service_ubp,16);
    advertising_identity[16]=1;advertising_identity[17]=UWB_PROGRAMMER_MASTER?1:0;
    memcpy(advertising_identity+18,gUbpConfig.mac,8);
    fields[0]=(gapAdStructure_t){2,gAdFlags_c,&flags};
    fields[1]=(gapAdStructure_t){27,gAdServiceData128bit_c,advertising_identity};
    response_fields[0]=(gapAdStructure_t){17,gAdComplete128bitServiceList_c,uuid_service_ubp};
    response_fields[1]=(gapAdStructure_t){7,gAdShortenedLocalName_c,(uint8_t *)"UBP RF"};
    if(xTaskCreate(app_task,"UbpBle",1024,0,3,&ble_task)!=pdPASS)UbpState("ble_task_failed",-1);
}
static void put32(uint8_t *p,uint32_t n) {for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static uint32_t crc32(const uint8_t *data,unsigned n) {
    uint32_t crc=0xffffffff;for(unsigned i=0;i<n;i++){crc^=data[i];for(unsigned k=0;k<8;k++)crc=(crc>>1)^((0-(crc&1))&0xedb88320);}return ~crc;
}
static void send_packet(appCallbackParam_t unused) {
    (void)unused;uint8_t packet[64];scheduled=0;
    if(!subscribed || peer==gInvalidDeviceId_c){xQueueReset(packets);return;}
    if(xQueueReceive(packets,packet,0)==pdPASS) {
        for(unsigned i=0;i<6;i++) {
            uint8_t part[20]={1,1,packet[8],packet[9],(uint8_t)i,6,64,0};
            unsigned n=64-i*12;if(n>12)n=12;memcpy(part+8,packet+i*12,n);
            if(GattServer_SendInstantValueNotification(peer,value_ubp_data,n+8,part)!=gBleSuccess_c){losses++;break;}
        }
    }
    if(uxQueueMessagesWaiting(packets)) {
        scheduled=1;if(App_PostCallbackMessage(send_packet,0)!=gBleSuccess_c){scheduled=0;losses++;xQueueReset(packets);}
    }
}
void UbpBleMeasurement(const phRangingMesrTdoa_t *m,unsigned mac_len,uint32_t boot,uint32_t sequence,uint32_t dropped) {
    if(!packets || !subscribed || peer==gInvalidDeviceId_c)return;
    uint8_t data[64]={0};data[0]='U';data[1]='B';data[2]=1;data[3]=1;
    put32(data+4,boot);put32(data+8,sequence);data[12]=UWB_PROGRAMMER_MASTER?1:0;
    data[13]=(m->message_control&ULTDOA_64BIT_RX_TIMESTAMP_MASK)?64:40;
    data[14]=(m->message_control&ULTDOA_64BIT_TX_TIMESTAMP_MASK)?64:((m->message_control&ULTDOA_40BIT_TX_TIMESTAMP_MASK)?40:0);
    data[15]=m->frame_type;put32(data+16,m->frame_number);data[20]=m->status;data[21]=m->message_control;
    data[22]=mac_len;memcpy(data+24,m->mac_addr,mac_len);memcpy(data+32,m->rx_timestamp,data[13]/8);memcpy(data+40,m->tx_timestamp,data[14]/8);
    data[48]=m->aoa_azimuth;data[49]=m->aoa_azimuth>>8;data[50]=m->aoa_elevation;data[51]=m->aoa_elevation>>8;
    data[52]=m->aoa_azimuth_FOM;data[53]=m->aoa_elevation_FOM;data[54]=m->nLos;
    put32(data+56,dropped+losses);put32(data+60,crc32(data,60));
    if(xQueueSend(packets,data,0)!=pdPASS){losses++;return;}
    taskENTER_CRITICAL();int post=!scheduled;if(post)scheduled=1;taskEXIT_CRITICAL();
    if(post && App_PostCallbackMessage(send_packet,0)!=gBleSuccess_c){scheduled=0;losses++;xQueueReset(packets);}
}
