#include "fusion.h"
#include <math.h>
#include <string.h>

void dual_path_init(DualPathFilter *f, float alpha, float delta_th, float rate_th) {
    f->ewma = 0.0f;
    f->prev_raw = 0.0f;
    f->initialized = false;
    f->alpha = alpha;
    f->delta_threshold = delta_th;
    f->rate_threshold = rate_th;
    f->rate_trigger_count = 0;
}

bool dual_path_update(DualPathFilter *f, float raw_sample) {
    bool triggered = false;
    if (!f->initialized) {
        f->ewma = raw_sample;
        f->prev_raw = raw_sample;
        f->initialized = true;
        return false;
    }

    float old_ewma = f->ewma;
    f->ewma = f->alpha * raw_sample + (1.0f - f->alpha) * f->ewma;

    float delta = fabsf(f->ewma - old_ewma);
    if (delta >= f->delta_threshold) {
        triggered = true;
    }

    float rate = raw_sample - f->prev_raw;
    f->prev_raw = raw_sample;

    if (fabsf(rate) >= f->rate_threshold) {
        f->rate_trigger_count++;
        if (f->rate_trigger_count >= 2) {
            triggered = true;
            f->rate_trigger_count = 0;
        }
    } else {
        f->rate_trigger_count = 0;
    }

    return triggered;
}

void sensor_health_init(SensorHealth *h, uint32_t now_ms) {
    memset(h->ring_buffer, 0, sizeof(h->ring_buffer));
    h->idx = 0;
    h->healthy = true;
    h->first_sample_ms = now_ms;
    h->last_sample_ms = now_ms;
}

void sensor_health_update(SensorHealth *h, float sample,
                          float phys_min, float phys_max, uint32_t now_ms) {
    if (isnan(sample) || sample < phys_min || sample > phys_max) {
        h->healthy = false;
        return;
    }
    h->ring_buffer[h->idx % 10] = sample;
    h->idx++;
    h->last_sample_ms = now_ms;

    if (h->idx >= 10 && (h->last_sample_ms - h->first_sample_ms >= 30000)) {
        float var = compute_variance(h->ring_buffer, 10);
        if (var < SENSOR_NOISE_FLOOR) {
            h->healthy = false;
            return;
        }
    }
    h->healthy = true;
}

float clampf(float v, float lo, float hi) {
    if (v < lo) return lo;
    if (v > hi) return hi;
    return v;
}

float compute_variance(const float *buf, int len) {
    float mean = 0.0f;
    for (int i = 0; i < len; i++) mean += buf[i];
    mean /= len;
    float var = 0.0f;
    for (int i = 0; i < len; i++) {
        float d = buf[i] - mean;
        var += d * d;
    }
    return var / len;
}
