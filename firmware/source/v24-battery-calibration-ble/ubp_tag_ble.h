#ifndef UBP_TAG_BLE_H
#define UBP_TAG_BLE_H
void UbpTagBleStart(void);
int UbpTagBleReady(void);
void UbpTagBleAdvertise(void);
unsigned UbpTagBleWindowRemaining(void);
void UbpTagBleClose(void);
int UbpTagBleClosed(void);
#endif
