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
