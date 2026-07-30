/*
 * Cursor Agent Beacon — VIEWE UEDX48480021-MD80ET status display
 *
 * Shows theme GIF + caption from serial lines:
 *   STATUS|state|message
 *   STATUS|state|message|model
 *   STATUS|state|message|model|ctx_pct
 *   THEME|theme_id   (logged only; GIFs are embedded standard theme)
 *
 * Board: BOARD_VIEWE_UEDX48480021_MD80ET (see esp_panel_board_supported_conf.h)
 * Serial: USB CDC 115200 — same port used by `cursor-agent-beacon bridge`
 *
 * GIFs: regenerate with `python3 scripts/embed_theme_gifs.py` (flash-viewe.sh runs it).
 */

#include <Arduino.h>
#include <esp_display_panel.hpp>
#include <lvgl.h>
#include <stdio.h>
#include <string.h>

#include "lvgl_v8_port.h"
#include "protocol.h"
#include "theme_gifs.h"

using namespace esp_panel::drivers;
using namespace esp_panel::board;

// Round 480px — Meter Band layout:
//   upper: GIF · mid: state + message · lower: model + bar with %
static const lv_coord_t kGifZoom = 148;       // 148/256 ≈ 58% of 480 → ~278px
static const lv_coord_t kGifOffsetY = -58;
static const lv_coord_t kTextWidth = 300;
static const lv_coord_t kStateOffsetY = -108;
static const lv_coord_t kMessageOffsetY = -82;
static const lv_coord_t kModelOffsetY = -56;
static const lv_coord_t kBarOffsetY = -24;
static const lv_coord_t kBarWidth = 150;
static const lv_coord_t kBarHeight = 12;
static const lv_coord_t kBarCenterX = -28;    // leave room for "100%" on the right
static const lv_coord_t kPctOffsetX = 92;

static BeaconStatus g_status = {};
static char g_line_buffer[192];
static size_t g_line_len = 0;
static char g_active_gif_state[32] = "";
static int g_context_pct = -1;

static lv_obj_t *g_screen = nullptr;
static lv_obj_t *g_gif = nullptr;
static lv_obj_t *g_state_label = nullptr;
static lv_obj_t *g_message_label = nullptr;
static lv_obj_t *g_model_label = nullptr;
static lv_obj_t *g_ctx_bar = nullptr;
static lv_obj_t *g_ctx_pct_label = nullptr;

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

static lv_color_t context_bar_color(int pct) {
    if (pct >= 90) {
        return lv_color_hex(0xF87171);
    }
    if (pct >= 70) {
        return lv_color_hex(0xFBBF24);
    }
    return lv_color_hex(0x38BDF8);
}

static bool looks_like_protocol_noise(const char *text) {
    if (!text || !text[0]) {
        return false;
    }
    if (strstr(text, "STATUS|") != nullptr) {
        return true;
    }
    if (strstr(text, "THEME|") != nullptr) {
        return true;
    }
    return false;
}

