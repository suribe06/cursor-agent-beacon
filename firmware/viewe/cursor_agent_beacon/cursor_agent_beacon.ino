/*
 * Cursor Agent Beacon — VIEWE UEDX48480021-MD80ET status display
 *
 * Shows theme GIF + caption from serial lines:
 *   STATUS|state|message
 *   THEME|theme_id   (logged only; GIFs are embedded standard theme)
 *
 * Board: BOARD_VIEWE_UEDX48480021_MD80ET (see esp_panel_board_supported_conf.h)
 * Serial: USB CDC 115200 — same /dev/ttyACM0 used by `cursor-agent-beacon bridge`
 *
 * GIFs: regenerate with `python3 scripts/embed_theme_gifs.py` (flash-viewe.sh runs it).
 */

#include <Arduino.h>
#include <esp_display_panel.hpp>
#include <lvgl.h>
#include <string.h>

#include "lvgl_v8_port.h"
#include "protocol.h"
#include "theme_gifs.h"

using namespace esp_panel::drivers;
using namespace esp_panel::board;

static BeaconStatus g_status = {};
static char g_line_buffer[160];
static size_t g_line_len = 0;
static char g_active_gif_state[32] = "";

static lv_obj_t *g_screen = nullptr;
static lv_obj_t *g_gif = nullptr;
static lv_obj_t *g_state_label = nullptr;
static lv_obj_t *g_message_label = nullptr;

struct StateStyle {
    const char *label;
    lv_color_t color;
};

static StateStyle style_for_state(const char *state) {
    if (strcmp(state, "thinking") == 0) {
        return {"Thinking", lv_color_hex(0xF59E0B)};
    }
    if (strcmp(state, "running_shell") == 0) {
        return {"Shell", lv_color_hex(0x38BDF8)};
    }
    if (strcmp(state, "running_mcp") == 0) {
        return {"MCP", lv_color_hex(0xA78BFA)};
    }
    if (strcmp(state, "waiting") == 0) {
        return {"Waiting", lv_color_hex(0xFBBF24)};
    }
    if (strcmp(state, "error") == 0) {
        return {"Error", lv_color_hex(0xF87171)};
    }
    if (strcmp(state, "success") == 0) {
        return {"Ready", lv_color_hex(0x4ADE80)};
    }
    if (strcmp(state, "stop") == 0) {
        return {"Stop", lv_color_hex(0x4ADE80)};
    }
    if (strcmp(state, "idle") == 0) {
        return {"Idle", lv_color_hex(0x94A3B8)};
    }
    return {state && state[0] ? state : "Beacon", lv_color_hex(0xE2E8F0)};
}

static void apply_status_ui(const BeaconStatus &status) {
    if (!g_state_label || !g_message_label || !g_screen || !g_gif) {
        return;
    }

    StateStyle style = style_for_state(status.state);
    const lv_img_dsc_t *gif_src = beacon_gif_for_state(status.state);

    if (!lvgl_port_lock(-1)) {
        return;
    }

    if (strcmp(g_active_gif_state, status.state) != 0) {
        lv_gif_set_src(g_gif, gif_src);
        strncpy(g_active_gif_state, status.state, sizeof(g_active_gif_state) - 1);
        g_active_gif_state[sizeof(g_active_gif_state) - 1] = '\0';
    }

    lv_obj_set_style_text_color(g_state_label, style.color, 0);
    lv_label_set_text(g_state_label, style.label);
    lv_label_set_text(
        g_message_label,
        status.message[0] ? status.message : "—"
    );
    lvgl_port_unlock();
}

static void on_status_received(const BeaconStatus &status) {
    Serial.print("[beacon] state=");
    Serial.print(status.state);
    Serial.print(" message=");
    Serial.println(status.message);
    apply_status_ui(status);
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

static void create_status_ui() {
    g_screen = lv_scr_act();
    lv_obj_set_style_bg_color(g_screen, lv_color_hex(0x071020), 0);
    lv_obj_set_style_bg_opa(g_screen, LV_OPA_COVER, 0);
    lv_obj_clear_flag(g_screen, LV_OBJ_FLAG_SCROLLABLE);

    g_gif = lv_gif_create(g_screen);
    lv_gif_set_src(g_gif, beacon_gif_for_state("idle"));
    strncpy(g_active_gif_state, "idle", sizeof(g_active_gif_state) - 1);
    lv_obj_align(g_gif, LV_ALIGN_CENTER, 0, -10);

    g_state_label = lv_label_create(g_screen);
    lv_label_set_text(g_state_label, "Idle");
    lv_obj_set_style_text_font(g_state_label, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(g_state_label, lv_color_hex(0x94A3B8), 0);
    lv_obj_align(g_state_label, LV_ALIGN_BOTTOM_MID, 0, -48);

    g_message_label = lv_label_create(g_screen);
    lv_label_set_long_mode(g_message_label, LV_LABEL_LONG_DOT);
    lv_obj_set_width(g_message_label, 400);
    lv_label_set_text(g_message_label, "Waiting for STATUS|...");
    lv_obj_set_style_text_font(g_message_label, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(g_message_label, lv_color_hex(0xE2E8F0), 0);
    lv_obj_set_style_text_align(g_message_label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(g_message_label, LV_ALIGN_BOTTOM_MID, 0, -20);
}

void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println("[beacon] cursor-agent-beacon VIEWE MD80ET + GIFs");

    Serial.println("[beacon] init board");
    Board *board = new Board();
    board->init();
#if LVGL_PORT_AVOID_TEARING_MODE
    auto lcd = board->getLCD();
    lcd->configFrameBufferNumber(LVGL_PORT_DISP_BUFFER_NUM);
#if ESP_PANEL_DRIVERS_BUS_ENABLE_RGB && CONFIG_IDF_TARGET_ESP32S3
    auto lcd_bus = lcd->getBus();
    if (lcd_bus->getBasicAttributes().type == ESP_PANEL_BUS_TYPE_RGB) {
        static_cast<BusRGB *>(lcd_bus)->configRGB_BounceBufferSize(lcd->getFrameWidth() * 10);
    }
#endif
#endif
    assert(board->begin());

    Serial.println("[beacon] init LVGL");
    lvgl_port_init(board->getLCD(), board->getTouch());

    lvgl_port_lock(-1);
    create_status_ui();
    lvgl_port_unlock();

    Serial.println("[beacon] waiting for STATUS|... lines");
}

void loop() {
    while (Serial.available() > 0) {
        consume_serial_char(static_cast<char>(Serial.read()));
    }
    delay(5);
}
