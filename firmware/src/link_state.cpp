#include "link_state.h"
#include <string.h>
#include <math.h>

void link_state_init(LinkStateTable *tbl) {
    memset(tbl, 0, sizeof(LinkStateTable));
}

int link_state_find(LinkStateTable *tbl, uint16_t node_id) {
    for (int i = 0; i < (int)tbl->count; i++) {
        if (tbl->entries[i].node_id == node_id) return i;
    }
    return -1;
}

void link_state_upsert(LinkStateTable *tbl, uint16_t node_id, uint32_t seq_num,
                        uint32_t now_ms, float edge_cost, float temp_c,
                        float smoke_ppm, bool flame_detected) {
    int idx = link_state_find(tbl, node_id);
    if (idx < 0) {
        if (tbl->count >= MAX_NODES) return;
        idx = tbl->count;
        tbl->entries[idx].node_id = node_id;
        tbl->count++;
    }
    tbl->entries[idx].seq_num = seq_num;
    tbl->entries[idx].last_update_ms = now_ms;
    tbl->entries[idx].edge_cost = edge_cost;
    tbl->entries[idx].temp_c = temp_c;
    tbl->entries[idx].smoke_ppm = smoke_ppm;
    tbl->entries[idx].flame_detected = flame_detected;
    tbl->entries[idx].has_data = true;
}

void link_state_age_edges(LinkStateTable *tbl, uint32_t now_ms, uint16_t own_id) {
    for (int i = 0; i < (int)tbl->count; i++) {
        if (tbl->entries[i].node_id == own_id) continue;
        if (!tbl->entries[i].has_data) continue;
        uint32_t elapsed = now_ms - tbl->entries[i].last_update_ms;
        if (elapsed > STALE_TIMEOUT_MS) {
            float age_ratio = fminf((float)(elapsed - STALE_TIMEOUT_MS) / 60000.0f, 1.0f);
            float base = tbl->entries[i].edge_cost;
            float decayed = base * (1.0f + age_ratio * 10.0f);
            tbl->entries[i].edge_cost = decayed;

            if (elapsed > STALE_TIMEOUT_MS * 3) {
                tbl->entries[i].flame_detected = true;
            }
        }
    }
}
