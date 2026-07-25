#include "leds.h"
#include <FastLED.h>

static CRGB leds[NUM_LEDS];
static LedCommand current_cmd = { LED_GREEN, 1, 0.0f };
static int scroll_offset = 0;
static unsigned long last_tick = 0;

void leds_init(void) {
    FastLED.addLeds<WS2812B, 2, GRB>(leds, NUM_LEDS);
    FastLED.setBrightness(64);
    FastLED.clear();
    FastLED.show();
}

void leds_set_command(LedCommand cmd) {
    current_cmd = cmd;
}

static void fill_color(CRGB c) {
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = c;
    }
}

static void chase_animation(CRGB base, int dir, float pulse) {
    FastLED.clear();
    int center = (scroll_offset % NUM_LEDS + NUM_LEDS) % NUM_LEDS;
    int spread = 3 + (int)(pulse * 5);
    uint8_t brightness = 64 + (uint8_t)(pulse * 191);
    for (int i = -spread; i <= spread; i++) {
        int pos = (center + dir * i + NUM_LEDS) % NUM_LEDS;
        uint8_t b = brightness - (abs(i) * 30);
        leds[pos] = base;
        leds[pos].nscale8(b);
    }
}

static void red_pulse(unsigned long now) {
    uint8_t brightness = (sin8((now >> 4) & 0xFF) / 2) + 128;
    fill_color(CRGB::Red);
    FastLED.setBrightness(brightness);
}

static void white_strobe(unsigned long now) {
    bool on = ((now / 250) & 1);
    if (on) {
        fill_color(CRGB::White);
        FastLED.setBrightness(255);
    } else {
        FastLED.clear();
    }
}

void leds_task(void *param) {
    (void)param;
    leds_init();

    while (true) {
        unsigned long now = millis();

        switch (current_cmd.color) {
            case LED_GREEN:
                chase_animation(CRGB::Green, current_cmd.direction, current_cmd.pulse_rate);
                FastLED.setBrightness(64);
                break;
            case LED_YELLOW:
                chase_animation(CRGB::Yellow, current_cmd.direction, current_cmd.pulse_rate);
                FastLED.setBrightness(96);
                break;
            case LED_RED_PULSE:
                red_pulse(now);
                break;
            case LED_WHITE_STROBE:
                white_strobe(now);
                break;
        }

        FastLED.show();
        scroll_offset = (scroll_offset + current_cmd.direction + NUM_LEDS) % NUM_LEDS;
        delay(50);
    }
}
