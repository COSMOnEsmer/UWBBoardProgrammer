"""Bounded RF clock interpolation; missing BLE records do not change RF epochs.

Map a BLINK only between measured SYNC timestamps, never by extrapolating.
Recent skip-one SYNC interpolation errors provide a validation noise estimate.
Boot/disconnect/counter-domain changes still require a new clock epoch.
"""
from collections import deque
from bisect import bisect_left
import math
import time

from .models import TICK_S, C_M_S


class AwaitingSync(ValueError):
    """A fresh later RF SYNC is needed to bracket this BLINK."""


class InterpolatedClockFit:
    def __init__(self):
        self.samples=deque(maxlen=16)
        self.last=0.;self.rms_s=float('inf');self.slope=1.
        self.max_segment_s=1.5
        self.validation_count=0

    def add(self,rx,master_tx,flight_m,rx_bias_m=0):
        if not all(isinstance(value,int) for value in (rx,master_tx)):
            raise ValueError('Clock samples must be exact integer RF timestamps')
        if not math.isfinite(flight_m) or flight_m<0:raise ValueError('Invalid RF propagation distance')
        flight_ticks=flight_m/(C_M_S*TICK_S)
        if self.samples:
            previous=self.samples[-1]
            if rx==previous[0] and master_tx==previous[1]:return
            if rx<=previous[0] or master_tx<=previous[1]:
                raise ValueError('RF SYNC timestamps moved backwards; reset clock domain')
            # Segment duration is defined in the MASTER RF domain. Slave ppm skew
            # must not turn an allowed 1.5 s master bracket into a false gap.
            # A genuinely long master RF interval still needs fresh validation.
            if (master_tx-previous[1])*TICK_S>self.max_segment_s:
                self.samples.clear()
        self.samples.append((rx,master_tx,flight_ticks));self.last=time.monotonic()
        if len(self.samples)>1:
            left,right=list(self.samples)[-2:]
            self.slope=(right[1]-left[1])/(right[0]-left[0])
        errors=[];items=list(self.samples)
        for left,middle,right in zip(items,items[1:],items[2:]):
            span=right[0]-left[0]
            if (right[1]-left[1])*TICK_S>2*self.max_segment_s:continue
            # Center integer counters before converting differences to float.
            predicted=(middle[0]-left[0])*(right[1]-left[1])/span
            error=((middle[1]-left[1])-predicted)*TICK_S
            errors.append(error)
        errors=errors[-4:];self.validation_count=len(errors)
        self.rms_s=math.sqrt(sum(value*value for value in errors)/len(errors)) if errors else float('inf')

    def ready(self):
        return (len(self.samples)>=6 and self.validation_count>=4 and
                (self.samples[-1][1]-self.samples[0][1])*TICK_S>=1 and
                time.monotonic()-self.last<2.5 and self.rms_s<2e-9 and
                abs(self.slope-1)<200e-6)

    def not_ready_reason(self):
        if len(self.samples)<6:return 'Need at least 6 RF SYNC samples'
        if self.validation_count<4:return 'Need 4 SYNC validation errors'
        if (self.samples[-1][1]-self.samples[0][1])*TICK_S<1:return 'RF SYNC span is shorter than 1 second'
        if time.monotonic()-self.last>=2.5:return 'Latest RF SYNC is older than 2.5 seconds'
        if not self.rms_s<2e-9:return 'Clock validation exceeds 2 ns'
        if not abs(self.slope-1)<200e-6:return 'RF clock skew exceeds 200 ppm'
        return ''

    def correct(self,rx,bias_m=0):
        if not self.ready():raise AwaitingSync('Waiting for six validated fresh RF SYNC samples')
        items=list(self.samples);index=bisect_left([item[0] for item in items],rx)
        if index==len(items):raise AwaitingSync('Waiting for the next RF SYNC to bracket BLINK')
        if index==0:
            if rx==items[0][0]:return items[0][1]+round(items[0][2]-bias_m/(C_M_S*TICK_S))
            raise ValueError('BLINK predates available RF clock samples')
        left,right=items[index-1],items[index]
        span=right[0]-left[0]
        if (right[1]-left[1])*TICK_S>self.max_segment_s:raise ValueError('RF SYNC bracket is too wide')
        slope=(right[1]-left[1])/span
        if abs(slope-1)>200e-6:raise ValueError('RF clock skew exceeds supported range')
        fraction=(rx-left[0])/span
        flight=left[2]+fraction*(right[2]-left[2])
        return left[1]+round((rx-left[0])*slope+flight-bias_m/(C_M_S*TICK_S))
