#include <Arduino.h>
#include <math.h>

#include "HazardPacket.h"
#include "graph_topology.h"
#include "link_state.h"
#include "routing.h"
#include "fusion.h"
#include "comms.h"
#include "leds.h"
#include "failsafe.h"
#include "sensor_drivers.h"

static const uint16_t MY_NODE_ID = 2;

static BuildingGraph building_graph;
static bool graph_initialized = false;

static LinkStateTable link_state_buffer_a;
static LinkStateTable link_state_buffer_b;
static volatile LinkStateTable *active_table = NULL;
static volatile bool table_updated = false;

static NodeSensorState sensor_state;
static DualPathFilter temp_filter;
static DualPathFilter smoke_filter;

static float current_temp = 25.0f;
static float current_smoke = 0.0f;
static bool  current_flame = false;
static uint16_t current_occupants = 2;

static LedCommand current_led_cmd = { LED_GREEN, 1, 0.0f };
static uint16_t current_next_hop = 0;

static unsigned long last_refresh_ms = 0;
static DijkstraResult last_result;

static void init_default_graph(void) {
    if (graph_initialized) return;

    building_graph.node_count = 6;
    building_graph.edge_count = 8;

    building_graph.nodes[0] = {1, 0, 0, 0, true, 25.0f, 80.0f, 0.0f, 1000.0f, 10.0f};
    building_graph.nodes[1] = {2, 0, 10, 0, false, 25.0f, 80.0f, 0.0f, 1000.0f, 8.0f};
    building_graph.nodes[2] = {3, 0, 20, 5, false, 25.0f, 80.0f, 0.0f, 1000.0f, 8.0f};
    building_graph.nodes[3] = {4, 0, 10, 10, true, 25.0f, 80.0f, 0.0f, 1000.0f, 10.0f};
    building_graph.nodes[4] = {5, 0, 0, 10, false, 25.0f, 80.0f, 0.0f, 1000.0f, 8.0f};
    building_graph.nodes[5] = {6, 0, 20, -5, true, 25.0f, 80.0f, 0.0f, 1000.0f, 10.0f};

    building_graph.edges[0]  = {1, 2, 10.0f, 5, false};
    building_graph.edges[1]  = {2, 3, 12.0f, 5, false};
    building_graph.edges[2]  = {3, 6, 10.0f, 5, false};
    building_graph.edges[3]  = {2, 4, 14.0f, 8, false};
    building_graph.edges[4]  = {4, 5, 10.0f, 5, false};
    building_graph.edges[5]  = {5, 1, 10.0f, 5, false};
    building_graph.edges[6]  = {5, 2, 8.0f, 5, false};
    building_graph.edges[7]  = {3, 4, 6.0f, 3, false};

    graph_initialized = true;
}

static void on_packet_received(const HazardPacket *pkt) {
    LinkStateTable *write_buf;
    if (active_table == &link_state_buffer_a) {
        write_buf = &link_state_buffer_b;
    } else {
        write_buf = &link_state_buffer_a;
    }

    if (!seq_num_accept(pkt->node_id, pkt->seq_num)) return;

    link_state_upsert(write_buf, pkt->node_id, pkt->seq_num,
                      millis(), pkt->edge_cost, pkt->temp_c,
                      pkt->smoke_ppm, pkt->flame_detected);

    active_table = write_buf;
    table_updated = true;
}

static void read_sensors(void) {
#ifdef REAL_HARDWARE
    current_temp = sensor_read_temperature();
    current_smoke = sensor_read_smoke();
    current_flame = sensor_read_flame();
#else
    current_temp = 25.0f + sinf(millis() / 10000.0f) * 2.0f;
    current_smoke = 0.0f;
    if (millis() > 15000) {
        current_temp += 15.0f;
        current_smoke += 200.0f + sinf(millis() / 5000.0f) * 50.0f;
    }
#endif
}

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("=== Fire Evacuation Router Node ===");
    Serial.printf("Node ID: %u\n", MY_NODE_ID);

    link_state_init(&link_state_buffer_a);
    link_state_init(&link_state_buffer_b);
    active_table = &link_state_buffer_a;

    init_default_graph();
    routing_init();
    seq_num_init(MY_NODE_ID);

    sensor_state_init(&sensor_state, millis());
    dual_path_init(&temp_filter, 0.3f, 2.0f, 5.0f);
    dual_path_init(&smoke_filter, 0.3f, 10.0f, 50.0f);

    sensor_drivers_init();
    comms_init(MY_NODE_ID, on_packet_received);

    link_state_upsert((LinkStateTable *)active_table, MY_NODE_ID, 0,
                      millis(), 0.0f, current_temp, current_smoke, current_flame);

    last_result.cost_to_exit = 0.0f;
    last_result.next_hop = 0;
    last_result.shelter_in_place = false;

    xTaskCreatePinnedToCore(leds_task, "leds", 4096, NULL, 1, NULL, 1);

    Serial.println("Setup complete.");
}

