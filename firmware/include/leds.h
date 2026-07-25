#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "routing.h"

#define NUM_LEDS 30

typedef struct {
    LedColor color;
    int8_t   direction;   // +1 or -1, scroll direction
    float    pulse_rate;  // 0.0–1.0 normalized severity
} LedCommand;

void leds_init(void);
void leds_set_command(LedCommand cmd);
void leds_task(void *param);
