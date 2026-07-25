#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "fusion.h"

#define SENSOR_NOISE_FLOOR 0.001

typedef enum {
    TIER_1_LOCAL_SENSOR,
    TIER_2_NEIGHBOR_CONSENSUS,
    TIER_3_STATIC_DEFAULT
} FailoverTier;

typedef struct {
    SensorHealth temp_health;
    SensorHealth smoke_health;
    SensorHealth flame_health;
    FailoverTier active_tier;
    char         status_str[48];
} NodeSensorState;

void sensor_state_init(NodeSensorState *s, uint32_t now_ms);
void sensor_state_update(NodeSensorState *s, float temp, float smoke,
                         bool flame, uint32_t now_ms);
bool sensor_state_all_healthy(const NodeSensorState *s);
