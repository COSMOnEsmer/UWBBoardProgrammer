#ifndef UWB_PROGRAMMER_CONSOLE_H
#define UWB_PROGRAMMER_CONSOLE_H
#include <stdint.h>
#include "UwbApi.h"
typedef struct { uint32_t magic; uint8_t mac[8]; uint32_t interval_ms; } UbpConfig;
extern UbpConfig gUbpConfig;
void UbpConsoleInit(void);
int UbpPoll(void); /* 1=start, 2=stop */
void UbpState(const char *state, int code);
void UbpCallback(eNotificationType type, void *data);
int UbpApplyOtp(void);
#endif
