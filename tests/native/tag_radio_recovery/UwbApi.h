/* Host-only API stand-ins for lifecycle fault injection, never in firmware. */
#ifndef UBP_TEST_API_H
#define UBP_TEST_API_H
#include <stdint.h>
typedef unsigned char tUWBAPI_STATUS;
typedef int eNotificationType;
typedef struct phRangingData phRangingData_t;
typedef struct {unsigned parameter,value;} UWB_AppParams_List_t;
typedef struct {unsigned noOfControlees,deviceRole,multiNodeMode,macAddrMode,deviceType;uint8_t deviceMacAddr[8],dstMacAddr[8];} phRangingParams_t;
#define UWBAPI_STATUS_OK 0
#define UWBAPI_STATUS_FAILED 2
#define UWBAPI_STATUS_SESSION_NOT_EXIST 0x11
#define UWBAPI_STATUS_HPD_WAKEUP 0xfc
#define UWBAPI_STATUS_TIMEOUT 0xfd
#define UWBAPI_SESSION_ERROR 0xff
#define UWBAPI_SESSION_ACTIVATED 2
#define UWBD_RANGING_SESSION 0
#define UWB_SET_APP_PARAM_VALUE(ignored,value) {0,(unsigned)(value)}
enum {kUWB_RangingRoundUsage_DS_TWR=1,kUWB_RfFrameConfig_SP3,kUWB_StsConfig_StaticSts,kUWB_RfFrameConfig_Sfd_Sts,
      kUWB_RangingMethod_TDoA,kUWB_DeviceRole_Initiator,kUWB_DeviceRole_Responder,kUWB_DeviceRole_UT_Tag,
      kUWB_MultiNodeMode_UniCast,kUWB_MultiNodeMode_OnetoMany,SHORT_MAC_ADDRESS_MODE,EXTENDED_MAC_ADDRESS_MODE_WITH_HEADER,
      kUWB_DeviceType_Controller,kUWB_DeviceType_Controlee};
tUWBAPI_STATUS UwbApi_SessionInit(uint32_t,unsigned);
tUWBAPI_STATUS UwbApi_SessionDeinit(uint32_t);
tUWBAPI_STATUS UwbApi_StopRangingSession(uint32_t);
tUWBAPI_STATUS UwbApi_StartRangingSession(uint32_t);
tUWBAPI_STATUS UwbApi_SetDefaultCoreConfigs(void);
tUWBAPI_STATUS UwbApi_SetAppConfigMultipleParams(uint32_t,unsigned,const UWB_AppParams_List_t*);
tUWBAPI_STATUS UwbApi_SetRangingParams(uint32_t,const phRangingParams_t*);
tUWBAPI_STATUS UwbApi_GetSessionState(uint32_t,uint8_t*);
#endif
