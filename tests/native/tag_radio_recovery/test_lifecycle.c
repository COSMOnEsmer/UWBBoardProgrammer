/* Executes the actual candidate's static lifecycle functions on host C.
 * The fake API exercises failure propagation, not RF accuracy or power. */
#include <stdio.h>
#define UBP_RADIO_UNIT_TEST 1
#include "tag_auto_survey.c"
UbpConfig gUbpConfig={0,{2,0,0,0,0,0,1,1},1000};
uint32_t gUbpConfigReady=1;
enum {INIT,DEINIT,STOP,START,CORE,CONFIG,RANGING,STATE};
typedef struct {int operation;unsigned status;} Reply;
static Reply replies[32];static unsigned count,index_;static int bad;static uint8_t fake_state=2;
static void begin(void){count=index_=0;bad=0;fake_state=2;hpd_recoveries=0;}
static void push(int operation,unsigned status){replies[count++]=(Reply){operation,status};}
static unsigned result(int operation){
    if(index_>=count || replies[index_].operation!=operation){bad=1;return 2;}
    return replies[index_++].status;
}
tUWBAPI_STATUS UwbApi_SessionInit(uint32_t id,unsigned type){(void)id;(void)type;return result(INIT);}
tUWBAPI_STATUS UwbApi_SessionDeinit(uint32_t id){(void)id;return result(DEINIT);}
tUWBAPI_STATUS UwbApi_StopRangingSession(uint32_t id){(void)id;return result(STOP);}
tUWBAPI_STATUS UwbApi_StartRangingSession(uint32_t id){(void)id;return result(START);}
tUWBAPI_STATUS UwbApi_SetDefaultCoreConfigs(void){return result(CORE);}
tUWBAPI_STATUS UwbApi_SetAppConfigMultipleParams(uint32_t id,unsigned n,const UWB_AppParams_List_t*p){(void)id;(void)n;(void)p;return result(CONFIG);}
tUWBAPI_STATUS UwbApi_SetRangingParams(uint32_t id,const phRangingParams_t*p){(void)id;(void)p;return result(RANGING);}
tUWBAPI_STATUS UwbApi_GetSessionState(uint32_t id,uint8_t*s){(void)id;*s=fake_state;return result(STATE);}
static void good_start(void){push(INIT,0);push(CONFIG,0);push(RANGING,0);push(START,0);push(STATE,0);}
#define CHECK(value) do{if(!(value) || bad || index_!=count){fprintf(stderr,"Failure at %d; calls %u/%u\n",__LINE__,index_,count);return 1;}}while(0)
int main(void){
    UbpSurveyCommand command={0};command.mode=2;command.session=123;uint32_t session;
    begin();session=0;push(INIT,0xfc);push(CORE,0);good_start();
    CHECK(start_tag(&command,&session)==0 && session==123 && hpd_recoveries==1);
    begin();session=0;push(INIT,0xfc);push(CORE,2);
    CHECK(start_tag(&command,&session)==2 && session==0 && hpd_recoveries==1);
    begin();session=0;push(INIT,0xfc);push(CORE,0);push(INIT,0xfc);
    CHECK(start_tag(&command,&session)==0xfc && session==0 && hpd_recoveries==1);
    begin();session=99;push(STOP,0xfd);
    CHECK(transition_tag(&command,&session)==0xfd && session==99);
    begin();session=99;push(STOP,0);push(DEINIT,0xfd);
    CHECK(transition_tag(&command,&session)==0xfd && session==99);
    begin();session=99;push(STOP,0xfc);push(CORE,0);good_start();
    CHECK(transition_tag(&command,&session)==0 && session==123 && hpd_recoveries==1);
    begin();session=0;push(INIT,0);push(CONFIG,2);push(DEINIT,0xfd);
    CHECK(start_tag(&command,&session)==2 && session==123);
    begin();session=0;fake_state=3;good_start();push(DEINIT,0);
    CHECK(start_tag(&command,&session)==2 && session==0);
    begin();session=88;push(INIT,0xfd);
    CHECK(start_tag(&command,&session)==0xfd && session==0);
    begin();command.mode=1;session=99;push(STOP,0);push(DEINIT,0);
    CHECK(transition_tag(&command,&session)==0 && session==0);
    good_ranges=failed_ranges=0;UbpTagRadioMeasurement(0);UbpTagRadioMeasurement(0x21);
    uint8_t diagnostic[20];UbpTagRadioDiagnostic(diagnostic);
    printf("DIAGNOSTIC ");for(unsigned i=0;i<20;i++)printf("%02x",diagnostic[i]);puts("");
    puts("10 lifecycle fault-injection scenarios passed; RF and current not simulated.");return 0;
}
