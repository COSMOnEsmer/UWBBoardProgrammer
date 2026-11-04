#ifndef UBP_TAG_BLE_H
#define UBP_TAG_BLE_H
#include <stdint.h>
void UbpTagRadioDiagnostic(uint8_t out[20]);
void UbpTagRadioMeasurement(uint8_t status);
void UbpTagBleStart(void);
int UbpTagBleReady(void);
void UbpTagBleAdvertise(void);
unsigned UbpTagBleWindowRemaining(void);
void UbpTagBleClose(void);
int UbpTagBleClosed(void);
#endif