void loop() {
    unsigned long now = millis();

    read_sensors();

    sensor_state_update(&sensor_state, current_temp, current_smoke, current_flame, now);

    bool temp_trigger = dual_path_update(&temp_filter, current_temp);
    bool smoke_trigger = dual_path_update(&smoke_filter, current_smoke);
    bool triggered = temp_trigger || smoke_trigger;

    float hazard = 0.0f;
    if (sensor_state.active_tier == TIER_1_LOCAL_SENSOR) {
        float T_norm = clampf((current_temp - 25.0f) / (80.0f - 25.0f), 0, 1);
        float S_norm = clampf(current_smoke / 1000.0f, 0, 1);
        float O_norm = clampf((float)current_occupants / 10.0f, 0, 1);
        hazard = compute_edge_cost(T_norm, S_norm, O_norm, 10.0f, current_flame, 5.0f);
    } else {
        hazard = 50000.0f;
    }

    link_state_upsert((LinkStateTable *)active_table, MY_NODE_ID,
                      seq_num_next(), now, hazard, current_temp,
                      current_smoke, current_flame);
    triggered = true;

    if (triggered || table_updated || (now - last_refresh_ms >= REFRESH_INTERVAL_MS)) {
        if (now - last_refresh_ms >= REFRESH_INTERVAL_MS) {
            HazardPacket tx;
            tx.node_id = MY_NODE_ID;
            tx.seq_num = seq_num_next();
            tx.node_uptime_ms = now;
            tx.temp_c = current_temp;
            tx.smoke_ppm = current_smoke;
            tx.flame_detected = current_flame;
            tx.edge_cost = hazard;
            tx.ttl = DEFAULT_TTL;
            tx.crc16 = hazard_packet_crc16(&tx);
            comms_broadcast(&tx);
            last_refresh_ms = now;
        } else if (triggered) {
            HazardPacket tx;
            tx.node_id = MY_NODE_ID;
            tx.seq_num = seq_num_next();
            tx.node_uptime_ms = now;
            tx.temp_c = current_temp;
            tx.smoke_ppm = current_smoke;
            tx.flame_detected = current_flame;
            tx.edge_cost = hazard;
            tx.ttl = DEFAULT_TTL;
            tx.crc16 = hazard_packet_crc16(&tx);
            comms_broadcast(&tx);
        }

        link_state_age_edges((LinkStateTable *)active_table, now, MY_NODE_ID);

        DijkstraResult dijk = routing_compute(MY_NODE_ID,
                                                active_table,
                                                &building_graph);
        last_result = dijk;

        if (dijk.shelter_in_place) {
            current_led_cmd.color = LED_WHITE_STROBE;
            current_led_cmd.pulse_rate = 1.0f;
            Serial.println("STATE: SHELTER-IN-PLACE - NO SAFE EGRESS");
        } else if (dijk.next_hop != current_next_hop) {
            bool flame_on_current = false;
            if (current_next_hop > 0) {
                int idx = link_state_find((LinkStateTable *)active_table, current_next_hop);
                if (idx >= 0) flame_on_current = active_table->entries[idx].flame_detected;
            }
            if (hold_down_should_switch(dijk.next_hop, current_next_hop,
                                         dijk.cost_to_exit, flame_on_current, now)) {
                current_next_hop = dijk.next_hop;
                Serial.printf("ROUTE: next hop now %u (cost %.1f)\n",
                              current_next_hop, dijk.cost_to_exit);
            }
        }

        EdgeDecision ed;
        ed.flame_detected_on_current = false;
        ed.flame_detected_on_next = false;
        if (current_next_hop > 0) {
            int idx = link_state_find((LinkStateTable *)active_table, current_next_hop);
            if (idx >= 0) {
                ed.flame_detected_on_next = active_table->entries[idx].flame_detected;
            }
        }
        ed.best_cost_to_exit = dijk.cost_to_exit;
        ed.rerouted_from_original = (current_next_hop != 0 && dijk.cost_to_exit > 10000);
        ed.deciding_edge_S_norm = clampf(current_smoke / 1000.0f, 0, 1);
        ed.deciding_edge_T_norm = clampf((current_temp - 25.0f) / 55.0f, 0, 1);

        current_led_cmd.color = choose_led_state(&ed, &dijk);
        current_led_cmd.pulse_rate = fminf(dijk.cost_to_exit / 50000.0f, 1.0f);

        int dir = 1;
        if (current_next_hop < MY_NODE_ID) dir = -1;
        current_led_cmd.direction = dir;
        leds_set_command(current_led_cmd);

        table_updated = false;
    }

    Serial.printf("T=%.1f S=%.0f F=%d occ=%u tier=%d status=%s hop=%u cost=%.1f led=%d\n",
                  current_temp, current_smoke, current_flame, current_occupants,
                  sensor_state.active_tier, sensor_state.status_str,
                  current_next_hop, last_result.cost_to_exit, current_led_cmd.color);

    delay(50);
}
