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

#include <esp_heap_caps.h>

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
static lv_obj_t *g_graph_canvas = nullptr;
static lv_obj_t *g_tap = nullptr;
static bool g_show_graph = false;

static const int kGraphMaxN = 80;
static const int kGraphMaxE = 160;

struct StoredNode {
    int16_t x;
    int16_t y;
    uint8_t deg;
    char label[17];
};

static StoredNode g_nodes[kGraphMaxN];
static uint8_t g_edge_a[kGraphMaxE];
static uint8_t g_edge_b[kGraphMaxE];
static int g_node_count = 0;
static int g_edge_count = 0;

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

static void set_agent_widgets(bool visible) {
    lv_obj_t *widgets[] = {
        g_gif, g_state_label, g_message_label, g_model_label, g_ctx_bar, g_ctx_pct_label,
    };
    for (lv_obj_t *widget : widgets) {
        if (!widget) {
            continue;
        }
        if (visible) {
            lv_obj_clear_flag(widget, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(widget, LV_OBJ_FLAG_HIDDEN);
        }
    }
}

static lv_point_t graph_xy(int x, int y) {
    lv_point_t point;
    point.x = (lv_coord_t)(40 + (x * 400) / 1000);
    point.y = (lv_coord_t)(40 + (y * 400) / 1000);
    return point;
}

static void redraw_graph() {
    if (!g_graph_canvas) {
        return;
    }
    lv_canvas_fill_bg(g_graph_canvas, lv_color_hex(0x071020), LV_OPA_COVER);

    lv_draw_line_dsc_t line_dsc;
    lv_draw_line_dsc_init(&line_dsc);
    line_dsc.color = lv_color_hex(0x334155);
    line_dsc.width = 2;
    for (int i = 0; i < g_edge_count; i++) {
        uint8_t a = g_edge_a[i];
        uint8_t b = g_edge_b[i];
        if (a >= g_node_count || b >= g_node_count) {
            continue;
        }
        lv_point_t points[2] = {
            graph_xy(g_nodes[a].x, g_nodes[a].y),
            graph_xy(g_nodes[b].x, g_nodes[b].y),
        };
        lv_canvas_draw_line(g_graph_canvas, points, 2, &line_dsc);
    }

    lv_draw_rect_dsc_t dot_dsc;
    lv_draw_rect_dsc_init(&dot_dsc);
    dot_dsc.bg_color = lv_color_hex(0x38BDF8);
    dot_dsc.bg_opa = LV_OPA_COVER;
    dot_dsc.radius = LV_RADIUS_CIRCLE;
    for (int i = 0; i < g_node_count; i++) {
        lv_point_t point = graph_xy(g_nodes[i].x, g_nodes[i].y);
        lv_canvas_draw_rect(g_graph_canvas, point.x - 3, point.y - 3, 6, 6, &dot_dsc);
    }

    lv_draw_label_dsc_t label_dsc;
    lv_draw_label_dsc_init(&label_dsc);
    label_dsc.color = lv_color_hex(0xE2E8F0);
    label_dsc.font = &lv_font_montserrat_12;
    int labeled = 0;
    bool used[kGraphMaxN] = {};
    for (int rank = 0; rank < g_node_count && labeled < 6; rank++) {
        int best = -1;
        for (int i = 0; i < g_node_count; i++) {
            if (used[i] || g_nodes[i].label[0] == '\0') {
                continue;
            }
            if (best < 0 || g_nodes[i].deg > g_nodes[best].deg) {
                best = i;
            }
        }
        if (best < 0) {
            break;
        }
        used[best] = true;
        lv_point_t point = graph_xy(g_nodes[best].x, g_nodes[best].y);
        lv_canvas_draw_text(
            g_graph_canvas, point.x + 6, point.y - 8, 120, &label_dsc, g_nodes[best].label);
        labeled++;
    }
}

static void show_agent_from_status() {
    if (g_gif) {
        lv_obj_clear_flag(g_gif, LV_OBJ_FLAG_HIDDEN);
    }
    if (g_state_label) {
        lv_obj_clear_flag(g_state_label, LV_OBJ_FLAG_HIDDEN);
    }
    if (g_message_label) {
        if (g_status.message[0]) {
            lv_obj_clear_flag(g_message_label, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(g_message_label, LV_OBJ_FLAG_HIDDEN);
        }
    }
    if (g_model_label) {
        if (g_status.model[0]) {
            lv_obj_clear_flag(g_model_label, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(g_model_label, LV_OBJ_FLAG_HIDDEN);
        }
    }
    if (g_ctx_bar && g_ctx_pct_label) {
        if (g_context_pct >= 0) {
            lv_obj_clear_flag(g_ctx_bar, LV_OBJ_FLAG_HIDDEN);
            lv_obj_clear_flag(g_ctx_pct_label, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(g_ctx_bar, LV_OBJ_FLAG_HIDDEN);
            lv_obj_add_flag(g_ctx_pct_label, LV_OBJ_FLAG_HIDDEN);
        }
    }
}

static void apply_page() {
    if (g_show_graph && g_graph_canvas) {
        set_agent_widgets(false);
        redraw_graph();
        lv_obj_clear_flag(g_graph_canvas, LV_OBJ_FLAG_HIDDEN);
    } else if (g_graph_canvas) {
        lv_obj_add_flag(g_graph_canvas, LV_OBJ_FLAG_HIDDEN);
        show_agent_from_status();
    }
    if (g_tap) {
        lv_obj_move_foreground(g_tap);
    }
}

static void on_screen_tap(lv_event_t *event) {
    if (lv_event_get_code(event) != LV_EVENT_CLICKED) {
        return;
    }
    g_show_graph = !g_show_graph;
    apply_page();
}

static void accept_graph_line(const BeaconGraphLine &parsed) {
    if (parsed.op == BEACON_GRAPH_BEGIN) {
        g_node_count = 0;
        g_edge_count = 0;
        return;
    }
    if (parsed.op == BEACON_GRAPH_NODE && g_node_count < kGraphMaxN) {
        StoredNode &node = g_nodes[g_node_count++];
        node.x = (int16_t)parsed.x;
        node.y = (int16_t)parsed.y;
        node.deg = (uint8_t)(parsed.deg < 0 ? 0 : parsed.deg > 255 ? 255 : parsed.deg);
        strncpy(node.label, parsed.label, sizeof(node.label) - 1);
        node.label[sizeof(node.label) - 1] = '\0';
        return;
    }
    if (parsed.op == BEACON_GRAPH_EDGE && g_edge_count < kGraphMaxE) {
        g_edge_a[g_edge_count] = (uint8_t)parsed.a;
        g_edge_b[g_edge_count] = (uint8_t)parsed.b;
        g_edge_count++;
        return;
    }
    if (parsed.op == BEACON_GRAPH_END && lvgl_port_lock(-1)) {
        if (g_show_graph) {
            apply_page();
        }
        lvgl_port_unlock();
    }
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
    if (strstr(text, "THEME|") != nullptr || strstr(text, "GRAPH|") != nullptr) {
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

    apply_page();
    lvgl_port_unlock();
}

static void on_status_received(const BeaconStatus &status) {
    // ponytail: do not Serial.print here — USB-CDC TX can echo into RX and
    // corrupt the STATUS line buffer (shows as "defSTATUS|..." garbage).
    apply_status_ui(status);
}

static const char *find_protocol_start(const char *line) {
    const char *best = nullptr;
    const char *marks[] = {"STATUS|", "THEME|", "GRAPH|", "PAGE|"};
    for (const char *mark : marks) {
        const char *found = strstr(line, mark);
        if (found && (!best || found < best)) {
            best = found;
        }
    }
    return best;
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

    char page[16] = {};
    if (beacon_parse_page_line(framed, page, sizeof(page))) {
        if (lvgl_port_lock(-1)) {
            g_show_graph = strcmp(page, "graph") == 0;
            apply_page();
            lvgl_port_unlock();
        }
        return;
    }

    BeaconGraphLine graph = {};
    if (beacon_parse_graph_line(framed, &graph)) {
        accept_graph_line(graph);
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

    size_t canvas_bytes = 480 * 480 * sizeof(lv_color_t);
    lv_color_t *buffer = static_cast<lv_color_t *>(
        heap_caps_malloc(canvas_bytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (buffer) {
        g_graph_canvas = lv_canvas_create(g_screen);
        lv_canvas_set_buffer(g_graph_canvas, buffer, 480, 480, LV_IMG_CF_TRUE_COLOR);
        lv_obj_align(g_graph_canvas, LV_ALIGN_CENTER, 0, 0);
        lv_obj_add_flag(g_graph_canvas, LV_OBJ_FLAG_HIDDEN);
    }

    g_tap = lv_obj_create(g_screen);
    lv_obj_set_size(g_tap, 480, 480);
    lv_obj_align(g_tap, LV_ALIGN_CENTER, 0, 0);
    lv_obj_set_style_bg_opa(g_tap, LV_OPA_TRANSP, 0);
    lv_obj_set_style_border_width(g_tap, 0, 0);
    lv_obj_add_flag(g_tap, LV_OBJ_FLAG_CLICKABLE);
    lv_obj_clear_flag(g_tap, LV_OBJ_FLAG_SCROLLABLE);
    lv_obj_add_event_cb(g_tap, on_screen_tap, LV_EVENT_CLICKED, nullptr);
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
