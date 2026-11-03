#ifndef UBP_SURVEY_H
#define UBP_SURVEY_H
#include <stdint.h>
#include "UwbApi.h"
/* Wire v1: version, mode, request LE32, peer MAC[8], session LE32, lease LE16 ms.
 * mode 0 restores autonomous UWB; 1 holds RF; 2 TWR responder; 3 TWR initiator.
 * Commands expire in <=30 s, including time spent waiting in the queue. */
typedef struct {uint8_t mode;uint32_t request;uint8_t peer[8];uint32_t session;uint16_t lease_ms;uint32_t received_tick;} UbpSurveyCommand;
void UbpSurveyInit(void);
int UbpSurveySubmit(const uint8_t *,unsigned);
int UbpSurveyTake(UbpSurveyCommand *);
int UbpSurveyExpired(void);
void UbpSurveyResult(const UbpSurveyCommand *,uint16_t,uint32_t);
void UbpSurveyDisconnect(void);
void UbpSurveyStatus(uint8_t out[24]);
int UbpSurveyMeasurement(const phRangingData_t *);
void UbpSurveyDrain(void);
#endif
