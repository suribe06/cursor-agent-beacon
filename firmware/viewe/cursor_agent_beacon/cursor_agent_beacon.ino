/*
 * Cursor Agent Beacon — VIEWE display firmware (skeleton)
 *
 * BEFORE FLASHING: verify VIEWESMART/ESP32-Arduino examples/2.1inch on your board.
 * Then merge display + LVGL init from the vendor example into this sketch.
 *
 * Serial: 115200 baud (confirm against vendor example USB-CDC setting)
 * Protocol: STATUS|state|message  and  THEME|theme_id
 */

#include "protocol.h"

// TODO: include LVGL + ESP32_Display_Panel headers from vendor example

static BeaconStatus g_status = {};
static char g_line_buffer[128];
static size_t g_line_len = 0;

static void on_status_received(const BeaconStatus &status) {
    // TODO: map status.state to LVGL animation (see data/standard/manifest.json)
    Serial.print("[beacon] state=");
    Serial.print(status.state);
    Serial.print(" message=");
    Serial.println(status.message);
}

static void consume_serial_char(char ch) {
    if (ch == '\n' || ch == '\r') {
        if (g_line_len > 0) {
            g_line_buffer[g_line_len] = '\0';
            BeaconStatus parsed = {};
            if (beacon_parse_status_line(g_line_buffer, &parsed)) {
                g_status = parsed;
                on_status_received(parsed);
            } else {
                char theme[32] = {};
                if (beacon_parse_theme_line(g_line_buffer, theme, sizeof(theme))) {
                    Serial.print("[beacon] theme=");
                    Serial.println(theme);
                }
            }
            g_line_len = 0;
        }
        return;
    }

    if (g_line_len + 1 < sizeof(g_line_buffer)) {
        g_line_buffer[g_line_len++] = ch;
    }
}

void setup() {
    Serial.begin(115200);
    delay(500);
    Serial.println("[beacon] cursor-agent-beacon VIEWE firmware skeleton");
    Serial.println("[beacon] waiting for STATUS|... lines");

    // TODO: init ESP32_Display_Panel + LVGL (copy from VIEWESMART example)
    // TODO: mount SPIFFS/LittleFS and load data/standard/manifest.json
    // TODO: show idle animation
}

void loop() {
    while (Serial.available() > 0) {
        consume_serial_char((char)Serial.read());
    }

    // TODO: lv_timer_handler() when LVGL is initialized
    // TODO: read knob/button via ESP32_Display_Panel callbacks → Serial.println("EVENT|...")
}
