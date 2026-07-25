#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "link_state.h"
#include "graph_topology.h"

#define SHELTER_THRESHOLD 100000.0
#define BLOCK_MULTIPLIER  1000000.0
#define HOLD_DOWN_MS      1800

typedef struct {
    uint16_t next_hop;
    float    cost_to_exit;
    bool     shelter_in_place;
} DijkstraResult;

typedef struct {
    bool     flame_detected_on_current;
    bool     flame_detected_on_next;
    float    best_cost_to_exit;
    bool     rerouted_from_original;
    float    deciding_edge_S_norm;
    float    deciding_edge_T_norm;
} EdgeDecision;

typedef enum {
    LED_GREEN,
    LED_YELLOW,
    LED_RED_PULSE,
    LED_WHITE_STROBE
} LedColor;

typedef struct {
    float    cost;
    bool     visited;
    uint16_t prev;
    bool     flame_blocked;
    bool     is_exit;
} DijkstraState;

void     routing_init(void);
float    compute_edge_cost(float T_norm, float S_norm, float O_norm,
                           float base_dist, bool flame, float cap);
DijkstraResult routing_compute(uint16_t own_id,
                                const LinkStateTable *table,
                                const BuildingGraph *graph);
bool     hold_down_should_switch(uint16_t new_next_hop, uint16_t current_next_hop,
                                 float new_cost, bool flame_on_current_edge,
                                 uint32_t now_ms);
LedColor choose_led_state(const EdgeDecision *d, DijkstraResult *res);
