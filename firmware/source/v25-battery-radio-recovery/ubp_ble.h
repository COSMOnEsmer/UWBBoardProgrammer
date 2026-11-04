#ifndef UBP_BLE_H
#define UBP_BLE_H
#include "UwbApi.h"
void UbpBleStart(void);
void UbpBleMeasurement(const phRangingMesrTdoa_t *, unsigned, uint32_t, uint32_t, uint32_t);
unsigned UbpInfoJson(char *, unsigned);
void UbpBleSurveyPacket(const uint8_t packet[20]);
#endif
