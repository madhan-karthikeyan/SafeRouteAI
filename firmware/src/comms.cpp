#include "comms.h"
#include "HazardPacket.h"
#include <string.h>
#include <esp_now.h>
#include <WiFi.h>

static uint16_t own_node_id = 0;
static comms_recv_cb_t user_cb = NULL;

static uint8_t peer_macs[MAX_PEERS][6];
static int peer_count = 0;

static uint32_t last_seq[MAX_NODES];

void seq_num_init(uint16_t node_id) {
    memset(last_seq, 0, sizeof(last_seq));
}

uint32_t seq_num_next(void) {
    static uint32_t counter = 0;
    return counter++;
}

bool seq_num_accept(uint16_t from_id, uint32_t seq) {
    if (from_id >= MAX_NODES) return false;
    uint32_t last = last_seq[from_id];
    int32_t diff = (int32_t)(seq - last);
    if (diff > 0 || (diff < 0 && last > 0xF0000000 && seq < 0x0FFFFFFF)) {
        last_seq[from_id] = seq;
        return true;
    }
    return false;
}

static void on_data_recv(const uint8_t *mac, const uint8_t *data, int len) {
    if (len != (int)sizeof(HazardPacket)) return;
    if (!user_cb) return;

    HazardPacket pkt;
    memcpy(&pkt, data, sizeof(pkt));

    if (!hazard_packet_validate(&pkt)) return;

    user_cb(&pkt);
}

void comms_init(uint16_t node_id, comms_recv_cb_t cb) {
    own_node_id = node_id;
    user_cb = cb;

    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    esp_now_init();
    esp_now_register_recv_cb(on_data_recv);
}

bool comms_add_peer(const uint8_t mac[6]) {
    if (peer_count >= MAX_PEERS) return false;
    memcpy(peer_macs[peer_count], mac, 6);
    esp_now_peer_info_t peer = {};
    peer.channel = ESP_NOW_CHANNEL;
    peer.encrypt = false;
    memcpy(peer.peer_addr, mac, 6);
    esp_now_add_peer(&peer);
    peer_count++;
    return true;
}

bool comms_broadcast(const HazardPacket *pkt) {
    for (int i = 0; i < peer_count; i++) {
        esp_now_send(peer_macs[i], (const uint8_t *)pkt, sizeof(HazardPacket));
    }
    return true;
}
