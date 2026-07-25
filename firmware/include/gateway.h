#pragma once

#include "HazardPacket.h"

void gateway_init(void);
void gateway_publish_hazard(const HazardPacket *pkt);
void gateway_publish_status(uint16_t node_id, const char *status_str);
