#pragma once

#include <Arduino.h>

struct BeaconStatus {
    char state[24];
    char message[65];
    char model[49];
    int context_pct;  // 0-100, or -1 if unknown
    bool valid;
};

/// Parse: STATUS|state|message[|model[|ctx_pct]]
bool beacon_parse_status_line(const char *line, BeaconStatus *out);

/// Parse one line: THEME|theme_id (optional, returns true if matched)
bool beacon_parse_theme_line(const char *line, char *theme_out, size_t theme_len);

/// PAGE|agent or PAGE|graph
bool beacon_parse_page_line(const char *line, char *page_out, size_t page_len);

enum BeaconGraphOp : uint8_t {
    BEACON_GRAPH_NONE = 0,
    BEACON_GRAPH_BEGIN,
    BEACON_GRAPH_NODE,
    BEACON_GRAPH_EDGE,
    BEACON_GRAPH_END,
};

struct BeaconGraphLine {
    BeaconGraphOp op;
    int a;
    int b;
    int x;
    int y;
    int deg;
    int color;
    char label[17];
};

/// GRAPH|BEGIN|n|e  GRAPH|N|i|x|y|deg|RRGGBB|label  GRAPH|E|a|b  GRAPH|END
bool beacon_parse_graph_line(const char *line, BeaconGraphLine *out);
