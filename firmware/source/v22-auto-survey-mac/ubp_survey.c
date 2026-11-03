#include "phUwb_BuildConfig.h"
#include "ubp_survey.h"
#include "uwb_programmer_console.h"
#include "FreeRTOS.h"
#include "queue.h"
#include "task.h"
#include "fsl_debug_console.h"
#include <string.h>
#if !UWB_PROGRAMMER_TAG
#include "ubp_ble.h"
#endif
static QueueHandle_t commands,records;
static UbpSurveyCommand active;
static uint16_t last_status,sample_index;
static uint32_t active_handle;
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));}
static void put16(uint8_t *p,uint16_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);}
static uint32_t crc32(const uint8_t *p,unsigned n){uint32_t c=0xffffffff;for(unsigned i=0;i<n;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^((0-(c&1))&0xedb88320);}return ~c;}
void UbpSurveyInit(void){commands=xQueueCreate(4,sizeof(UbpSurveyCommand));records=xQueueCreate(16,20);memset(&active,0,sizeof(active));}
int UbpSurveySubmit(const uint8_t *p,unsigned n){
    if(n!=20 || !commands || p[0]!=1 || p[1]>3)return 0;
    UbpSurveyCommand c;memset(&c,0,sizeof(c));c.mode=p[1];c.request=get32(p+2);memcpy(c.peer,p+6,8);c.session=get32(p+14);c.lease_ms=p[18]|((uint16_t)p[19]<<8);c.received_tick=xTaskGetTickCount();
    if(!c.request)return 0;
    if(c.mode && (c.lease_ms<1000 || c.lease_ms>30000))return 0;
    if(c.mode>=2 && (!c.session || !memcmp(c.peer,gUbpConfig.mac,8)))return 0;
    return xQueueSend(commands,&c,0)==pdPASS;
}
int UbpSurveyTake(UbpSurveyCommand *c){
    if(!commands || xQueueReceive(commands,c,0)!=pdPASS)return 0;
    if(c->mode && (TickType_t)(xTaskGetTickCount()-c->received_tick)>=pdMS_TO_TICKS(c->lease_ms)){c->mode=0;c->session=0;}
    return 1;
}
int UbpSurveyExpired(void){return active.mode && (TickType_t)(xTaskGetTickCount()-active.received_tick)>=pdMS_TO_TICKS(active.lease_ms);}
void UbpSurveyResult(const UbpSurveyCommand *c,uint16_t status,uint32_t handle){
    taskENTER_CRITICAL();active=*c;last_status=status;active_handle=handle;sample_index=0;taskEXIT_CRITICAL();
    if(records)xQueueReset(records);
    PRINTF("{\"v\":1,\"kind\":\"survey_status\",\"request\":%lu,\"mode\":%u,\"session\":%lu,\"status\":%u}\r\n",(unsigned long)c->request,c->mode,(unsigned long)c->session,status);
}
void UbpSurveyDisconnect(void){
    if(!commands)return;
    UbpSurveyCommand c;memset(&c,0,sizeof(c));c.request=active.request?active.request:1;
    xQueueReset(commands);xQueueSendToFront(commands,&c,0);
}
void UbpSurveyStatus(uint8_t out[24]){
    taskENTER_CRITICAL();out[0]=1;out[1]=active.mode;put16(out+2,last_status);put32(out+4,active.request);put32(out+8,active.session);memcpy(out+12,active.peer,8);taskEXIT_CRITICAL();put32(out+20,crc32(out,20));
}
int UbpSurveyMeasurement(const phRangingData_t *r){
#if UWBFTR_TWR
    if(!r || active.mode<2 || r->sessionHandle!=active_handle)return 0;
    if(r->ranging_measure_type!=MEASUREMENT_TYPE_TWOWAY)return 0;
    for(unsigned i=0;i<r->no_of_measurements;i++){
        const phRangingMesr_t *m=&r->ranging_meas.range_meas_twr[i];
        if(r->mac_addr_mode_indicator==0){if(memcmp(m->mac_addr,active.peer+6,2))continue;}
        else if(memcmp(m->mac_addr,active.peer,8))continue;
        uint8_t out[20]={1,0x54};put32(out+2,active.request);put16(out+6,++sample_index);put32(out+8,(uint32_t)m->distance*10);out[12]=m->status;out[13]=m->nLos;put16(out+14,(uint16_t)active.session);put32(out+16,crc32(out,16));
        if(records)xQueueSend(records,out,0);
    }
    return 1;
#else
    (void)r;return 0;
#endif
}
void UbpSurveyDrain(void){
    uint8_t p[20];
    for(unsigned i=0;i<8 && records && xQueueReceive(records,p,0)==pdPASS;i++){
#if !UWB_PROGRAMMER_TAG
        UbpBleSurveyPacket(p);
#endif
        PRINTF("{\"v\":1,\"kind\":\"survey_twr\",\"request\":%lu,\"sample\":%u,\"distance_mm\":%lu,\"status\":%u,\"nlos\":%u}\r\n",(unsigned long)get32(p+2),(unsigned)(p[6]|((uint16_t)p[7]<<8)),(unsigned long)get32(p+8),p[12],p[13]);
    }
}
