#include "routing.h"
#include <math.h>
#include <string.h>
#include <stdlib.h>

static uint32_t last_switch_ms = 0;
static bool     initial_path_set = false;

static uint16_t current_next_hop = 0;

void routing_init(void) {
    last_switch_ms = 0;
    initial_path_set = false;
    current_next_hop = 0;
}

float compute_edge_cost(float T_norm, float S_norm, float O_norm,
                         float base_dist, bool flame, float cap) {
    float hazard_mult = expf(2.2f * T_norm + 1.6f * S_norm);
    float congestion_term = 0.5f * O_norm * base_dist;
    float cost = base_dist * hazard_mult + congestion_term;
    if (flame) {
        cost *= BLOCK_MULTIPLIER;
    }
    return cost;
}

DijkstraResult routing_compute(uint16_t own_id,
                                const LinkStateTable *table,
                                const BuildingGraph *graph) {
    DijkstraResult result;
    result.next_hop = 0;
    result.cost_to_exit = INFINITY;
    result.shelter_in_place = false;

    double dist[MAX_NODES];
    bool visited[MAX_NODES];
    uint16_t prev[MAX_NODES];
    bool is_exit[MAX_NODES];

    for (int i = 0; i < MAX_NODES; i++) {
        dist[i] = INFINITY;
        visited[i] = false;
        prev[i] = 0;
        is_exit[i] = false;
    }

    int own_idx = -1;
    for (int i = 0; i < graph->node_count; i++) {
        if (graph->nodes[i].node_id == own_id) {
            own_idx = i;
            break;
        }
    }
    if (own_idx < 0) return result;

    for (int i = 0; i < graph->node_count; i++) {
        is_exit[i] = graph->nodes[i].is_exit;
    }

    dist[own_idx] = 0.0;

    for (int iter = 0; iter < graph->node_count; iter++) {
        int u = -1;
        double best = INFINITY;
        for (int i = 0; i < graph->node_count; i++) {
            if (!visited[i] && dist[i] < best) {
                best = dist[i];
                u = i;
            }
        }
        if (u < 0) break;
        visited[u] = true;

        uint16_t uid = graph->nodes[u].node_id;

        for (int e = 0; e < graph->edge_count; e++) {
            uint16_t neighbor_id;
            int v = -1;
            if (graph->edges[e].from == uid) {
                neighbor_id = graph->edges[e].to;
            } else if (graph->edges[e].to == uid) {
                neighbor_id = graph->edges[e].from;
            } else {
                continue;
            }
            for (int j = 0; j < graph->node_count; j++) {
                if (graph->nodes[j].node_id == neighbor_id) {
                    v = j;
                    break;
                }
            }
            if (v < 0 || visited[v]) continue;

            int ls_idx = link_state_find((LinkStateTable *)table, neighbor_id);
            bool flame = false;
            if (ls_idx >= 0 && table->entries[ls_idx].has_data) {
                flame = table->entries[ls_idx].flame_detected;
            }
            if (flame) {
                double flame_cost = dist[u] + BLOCK_MULTIPLIER * graph->edges[e].base_distance;
                if (flame_cost < dist[v]) {
                    dist[v] = flame_cost;
                    prev[v] = uid;
                }
                continue;
            }

            int own_ls = link_state_find((LinkStateTable *)table, uid);
            float T_norm = 0, S_norm = 0, O_norm = 0;

            if (own_ls >= 0 && table->entries[own_ls].has_data) {
                T_norm = clampf((table->entries[own_ls].temp_c - graph->nodes[u].T_baseline) /
                                (graph->nodes[u].T_critical - graph->nodes[u].T_baseline), 0, 1);
                S_norm = clampf((table->entries[own_ls].smoke_ppm - graph->nodes[u].S_baseline) /
                                (graph->nodes[u].S_critical - graph->nodes[u].S_baseline), 0, 1);
                O_norm = clampf(table->entries[own_ls].edge_cost / graph->nodes[u].occupant_capacity, 0, 1);
            }

            float edge_cost = compute_edge_cost(T_norm, S_norm, O_norm,
                                                 graph->edges[e].base_distance,
                                                 flame,
                                                 graph->edges[e].occupant_capacity);
            double new_dist = dist[u] + (double)edge_cost;
            if (new_dist < dist[v]) {
                dist[v] = new_dist;
                prev[v] = uid;
            }
        }
    }

    int nearest_exit = -1;
    double best_cost = INFINITY;
    for (int i = 0; i < graph->node_count; i++) {
        if (is_exit[i] && dist[i] < best_cost) {
            best_cost = dist[i];
            nearest_exit = i;
        }
    }

    result.cost_to_exit = (float)best_cost;

    if (best_cost >= SHELTER_THRESHOLD) {
        result.shelter_in_place = true;
        result.next_hop = 0;
        return result;
    }

    int walk = nearest_exit;
    while (walk >= 0) {
        uint16_t prev_id = prev[walk];
        if (prev_id == 0) break;
        if (prev_id == own_id) {
            result.next_hop = graph->nodes[walk].node_id;
            break;
        }
        int next = -1;
        for (int i = 0; i < graph->node_count; i++) {
            if (graph->nodes[i].node_id == prev_id) {
                next = i;
                break;
            }
        }
        walk = next;
    }

    if (result.next_hop == 0 && nearest_exit >= 0) {
        for (int e = 0; e < graph->edge_count; e++) {
            if (graph->edges[e].from == own_id) {
                float min_cost = INFINITY;
                int best_edge = -1;
                for (int e2 = 0; e2 < graph->edge_count; e2++) {
                    if (graph->edges[e2].from == own_id) {
                        uint16_t nid = graph->edges[e2].to;
                        for (int j = 0; j < graph->node_count; j++) {
                            if (graph->nodes[j].node_id == nid && dist[j] < min_cost) {
                                min_cost = dist[j];
                                best_edge = e2;
                            }
                        }
                    }
                }
                if (best_edge >= 0) {
                    result.next_hop = graph->edges[best_edge].to;
                }
                break;
            }
        }
    }

    return result;
}

bool hold_down_should_switch(uint16_t new_next_hop, uint16_t current_next_hop,
                              float new_cost, bool flame_on_current_edge,
                              uint32_t now_ms) {
    if (new_next_hop == 0) return false;
    if (current_next_hop == 0) {
        initial_path_set = true;
        last_switch_ms = now_ms;
        return true;
    }
    if (flame_on_current_edge) {
        last_switch_ms = now_ms;
        return true;
    }
    if (!initial_path_set) {
        initial_path_set = true;
        last_switch_ms = now_ms;
        return true;
    }
    uint32_t elapsed = now_ms - last_switch_ms;
    if (elapsed < HOLD_DOWN_MS && new_cost > 0.7f * SHELTER_THRESHOLD) {
        return false;
    }
    last_switch_ms = now_ms;
    return true;
}

LedColor choose_led_state(const EdgeDecision *d, DijkstraResult *res) {
    if (res->shelter_in_place) return LED_WHITE_STROBE;
    if (d->flame_detected_on_current || d->flame_detected_on_next) return LED_RED_PULSE;
    if (res->cost_to_exit >= SHELTER_THRESHOLD) return LED_WHITE_STROBE;
    if (d->rerouted_from_original) {
        return (d->deciding_edge_S_norm > d->deciding_edge_T_norm)
               ? LED_YELLOW : LED_RED_PULSE;
    }
    return LED_GREEN;
}
