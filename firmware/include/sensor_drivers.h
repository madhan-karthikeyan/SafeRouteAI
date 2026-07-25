#pragma once

#include <stdint.h>
#include <stdbool.h>

#ifdef REAL_HARDWARE

#include <DHT.h>
#include <driver/adc.h>

#define DHT_PIN 4
#define DHT_TYPE DHT22
#define MQ2_ADC_CHANNEL ADC1_CHANNEL_0
#define FLAME_ADC_CHANNEL ADC1_CHANNEL_3

void sensor_drivers_init(void);
float sensor_read_temperature(void);
float sensor_read_smoke(void);
bool  sensor_read_flame(void);

#else

static inline void sensor_drivers_init(void) {}
static inline float sensor_read_temperature(void) { return 25.0f; }
static inline float sensor_read_smoke(void) { return 0.0f; }
static inline bool  sensor_read_flame(void) { return false; }

#endif
