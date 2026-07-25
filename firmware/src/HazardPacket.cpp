#include "HazardPacket.h"

uint16_t hazard_packet_crc16(const HazardPacket *pkt) {
    const uint8_t *data = (const uint8_t *)pkt;
    uint16_t crc = 0xFFFF;
    for (int i = 0; i < (int)sizeof(HazardPacket) - 2; i++) {
        crc ^= data[i];
        for (int j = 0; j < 8; j++) {
            if (crc & 1) {
                crc = (crc >> 1) ^ 0xA001;
            } else {
                crc >>= 1;
            }
        }
    }
    return crc;
}

bool hazard_packet_validate(const HazardPacket *pkt) {
    uint16_t computed = hazard_packet_crc16(pkt);
    return computed == pkt->crc16;
}
