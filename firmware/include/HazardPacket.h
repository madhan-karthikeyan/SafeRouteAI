#pragma once

#include <stdint.h>
#include <stdbool.h>

#define HAZARD_PACKET_SIZE 26

typedef struct __attribute__((packed)) {
    uint16_t node_id;
    uint32_t seq_num;
    uint32_t node_uptime_ms;
    float    temp_c;
    float    smoke_ppm;
    bool     flame_detected;
    float    edge_cost;
    uint8_t  ttl;
    uint16_t crc16;
} HazardPacket;

#define DEFAULT_TTL 4

#ifdef __cplusplus
extern "C" {
#endif

uint16_t hazard_packet_crc16(const HazardPacket *pkt);
bool     hazard_packet_validate(const HazardPacket *pkt);

#ifdef __cplusplus
}
#endif
