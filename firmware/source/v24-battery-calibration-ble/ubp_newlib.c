/* Bounded newlib heap for the standalone GCC build, separate from FreeRTOS heap. */
#include "FreeRTOS.h"
#include "task.h"
#include <sys/types.h>
#include <stddef.h>
#include <stdint.h>
#include <errno.h>
#include <reent.h>
extern char _pvHeapStart, _pvHeapLimit;
static char *heap_end;
void *_sbrk(ptrdiff_t increment) {
    if(!heap_end)heap_end=&_pvHeapStart;
    uintptr_t current=(uintptr_t)heap_end;
    uintptr_t low=(uintptr_t)&_pvHeapStart, high=(uintptr_t)&_pvHeapLimit;
    if((increment>=0 && (uintptr_t)increment>high-current) ||
       (increment<0 && (uintptr_t)(-(increment+1))+1>current-low)) {
        errno=ENOMEM;return (void *)-1;
    }
    char *previous=heap_end;heap_end+=increment;return previous;
}
void __malloc_lock(struct _reent *context) {
    (void)context;if(xTaskGetSchedulerState()!=taskSCHEDULER_NOT_STARTED)vTaskSuspendAll();
}
void __malloc_unlock(struct _reent *context) {
    (void)context;if(xTaskGetSchedulerState()!=taskSCHEDULER_NOT_STARTED)(void)xTaskResumeAll();
}