static void apply_status_ui(const BeaconStatus &status) {
    if (!g_state_label || !g_message_label || !g_model_label || !g_ctx_bar ||
        !g_ctx_pct_label || !g_screen || !g_gif) {
        return;
    }

    StateStyle style = style_for_state(status.state);
    const lv_img_dsc_t *gif_src = beacon_gif_for_state(status.state);
    const bool show_message =
        status.message[0] && !looks_like_protocol_noise(status.message);
    const bool show_model =
        status.model[0] && !looks_like_protocol_noise(status.model);

    if (status.context_pct >= 0) {
        g_context_pct = status.context_pct;
    }

    if (!lvgl_port_lock(-1)) {
        return;
    }

    if (strcmp(g_active_gif_state, status.state) != 0) {
        lv_gif_set_src(g_gif, gif_src);
        lv_img_set_zoom(g_gif, kGifZoom);
        strncpy(g_active_gif_state, status.state, sizeof(g_active_gif_state) - 1);
        g_active_gif_state[sizeof(g_active_gif_state) - 1] = '\0';
    }

    lv_obj_set_style_text_color(g_state_label, style.color, 0);
    lv_label_set_text(g_state_label, style.label);

    if (show_message) {
        lv_label_set_text(g_message_label, status.message);
        lv_obj_clear_flag(g_message_label, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_label_set_text(g_message_label, "");
        lv_obj_add_flag(g_message_label, LV_OBJ_FLAG_HIDDEN);
    }

    if (show_model) {
        lv_label_set_text(g_model_label, status.model);
        lv_obj_clear_flag(g_model_label, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_label_set_text(g_model_label, "");
        lv_obj_add_flag(g_model_label, LV_OBJ_FLAG_HIDDEN);
    }

    if (g_context_pct >= 0) {
        char pct_text[8];
        snprintf(pct_text, sizeof(pct_text), "%d%%", g_context_pct);
        lv_color_t bar_color = context_bar_color(g_context_pct);
        lv_bar_set_value(g_ctx_bar, g_context_pct, LV_ANIM_OFF);
        lv_obj_set_style_bg_color(g_ctx_bar, bar_color, LV_PART_INDICATOR);
        lv_label_set_text(g_ctx_pct_label, pct_text);
        lv_obj_set_style_text_color(g_ctx_pct_label, bar_color, 0);
        lv_obj_clear_flag(g_ctx_bar, LV_OBJ_FLAG_HIDDEN);
        lv_obj_clear_flag(g_ctx_pct_label, LV_OBJ_FLAG_HIDDEN);
    } else {
        lv_obj_add_flag(g_ctx_bar, LV_OBJ_FLAG_HIDDEN);
        lv_obj_add_flag(g_ctx_pct_label, LV_OBJ_FLAG_HIDDEN);
    }

    lvgl_port_unlock();
}

static void on_status_received(const BeaconStatus &status) {
    // ponytail: do not Serial.print here — USB-CDC TX can echo into RX and
    // corrupt the STATUS line buffer (shows as "defSTATUS|..." garbage).
    apply_status_ui(status);
}

static const char *find_protocol_start(const char *line) {
    const char *status = strstr(line, "STATUS|");
    const char *theme = strstr(line, "THEME|");
    if (status && theme) {
        return status < theme ? status : theme;
    }
    if (status) {
        return status;
    }
    return theme;
}

static void handle_line(const char *line) {
    const char *framed = find_protocol_start(line);
    if (!framed) {
        return;
    }

    BeaconStatus parsed = {};
    parsed.context_pct = -1;
    if (beacon_parse_status_line(framed, &parsed)) {
        g_status = parsed;
        on_status_received(parsed);
        return;
    }

    char theme[32] = {};
    if (beacon_parse_theme_line(framed, theme, sizeof(theme))) {
        return;
    }
}

static void consume_serial_char(char ch) {
    if (ch == '\n' || ch == '\r') {
        if (g_line_len > 0) {
            g_line_buffer[g_line_len] = '\0';
            handle_line(g_line_buffer);
            g_line_len = 0;
        }
        return;
    }

    if (ch < 32 || ch > 126) {
        return;
    }

    if (g_line_len + 1 >= sizeof(g_line_buffer)) {
        g_line_len = 0;
    }
    g_line_buffer[g_line_len++] = ch;
}

static void create_status_ui() {
    g_screen = lv_scr_act();
    lv_obj_set_style_bg_color(g_screen, lv_color_hex(0x071020), 0);
    lv_obj_set_style_bg_opa(g_screen, LV_OPA_COVER, 0);
    lv_obj_clear_flag(g_screen, LV_OBJ_FLAG_SCROLLABLE);

    g_gif = lv_gif_create(g_screen);
    lv_gif_set_src(g_gif, beacon_gif_for_state("idle"));
    lv_img_set_zoom(g_gif, kGifZoom);
    lv_obj_align(g_gif, LV_ALIGN_CENTER, 0, kGifOffsetY);
    strncpy(g_active_gif_state, "idle", sizeof(g_active_gif_state) - 1);

    g_state_label = lv_label_create(g_screen);
    lv_label_set_text(g_state_label, "Idle");
    lv_obj_set_style_text_font(g_state_label, &lv_font_montserrat_20, 0);
    lv_obj_set_style_text_color(g_state_label, lv_color_hex(0x94A3B8), 0);
    lv_obj_align(g_state_label, LV_ALIGN_BOTTOM_MID, 0, kStateOffsetY);

    g_message_label = lv_label_create(g_screen);
    lv_label_set_long_mode(g_message_label, LV_LABEL_LONG_DOT);
    lv_obj_set_width(g_message_label, kTextWidth);
    lv_label_set_text(g_message_label, "Connecting...");
    lv_obj_set_style_text_font(g_message_label, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(g_message_label, lv_color_hex(0xE2E8F0), 0);
    lv_obj_set_style_text_align(g_message_label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(g_message_label, LV_ALIGN_BOTTOM_MID, 0, kMessageOffsetY);

    g_model_label = lv_label_create(g_screen);
    lv_label_set_long_mode(g_model_label, LV_LABEL_LONG_DOT);
    lv_obj_set_width(g_model_label, kTextWidth);
    lv_label_set_text(g_model_label, "");
    lv_obj_set_style_text_font(g_model_label, &lv_font_montserrat_12, 0);
    lv_obj_set_style_text_color(g_model_label, lv_color_hex(0x94A3B8), 0);
    lv_obj_set_style_text_align(g_model_label, LV_TEXT_ALIGN_CENTER, 0);
    lv_obj_align(g_model_label, LV_ALIGN_BOTTOM_MID, 0, kModelOffsetY);
    lv_obj_add_flag(g_model_label, LV_OBJ_FLAG_HIDDEN);

    g_ctx_bar = lv_bar_create(g_screen);
    lv_obj_set_size(g_ctx_bar, kBarWidth, kBarHeight);
    lv_bar_set_range(g_ctx_bar, 0, 100);
    lv_bar_set_value(g_ctx_bar, 0, LV_ANIM_OFF);
    lv_obj_set_style_radius(g_ctx_bar, 4, LV_PART_MAIN);
    lv_obj_set_style_radius(g_ctx_bar, 4, LV_PART_INDICATOR);
    lv_obj_set_style_bg_color(g_ctx_bar, lv_color_hex(0x1E293B), LV_PART_MAIN);
    lv_obj_set_style_bg_opa(g_ctx_bar, LV_OPA_COVER, LV_PART_MAIN);
    lv_obj_set_style_bg_color(g_ctx_bar, lv_color_hex(0x38BDF8), LV_PART_INDICATOR);
    lv_obj_set_style_bg_opa(g_ctx_bar, LV_OPA_COVER, LV_PART_INDICATOR);
    lv_obj_align(g_ctx_bar, LV_ALIGN_BOTTOM_MID, kBarCenterX, kBarOffsetY);
    lv_obj_add_flag(g_ctx_bar, LV_OBJ_FLAG_HIDDEN);

    g_ctx_pct_label = lv_label_create(g_screen);
    lv_label_set_text(g_ctx_pct_label, "");
    lv_obj_set_style_text_font(g_ctx_pct_label, &lv_font_montserrat_14, 0);
    lv_obj_set_style_text_color(g_ctx_pct_label, lv_color_hex(0x38BDF8), 0);
    lv_obj_align(g_ctx_pct_label, LV_ALIGN_BOTTOM_MID, kPctOffsetX, kBarOffsetY - 2);
    lv_obj_add_flag(g_ctx_pct_label, LV_OBJ_FLAG_HIDDEN);
}

void setup() {
    Serial.begin(115200);
    delay(300);

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

    lvgl_port_init(board->getLCD(), board->getTouch());

    lvgl_port_lock(-1);
    create_status_ui();
    lvgl_port_unlock();
}

void loop() {
    while (Serial.available() > 0) {
        consume_serial_char(static_cast<char>(Serial.read()));
    }
    delay(5);
}
