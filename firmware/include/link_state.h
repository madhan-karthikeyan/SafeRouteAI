#pragma once

#include <stdint.h>
#include <stdbool.h>

#define MAX_NODES 15
#define STALE_TIMEOUT_MS 6000
#define REFRESH_INTERVAL_MS 2000

typedef struct {
    uint16_t node_id;
    uint32_t seq_num;
    uint32_t last_update_ms;
    float    edge_cost;
    float    temp_c;
    float    smoke_ppm;
    bool     flame_detected;
    bool     has_data;
} LinkStateEntry;

typedef struct {
    LinkStateEntry entries[MAX_NODES];
    uint8_t        count;
} LinkStateTable;

void link_state_init(LinkStateTable *tbl);
int  link_state_find(LinkStateTable *tbl, uint16_t node_id);
void link_state_upsert(LinkStateTable *tbl, uint16_t node_id, uint32_t seq_num,
                       uint32_t now_ms, float edge_cost, float temp_c,
                       float smoke_ppm, bool flame_detected);
void link_state_age_edges(LinkStateTable *tbl, uint32_t now_ms, uint16_t own_id);
