#pragma once

#include <stdint.h>
#include <stdbool.h>

#define MAX_NODES 15
#define MAX_EDGES 40
#define MAX_NEIGHBORS 10

typedef struct {
    uint16_t node_id;
    uint8_t  floor;
    float    x;
    float    y;
    bool     is_exit;
    float    T_baseline;
    float    T_critical;
    float    S_baseline;
    float    S_critical;
    float    occupant_capacity;
} NodeConfig;

typedef struct {
    uint16_t from;
    uint16_t to;
    float    base_distance;
    float    occupant_capacity;
    bool     floor_transition;
} EdgeConfig;

typedef struct {
    NodeConfig nodes[MAX_NODES];
    EdgeConfig edges[MAX_EDGES];
    uint8_t    node_count;
    uint8_t    edge_count;
} BuildingGraph;

typedef struct {
    uint16_t neighbor_id;
    float    base_distance;
    float    occupant_capacity;
    bool     floor_transition;
} AdjacencyEntry;

typedef struct {
    AdjacencyEntry entries[MAX_NEIGHBORS];
    uint8_t        count;
} AdjacencyList;
