#include "sensor_drivers.h"

#ifdef REAL_HARDWARE

#include <DHT.h>
#include <driver/adc.h>

static DHT dht(DHT_PIN, DHT_TYPE);

void sensor_drivers_init(void) {
    dht.begin();
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(MQ2_ADC_CHANNEL, ADC_ATTEN_DB_11);
    adc1_config_channel_atten(FLAME_ADC_CHANNEL, ADC_ATTEN_DB_11);
}

float sensor_read_temperature(void) {
    float t = dht.readTemperature();
    if (isnan(t)) return 25.0f;
    return t;
}

float sensor_read_smoke(void) {
    int raw = adc1_get_raw(MQ2_ADC_CHANNEL);
    float voltage = raw * (3.3f / 4095.0f);
    float ratio = voltage / 3.3f;
    float ppm = 1000.0f * (1.0f - ratio);
    if (ppm < 0) ppm = 0;
    return ppm;
}

bool sensor_read_flame(void) {
    int raw = adc1_get_raw(FLAME_ADC_CHANNEL);
    return raw < 500;
}

#endif
