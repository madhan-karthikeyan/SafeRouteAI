#pragma once

#include <stdint.h>
#include <stdbool.h>
#include "HazardPacket.h"
#include "link_state.h"

#define ESP_NOW_CHANNEL 1
#define MAX_PEERS 15

typedef void (*comms_recv_cb_t)(const HazardPacket *pkt);

void comms_init(uint16_t own_node_id, comms_recv_cb_t cb);
bool comms_add_peer(const uint8_t mac[6]);
bool comms_broadcast(const HazardPacket *pkt);

void seq_num_init(uint16_t node_id);
uint32_t seq_num_next(void);
bool seq_num_accept(uint16_t from_id, uint32_t seq);
