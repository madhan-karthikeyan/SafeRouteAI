#include "failsafe.h"
#include <string.h>
#include <stdio.h>

void sensor_state_init(NodeSensorState *s, uint32_t now_ms) {
    sensor_health_init(&s->temp_health, now_ms);
    sensor_health_init(&s->smoke_health, now_ms);
    sensor_health_init(&s->flame_health, now_ms);
    s->active_tier = TIER_1_LOCAL_SENSOR;
    strcpy(s->status_str, "all sensors healthy");
}

void sensor_state_update(NodeSensorState *s, float temp, float smoke,
                          bool flame, uint32_t now_ms) {
    sensor_health_update(&s->temp_health, temp, -20.0f, 150.0f, now_ms);
    sensor_health_update(&s->smoke_health, smoke, 0.0f, 10000.0f, now_ms);

    float flame_f = flame ? 1.0f : 0.0f;
    sensor_health_update(&s->flame_health, flame_f, 0.0f, 1.0f, now_ms);

    if (sensor_state_all_healthy(s)) {
        s->active_tier = TIER_1_LOCAL_SENSOR;
        strcpy(s->status_str, "all sensors healthy");
    } else if (!s->temp_health.healthy || !s->smoke_health.healthy) {
        s->active_tier = TIER_2_NEIGHBOR_CONSENSUS;
        snprintf(s->status_str, sizeof(s->status_str),
                 "SENSOR FAULT - using neighbor consensus");
    } else {
        s->active_tier = TIER_3_STATIC_DEFAULT;
        snprintf(s->status_str, sizeof(s->status_str),
                 "SENSOR FAULT - isolated, static default");
    }
}

bool sensor_state_all_healthy(const NodeSensorState *s) {
    return s->temp_health.healthy && s->smoke_health.healthy && s->flame_health.healthy;
}
