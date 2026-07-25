#include <Arduino.h>
#include <WiFi.h>
#include <PubSubClient.h>
#include "HazardPacket.h"
#include "comms.h"

static const char *WIFI_SSID = "SafeRouteAI";
static const char *WIFI_PASS = "evacuation2024";
static const char *MQTT_BROKER = "192.168.4.1";
static const int   MQTT_PORT = 1883;

static WiFiClient wifi_client;
static PubSubClient mqtt_client(wifi_client);
static int mqtt_reconnect_attempts = 0;

static void mqtt_callback(char *topic, byte *payload, unsigned int len) {
}

static void ensure_mqtt_connected(void) {
    if (mqtt_client.connected()) return;

    char client_id[32];
    snprintf(client_id, sizeof(client_id), "gateway-%u", random(1000, 9999));

    if (mqtt_client.connect(client_id)) {
        Serial.println("MQTT connected");
        mqtt_client.subscribe("evac/cmd/#");
        mqtt_reconnect_attempts = 0;
    } else {
        mqtt_reconnect_attempts++;
        Serial.printf("MQTT connect fail (attempt %d)\n", mqtt_reconnect_attempts);
    }
}

void gateway_init(void) {
    WiFi.mode(WIFI_STA);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    Serial.print("Connecting to WiFi");
    for (int i = 0; i < 20 && WiFi.status() != WL_CONNECTED; i++) {
        delay(500);
        Serial.print(".");
    }
    Serial.println(WiFi.status() == WL_CONNECTED ? " OK" : " FAIL");

    mqtt_client.setServer(MQTT_BROKER, MQTT_PORT);
    mqtt_client.setCallback(mqtt_callback);
}

void gateway_publish_hazard(const HazardPacket *pkt) {
    if (!WiFi.isConnected()) return;
    ensure_mqtt_connected();
    if (!mqtt_client.connected()) return;

    char topic[64];
    char payload[256];

    snprintf(topic, sizeof(topic), "evac/node/%u/hazard", pkt->node_id);
    snprintf(payload, sizeof(payload),
             "{\"node_id\":%u,\"seq\":%lu,\"temp\":%.1f,\"smoke\":%.0f,"
             "\"flame\":%s,\"cost\":%.2f}",
             pkt->node_id, pkt->seq_num, pkt->temp_c, pkt->smoke_ppm,
             pkt->flame_detected ? "true" : "false", pkt->edge_cost);

    mqtt_client.publish(topic, payload);
    mqtt_client.loop();
}

void gateway_publish_status(uint16_t node_id, const char *status_str) {
    if (!WiFi.isConnected()) return;
    ensure_mqtt_connected();
    if (!mqtt_client.connected()) return;

    char topic[64];
    snprintf(topic, sizeof(topic), "evac/node/%u/status", node_id);
    mqtt_client.publish(topic, status_str);
}
