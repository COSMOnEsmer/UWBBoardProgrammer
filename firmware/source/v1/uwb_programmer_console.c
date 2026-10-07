#include "phUwb_BuildConfig.h"
#include "uwb_programmer_console.h"
#include "fsl_debug_console.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "PDM.h"
#include "RNG_Interface.h"
#include "AppInternal.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef UWB_PROGRAMMER_TAG
#define UWB_PROGRAMMER_TAG 0
#endif
#ifndef UWB_PROGRAMMER_MASTER
#define UWB_PROGRAMMER_MASTER 0
#endif
UbpConfig gUbpConfig = {0xE2E11001, {2,0,0,0,0,0,0,UWB_PROGRAMMER_MASTER ? 1 : 2}, 500};
static const char *gRole = UWB_PROGRAMMER_TAG ? "tag" : (UWB_PROGRAMMER_MASTER ? "master" : "slave");
static const char *gModel = UWB_PROGRAMMER_TAG ? "Type2DK" : "Type2BP";
static const char *gRunState="booting";
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
static void hello(void) {
    char mac[17]; hex_mac(mac,gUbpConfig.mac,8);
    PRINTF("{\"v\":1,\"kind\":\"hello\",\"model\":\"%s\",\"role\":\"%s\",\"state\":\"%s\",\"version\":\"1.0.0\",\"mac\":\"%s\",\"interval_ms\":%lu,\"boot\":\"%08lx\",\"dropped\":%lu}\r\n",gModel,gRole,gRunState,mac,(unsigned long)gUbpConfig.interval_ms,gBoot,gDrops);
}
void UbpState(const char *state,int code) {
    if(strcmp(state,"configured_restart_required") && strcmp(state,"unknown_command")) gRunState=state;
    PRINTF("{\"v\":1,\"kind\":\"status\",\"state\":\"%s\",\"code\":%d,\"boot\":\"%08lx\"}\r\n",state,code,gBoot);
}
void UbpConsoleInit(void) {
    uint16_t length=0; UbpConfig saved;
    if(PDM_Init()!=0) UbpState("pdm_init_failed",-1);
    if(UWB_PROGRAMMER_TAG) { gUbpConfig.mac[6]=1; gUbpConfig.mac[7]=1; gUbpConfig.interval_ms=1000; }
    if(PDM_eReadDataFromRecord(0xE2E2,&saved,sizeof(saved),&length)==PDM_E_STATUS_OK && length==sizeof(saved) && saved.magic==0xE2E11001 && saved.interval_ms>=100 && saved.interval_ms<=10000) gUbpConfig=saved;
    gBoot=(unsigned long)xTaskGetTickCount();
    RNG_GetRandomNo((uint32_t *)&gBoot);
#if UWBFTR_UL_TDoA_Anchor
    gEvents=xQueueCreate(16,sizeof(UbpEvent));
    if(!gEvents) UbpState("queue_error",-1);
#endif
    hello();
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
        /* One complete UART call; timestamp words are never converted to floating point. */
        PRINTF("{\"v\":1,\"kind\":\"rx\",\"peer_mac\":\"%s\",\"frame_type\":\"%s\",\"frame_number\":\"%lu\",\"status\":%u,\"message_control\":%u,\"timestamp_bits\":%u,\"tx_timestamp_bits\":%u,\"rx_timestamp_hex\":\"%08lx%08lx\",\"tx_timestamp_hex\":%s,\"azimuth_deg\":%.6f,\"elevation_deg\":%.6f,\"az_fom\":%u,\"el_fom\":%u,\"nlos\":%u,\"boot\":\"%08lx\"}\r\n",peer,m->frame_type==0?"BLINK":"SYNC",(unsigned long)m->frame_number,m->status,m->message_control,bits,tx_bits,(unsigned long)high,(unsigned long)low,tx,(double)m->aoa_azimuth/128.,(double)m->aoa_elevation/128.,m->aoa_azimuth_FOM,m->aoa_elevation_FOM,m->nLos,gBoot);
    }
#endif
}
int UbpPoll(void) {
    char c; drain();
    while(DbgConsole_TryGetchar(&c)==kStatus_Success) {
        if(c=='\r') continue;
        if(c!='\n') { if(gInputLen<sizeof(gInput)-1) gInput[gInputLen++]=c; else {gInputLen=0;UbpState("command_too_long",-1);} continue; }
        gInput[gInputLen]=0; gInputLen=0;
        if(strcmp(gInput,"E2E HELLO")==0) hello();
        else if(strcmp(gInput,"E2E START")==0) return 1;
        else if(strcmp(gInput,"E2E STOP")==0) return 2;
        else if(strncmp(gInput,"E2E CONFIG ",11)==0) {
            char mac[17]; unsigned long interval; UbpConfig next=gUbpConfig;
            if(sscanf(gInput+11,"%16s %lu",mac,&interval)!=2 || strlen(mac)!=16 || interval<100 || interval>10000) { UbpState("invalid_config",-1); continue; }
            int valid=1;
            for(unsigned i=0;i<8;i++) { char pair[3]={mac[2*i],mac[2*i+1],0}; char *end; unsigned long value=strtoul(pair,&end,16); if(*end || value>255) valid=0; next.mac[i]=(uint8_t)value; }
            if(!valid) {UbpState("invalid_mac",-1);continue;}
            next.interval_ms=(uint32_t)interval;
            int status=PDM_eSaveRecordData(0xE2E2,&next,sizeof(next));
            if(status==PDM_E_STATUS_OK) {gUbpConfig=next;UbpState("configured_restart_required",0);hello();} else UbpState("config_save_failed",status);
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
