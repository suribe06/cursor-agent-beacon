#include "protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool starts_with(const char *line, const char *prefix) {
    return strncmp(line, prefix, strlen(prefix)) == 0;
}

static void copy_token(const char *src, char *dest, size_t dest_len) {
    if (dest_len == 0) {
        return;
    }
    strncpy(dest, src, dest_len - 1);
    dest[dest_len - 1] = '\0';
}

bool beacon_parse_status_line(const char *line, BeaconStatus *out) {
    if (!line || !out) {
        return false;
    }

    if (!starts_with(line, "STATUS|")) {
        return false;
    }

    const char *rest = line + strlen("STATUS|");
    const char *sep = strchr(rest, '|');
    if (!sep) {
        return false;
    }

    size_t state_len = (size_t)(sep - rest);
    if (state_len == 0 || state_len >= sizeof(out->state)) {
        return false;
    }

    strncpy(out->state, rest, state_len);
    out->state[state_len] = '\0';

    const char *msg = sep + 1;
    const char *model_sep = strchr(msg, '|');
    out->model[0] = '\0';
    out->context_pct = -1;

    if (model_sep) {
        size_t msg_len = (size_t)(model_sep - msg);
        if (msg_len >= sizeof(out->message)) {
            msg_len = sizeof(out->message) - 1;
        }
        memcpy(out->message, msg, msg_len);
        out->message[msg_len] = '\0';

        const char *model = model_sep + 1;
        const char *ctx_sep = strchr(model, '|');
        if (ctx_sep) {
            size_t model_len = (size_t)(ctx_sep - model);
            if (model_len >= sizeof(out->model)) {
                model_len = sizeof(out->model) - 1;
            }
            memcpy(out->model, model, model_len);
            out->model[model_len] = '\0';
            out->context_pct = atoi(ctx_sep + 1);
            if (out->context_pct < 0) {
                out->context_pct = 0;
            }
            if (out->context_pct > 100) {
                out->context_pct = 100;
            }
        } else {
            copy_token(model, out->model, sizeof(out->model));
        }
    } else {
        copy_token(msg, out->message, sizeof(out->message));
    }

    out->valid = true;
    return true;
}

bool beacon_parse_theme_line(const char *line, char *theme_out, size_t theme_len) {
    if (!line || !theme_out || theme_len == 0) {
        return false;
    }

    if (!starts_with(line, "THEME|")) {
        return false;
    }

    copy_token(line + strlen("THEME|"), theme_out, theme_len);
    return theme_out[0] != '\0';
}

bool beacon_parse_page_line(const char *line, char *page_out, size_t page_len) {
    if (!line || !page_out || page_len == 0 || !starts_with(line, "PAGE|")) {
        return false;
    }
    copy_token(line + strlen("PAGE|"), page_out, page_len);
    return page_out[0] != '\0';
}

bool beacon_parse_graph_line(const char *line, BeaconGraphLine *out) {
    if (!line || !out || !starts_with(line, "GRAPH|")) {
        return false;
    }
    memset(out, 0, sizeof(*out));
    const char *rest = line + strlen("GRAPH|");
    if (strcmp(rest, "END") == 0) {
        out->op = BEACON_GRAPH_END;
        return true;
    }
    if (starts_with(rest, "BEGIN|")) {
        out->op = BEACON_GRAPH_BEGIN;
        sscanf(rest + strlen("BEGIN|"), "%d|%d", &out->a, &out->b);
        return true;
    }
    if (starts_with(rest, "E|")) {
        out->op = BEACON_GRAPH_EDGE;
        return sscanf(rest + 2, "%d|%d", &out->a, &out->b) == 2;
    }
    if (starts_with(rest, "N|")) {
        out->op = BEACON_GRAPH_NODE;
        const char *body = rest + 2;
        int index = 0;
        int x = 0;
        int y = 0;
        int deg = 0;
        char hex[8] = "94A3B8";
        const char *label = body;
        for (int field = 0; field < 5; field++) {
            const char *sep = strchr(label, '|');
            if (!sep) {
                return false;
            }
            label = sep + 1;
        }
        if (sscanf(body, "%d|%d|%d|%d|%6[^|]|", &index, &x, &y, &deg, hex) != 5) {
            return false;
        }
        out->a = index;
        out->x = x;
        out->y = y;
        out->deg = deg;
        out->color = (int)strtoul(hex, nullptr, 16);
        copy_token(label, out->label, sizeof(out->label));
        return true;
    }
    return false;
}
