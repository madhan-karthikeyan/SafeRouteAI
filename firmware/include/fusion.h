#pragma once

#include <stdint.h>
#include <stdbool.h>

#define SENSOR_HEALTH_RING_SIZE 10
#define SENSOR_STUCK_WINDOW_MS  5000

typedef struct {
    float ring_buffer[SENSOR_HEALTH_RING_SIZE];
    uint8_t idx;
    bool    healthy;
    uint32_t first_sample_ms;
    uint32_t last_sample_ms;
} SensorHealth;

typedef struct {
    float ewma;
    float prev_raw;
    bool  initialized;

    float rate_threshold;
    float delta_threshold;
    float alpha;

    uint8_t rate_trigger_count;
} DualPathFilter;

void dual_path_init(DualPathFilter *f, float alpha, float delta_th, float rate_th);
bool dual_path_update(DualPathFilter *f, float raw_sample);

void sensor_health_init(SensorHealth *h, uint32_t now_ms);
void sensor_health_update(SensorHealth *h, float sample,
                          float phys_min, float phys_max, uint32_t now_ms);

float clampf(float v, float lo, float hi);
float compute_variance(const float *buf, int len);
