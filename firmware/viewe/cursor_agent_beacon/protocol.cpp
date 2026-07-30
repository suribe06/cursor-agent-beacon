#include "protocol.h"

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
