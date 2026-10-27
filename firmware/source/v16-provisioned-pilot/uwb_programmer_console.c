#include "phUwb_BuildConfig.h"
#include "uwb_programmer_console.h"
#include "fsl_debug_console.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "PDM.h"
#include "RNG_Interface.h"
#include "AppInternal.h"
#include <stdio.h>
#if !UWB_PROGRAMMER_TAG
#include "ubp_ble.h"
#endif
#include <stdlib.h>
#include <string.h>
#ifndef UWB_PROGRAMMER_TAG
#define UWB_PROGRAMMER_TAG 0
#endif
#ifndef UWB_PROGRAMMER_MASTER
#define UWB_PROGRAMMER_MASTER 0
#endif
#ifndef UBP_BOARD_SLOT
#define UBP_BOARD_SLOT 1
#endif
uint32_t gUbpConfigReady;
static uint32_t gProvisionCrc;
UbpConfig gUbpConfig = {0xE2E11001, {2,0,0,0,0,0,0,UBP_BOARD_SLOT}, 500};
static const char *gRole = UWB_PROGRAMMER_TAG ? "tag" : (UWB_PROGRAMMER_MASTER ? "master" : "slave");
static const char *gModel = UWB_PROGRAMMER_TAG ? "Type2DK" : "Type2BP";
static const char *gRunState="booting";
static uint32_t gSequence;
static char gInput[128]; static unsigned gInputLen; static unsigned long gBoot; static unsigned long gDrops;
#if UWBFTR_UL_TDoA_Anchor
typedef struct { phRangingMesrTdoa_t measurement; uint8_t mac_len; } UbpEvent;
static QueueHandle_t gEvents;
#endif
static void hex_mac(char *out,const uint8_t *mac,unsigned length) {
    const char hex[]="0123456789ABCDEF";
    for (unsigned i=0;i<length;i++) { out[2*i]=hex[mac[i]>>4]; out[2*i+1]=hex[mac[i]&15]; }
    out[2*length]=0;
}
unsigned UbpInfoJson(char *out,unsigned size) {
    char mac[17];hex_mac(mac,gUbpConfig.mac,8);
    return snprintf(out,size,"{\"v\":1,\"model\":\"Type2BP\",\"role\":\"%s\",\"mac\":\"%s\",\"boot\":\"%08lx\",\"sequence\":%lu,\"firmware\":\"1.3.1-pilot\",\"autonomous\":true,\"radio_state\":\"%s\",\"interval_ms\":%lu,\"config_crc\":\"%08lx\",\"provisioned\":%s}",gRole,mac,gBoot,(unsigned long)gSequence,gRunState,(unsigned long)gUbpConfig.interval_ms,(unsigned long)gProvisionCrc,gUbpConfigReady?"true":"false");
}
static void hello(void) {
    char mac[17]; hex_mac(mac,gUbpConfig.mac,8);
    PRINTF("{\"v\":1,\"kind\":\"hello\",\"model\":\"%s\",\"role\":\"%s\",\"state\":\"%s\",\"version\":\"1.3.1-pilot\",\"mac\":\"%s\",\"interval_ms\":%lu,\"boot\":\"%08lx\",\"dropped\":%lu,\"config_crc\":\"%08lx\",\"provisioned\":%s}\r\n",gModel,gRole,gRunState,mac,(unsigned long)gUbpConfig.interval_ms,gBoot,gDrops,(unsigned long)gProvisionCrc,gUbpConfigReady?"true":"false");
}
void UbpState(const char *state,int code) {
    if(strcmp(state,"configured_restart_required") && strcmp(state,"unknown_command")) gRunState=state;
    PRINTF("{\"v\":1,\"kind\":\"status\",\"state\":\"%s\",\"code\":%d,\"boot\":\"%08lx\"}\r\n",state,code,gBoot);
}
typedef struct { UbpConfig config; uint32_t role; uint32_t crc; } UbpProvision;
_Static_assert(sizeof(UbpProvision)==24,"Provision layout");
static uint32_t provision_crc(const void *data,unsigned length) {
    const uint8_t *bytes=data;uint32_t crc=0xffffffff;
    for(unsigned i=0;i<length;i++){crc^=bytes[i];for(unsigned k=0;k<8;k++)crc=(crc>>1)^((0-(crc&1))&0xedb88320);}
    return ~crc;
}
void UbpConsoleInit(void) {
    gUbpConfigReady=0;gSequence=0;gDrops=0;
    uint16_t length=0;UbpProvision expected,saved;
    if(UWB_PROGRAMMER_TAG){gUbpConfig.mac[6]=1;gUbpConfig.mac[7]=1;gUbpConfig.interval_ms=1000;}
    memset(&expected,0,sizeof(expected));expected.config=gUbpConfig;
    expected.role=UWB_PROGRAMMER_TAG?2:(UWB_PROGRAMMER_MASTER?1:0);
    expected.crc=provision_crc(&expected,sizeof(expected)-4);
    if(PDM_Init()!=0){UbpState("pdm_init_failed",-1);return;}
    int valid=PDM_eReadDataFromRecord(0xE2E3,&saved,sizeof(saved),&length)==PDM_E_STATUS_OK && length==sizeof(saved) && memcmp(&saved,&expected,sizeof(saved))==0;
    if(!valid) {
        if(PDM_eSaveRecordData(0xE2E3,&expected,sizeof(expected))!=PDM_E_STATUS_OK){UbpState("provision_save_failed",-1);return;}
        memset(&saved,0,sizeof(saved));length=0;
        if(PDM_eReadDataFromRecord(0xE2E3,&saved,sizeof(saved),&length)!=PDM_E_STATUS_OK || length!=sizeof(saved) || memcmp(&saved,&expected,sizeof(saved))){UbpState("provision_verify_failed",-1);return;}
    }
    gUbpConfig=saved.config;gProvisionCrc=saved.crc;
    gBoot=(unsigned long)xTaskGetTickCount();
    if(RNG_Init()!=gRngSuccess_d){UbpState("rng_init_failed",-1);return;}
    RNG_GetRandomNo((uint32_t *)&gBoot);
#if UWBFTR_UL_TDoA_Anchor
    gEvents=xQueueCreate(16,sizeof(UbpEvent));
    if(!gEvents){UbpState("queue_error",-1);return;}
#endif
    gUbpConfigReady=1;hello();
}
void UbpCallback(eNotificationType type,void *data) {
#if UWBFTR_UL_TDoA_Anchor
    if(type==UWBD_RANGING_DATA) {
        const phRangingData_t *r=(const phRangingData_t *)data;
        if(r && r->ranging_measure_type==MEASUREMENT_TYPE_ONEWAY) {
            for(unsigned i=0;i<r->no_of_measurements;i++) {
                UbpEvent e; e.measurement=r->ranging_meas.range_meas_tdoa[i]; e.mac_len=r->mac_addr_mode_indicator==0 ? 2 : 8;
                if(!gEvents || xQueueSend(gEvents,&e,0)!=pdPASS) gDrops++;
            }
        }
        return;
    }
#endif
    AppCallback(type,data);
}
static void drain(void) {
#if UWBFTR_UL_TDoA_Anchor
    UbpEvent e;
    for(unsigned count=0;count<16 && gEvents && xQueueReceive(gEvents,&e,0)==pdPASS;count++) {
        phRangingMesrTdoa_t *m=&e.measurement; char peer[17],tx[20];
        unsigned bits=(m->message_control&ULTDOA_64BIT_RX_TIMESTAMP_MASK)?64:40;
        unsigned tx_bits=(m->message_control&ULTDOA_64BIT_TX_TIMESTAMP_MASK)?64:((m->message_control&ULTDOA_40BIT_TX_TIMESTAMP_MASK)?40:0);
        uint32_t low=0,high=0,txlow=0,txhigh=0;
        for(unsigned i=0;i<4;i++) {low|=(uint32_t)m->rx_timestamp[i]<<(8*i); txlow|=(uint32_t)m->tx_timestamp[i]<<(8*i);}
        for(unsigned i=4;i<bits/8;i++) high|=(uint32_t)m->rx_timestamp[i]<<(8*(i-4));
        for(unsigned i=4;i<tx_bits/8;i++) txhigh|=(uint32_t)m->tx_timestamp[i]<<(8*(i-4));
        hex_mac(peer,m->mac_addr,e.mac_len);
        if(tx_bits) snprintf(tx,sizeof(tx),"\"%08lx%08lx\"",(unsigned long)txhigh,(unsigned long)txlow); else strcpy(tx,"null");
        UbpBleMeasurement(m,e.mac_len,(uint32_t)gBoot,++gSequence,(uint32_t)gDrops);
        /* One complete UART call; timestamp words are never converted to floating point. */
        PRINTF("{\"v\":1,\"kind\":\"rx\",\"peer_mac\":\"%s\",\"frame_type\":\"%s\",\"frame_number\":\"%lu\",\"status\":%u,\"message_control\":%u,\"timestamp_bits\":%u,\"tx_timestamp_bits\":%u,\"rx_timestamp_hex\":\"%08lx%08lx\",\"tx_timestamp_hex\":%s,\"azimuth_deg\":%.6f,\"elevation_deg\":%.6f,\"az_fom\":%u,\"el_fom\":%u,\"nlos\":%u,\"boot\":\"%08lx\"}\r\n",peer,m->frame_type==0?"BLINK":"SYNC",(unsigned long)m->frame_number,m->status,m->message_control,bits,tx_bits,(unsigned long)high,(unsigned long)low,tx,(double)m->aoa_azimuth/128.,(double)m->aoa_elevation/128.,m->aoa_azimuth_FOM,m->aoa_elevation_FOM,m->nLos,gBoot);
    }
#endif
}
int UbpPoll(void) {
    char c; drain();
    static TickType_t last_hello;TickType_t now=xTaskGetTickCount();
    if(now-last_hello>=pdMS_TO_TICKS(2000)){hello();last_hello=now;}
    while(DbgConsole_TryGetchar(&c)==kStatus_Success) {
        if(c=='\r') continue;
        if(c!='\n') { if(gInputLen<sizeof(gInput)-1) gInput[gInputLen++]=c; else {gInputLen=0;UbpState("command_too_long",-1);} continue; }
        gInput[gInputLen]=0; gInputLen=0;
        if(strcmp(gInput,"E2E HELLO")==0) hello();
        else if(strcmp(gInput,"E2E START")==0) return 1;
        else if(strcmp(gInput,"E2E STOP")==0) return 2;
        else if(strncmp(gInput,"E2E CONFIG ",11)==0) {
            UbpState("identity_bound_to_selected_image",-1);
        } else UbpState("unknown_command",-1);
    }
    return 0;
}
int UbpApplyOtp(void) {
#if !UWB_PROGRAMMER_TAG
    phCalibPayload_t calib; uint8_t channels[2]={5,9};
    for(unsigned i=0;i<2;i++) {
        memset(&calib,0,sizeof(calib));
        if(UwbApi_ReadOtpCalibDataCmd(channels[i],1<<1,&calib)!=UWBAPI_STATUS_OK) return -1;
        uint8_t power[11]={2,1,0,0,0,0,2,0,0,0,0};
        unsigned rms=calib.TX_POWER_ID[0]+8;
        power[4]=rms>255?255:rms;power[2]=calib.TX_POWER_ID[1];
        if(UwbApi_SetCalibration(channels[i],TX_POWER_PER_ANTENNA,power,sizeof(power))!=UWBAPI_STATUS_OK) return -2;
    }
    if(UwbApi_ReadOtpCalibDataCmd(9,1<<2,&calib)!=UWBAPI_STATUS_OK) return -3;
    uint8_t clock[7]={3,0,0,0,0,0,0};clock[1]=calib.XTAL_CAP_VALUES[0];clock[3]=calib.XTAL_CAP_VALUES[1];clock[5]=calib.XTAL_CAP_VALUES[2];
    if(UwbApi_SetCalibration(9,RF_CLK_ACCURACY_CALIB,clock,sizeof(clock))!=UWBAPI_STATUS_OK) return -4;
#endif
    return 0;
}
