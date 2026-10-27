#include "board.h"
#include "fsl_usart.h"
#include <stdint.h>
#include "FreeRTOS.h"
#include "task.h"
static void out(const char *s) {
    while(*s) { uint8_t ch=(uint8_t)*s++; USART_WriteBlocking((USART_Type *)BOARD_DEBUG_UART_BASEADDR,&ch,1); }
}
static void hex(uint32_t n) {
    char text[9]; for(unsigned i=0;i<8;i++) text[i]="0123456789abcdef"[(n>>(28-4*i))&15];text[8]=0;out(text);
}
void UbpAssert(const char *file,unsigned line) {
    __disable_irq();out("\r\nUBP_ASSERT ");out(file);out(" task=");out(pcTaskGetName(0));out(" water=0x");hex(uxTaskGetStackHighWaterMark(0));out(" line=0x");hex(line);out(" ipsr=0x");hex(__get_IPSR());out("\r\n");for(;;){}
}
__attribute__((used,noinline)) void UbpFault(uint32_t *stack) {
    __disable_irq();out("\r\nUBP_FAULT pc=0x");hex(stack[6]);out(" lr=0x");hex(stack[5]);out(" cfsr=0x");hex(SCB->CFSR);out(" hfsr=0x");hex(SCB->HFSR);out(" bfar=0x");hex(SCB->BFAR);out("\r\n");for(;;){}
}
__attribute__((naked)) void HardFault_Handler(void) {
    __asm volatile("tst lr,#4\n ite eq\n mrseq r0,msp\n mrsne r0,psp\n b UbpFault\n");
}
