/* Cursor Status Panel — multi-session agent status */

import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import St from 'gi://St';

import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const BEACON_DIR = GLib.build_filenamev([
    GLib.get_home_dir(),
    '.local',
    'share',
    'cursor-agent-beacon',
]);
const STATUS_PATH = GLib.build_filenamev([BEACON_DIR, 'status.json']);
const REGISTRY_PATH = GLib.build_filenamev([BEACON_DIR, 'registry.json']);
const CURSOR_STORAGE_PATH = GLib.build_filenamev([
    GLib.get_home_dir(),
    '.config',
    'Cursor',
    'User',
    'globalStorage',
    'storage.json',
]);
const POLL_MS = 500;
const MAX_LABEL_CHARS = 24;

const STATE_CLASSES = ['idle', 'thinking', 'working', 'error'];
const BUSY_STATES = new Set([
    'waiting',
    'thinking',
    'running_shell',
    'running_mcp',
]);
const STATE_PRIORITY = {
    thinking: 0,
    running_shell: 1,
    running_mcp: 2,
    waiting: 3,
    error: 4,
    success: 5,
    idle: 6,
};

const ICONS = {
    idle: 'view-reveal-symbolic',
    thinking: 'content-loading-symbolic',
    waiting: 'user-busy-symbolic',
    terminal: 'utilities-terminal-symbolic',
    mcp: 'network-transmit-receive-symbolic',
    error: 'dialog-error-symbolic',
};

const PROFILES = {
    idle: { icon: ICONS.idle, label: 'Cursor', style: 'idle' },
    success: { icon: ICONS.idle, label: 'Ready', style: 'idle' },
    waiting: { icon: ICONS.waiting, label: 'Waiting', style: 'thinking' },
    thinking: { icon: ICONS.thinking, label: 'Thinking', style: 'thinking' },
    running_shell: {
        icon: ICONS.terminal,
        label: 'Shell',
        style: 'working',
        useMessage: true,
    },
    running_mcp: {
        icon: ICONS.mcp,
        label: 'MCP',
        style: 'working',
        useMessage: true,
    },
    error: {
        icon: ICONS.error,
        label: 'Error',
        style: 'error',
        useMessage: true,
    },
};

function readJson(path) {
    try {
        const [ok, bytes] = GLib.file_get_contents(path);
        if (!ok) return null;
        return JSON.parse(new TextDecoder().decode(bytes));
    } catch {
        return null;
    }
}

function truncate(text, limit = MAX_LABEL_CHARS) {
    const cleaned = (text || '').trim().replace(/\s+/g, ' ');
    if (!cleaned) return '';
    if (cleaned.length <= limit) return cleaned;
    return `${cleaned.slice(0, limit - 1)}…`;
}

function parseTs(value) {
    if (!value) return 0;
    const parsed = Date.parse(value);
    return Number.isNaN(parsed) ? 0 : parsed;
}

function isBusy(state) {
    return BUSY_STATES.has(state);
}

function isCursorRunning() {
    try {
        const [, , exitStatus] = GLib.spawn_command_line_sync('pgrep -x cursor');
        return GLib.spawn_check_wait_status(exitStatus);
    } catch {
        return false;
    }
}

function folderUriToPath(uri) {
    if (!uri) return '';
    try {
        const decoded = decodeURIComponent(uri);
        if (decoded.startsWith('file://')) return decoded.slice(7);
        return decoded;
    } catch {
        return uri.replace(/^file:\/\//, '');
    }
}

function readOpenWorkspaceFolders() {
    if (!isCursorRunning()) return [];
    const data = readJson(CURSOR_STORAGE_PATH);
    const windows = data?.windowsState?.openedWindows;
    if (!Array.isArray(windows)) return [];
    return windows
        .map(entry => folderUriToPath(entry?.folder || entry?.folderUri || ''))
        .filter(Boolean);
}

function sessionInOpenWindow(session, openFolders) {
    if (!openFolders.length) return false;
    const root = (session.workspace_root || '').trim();
    if (root) return openFolders.includes(root);

    const project = (session.project || '').trim();
    if (!project) return false;
    return openFolders.some(folder => {
        const parts = folder.split('/');
        return parts[parts.length - 1] === project;
    });
}

function filterVisibleSessions(sessions, openFolders) {
    return (sessions || []).filter(
        session => session.active !== false && sessionInOpenWindow(session, openFolders),
    );
}

function profileFor(status) {
    if (!status?.state) return PROFILES.idle;
    return PROFILES[status.state] ?? PROFILES.idle;
}

function pickAutoFocus(sessions) {
    const live = (sessions || []).filter(session => session.active !== false);
    if (!live.length) return null;

    live.sort((a, b) => {
        const priA = STATE_PRIORITY[a.state] ?? 99;
        const priB = STATE_PRIORITY[b.state] ?? 99;
        if (priA !== priB) return priA - priB;
        return parseTs(b.updated_at) - parseTs(a.updated_at);
    });
    return live[0];
}

function pickDisplaySession(registry, pinnedId) {
    const sessions = registry?.sessions || [];
    if (pinnedId) {
        const pinned = sessions.find(session => session.id === pinnedId);
        if (pinned) return pinned;
    }
    return pickAutoFocus(sessions) || sessions[0] || null;
}

function busyCount(sessions) {
    return (sessions || []).filter(
        session => session.active !== false && isBusy(session.state),
    ).length;
}

function formatWhen(iso) {
    if (!iso || iso === '—') return '—';
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return '—';

    const diffSec = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
    if (diffSec < 15) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
    if (diffSec < 86400) {
        return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
    return date.toLocaleString([], {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function stateLabel(state) {
    const labels = {
        idle: 'Idle',
        waiting: 'Waiting',
        thinking: 'Thinking',
        running_shell: 'Running shell',
        running_mcp: 'Running MCP',
        success: 'Ready',
        error: 'Error',
    };
    return labels[state] || state;
}

function hookLabel(hook) {
    const labels = {
        stop: 'Turn ended',
        afterAgentThought: 'Thinking',
        beforeShellExecution: 'Shell',
        afterShellExecution: 'Shell done',
        beforeMCPExecution: 'MCP',
        afterMCPExecution: 'MCP done',
        preToolUse: 'Tool',
        postToolUse: 'Tool done',
        beforeSubmitPrompt: 'Prompt',
        afterAgentResponse: 'Response',
        sessionStart: 'Session',
        sessionEnd: 'Session ended',
        subagentStart: 'Subagent',
        subagentStop: 'Subagent done',
    };
    return labels[hook] || hook;
}

function panelLabel(status, profile, activeCount) {
    const msg = truncate(status?.message);
    let text = profile.label;
    if (profile.useMessage && msg) text = msg;
    else if (profile.style === 'thinking' && msg && msg !== 'Thinking...') text = msg;

    if (activeCount > 1) text = `${text} · ${activeCount}`;
    return text;
}

function sessionMenuLabel(session, pinnedId) {
    const pin = session.id === pinnedId ? '★' : '○';
    const project = truncate(session.project || 'workspace', 16);
    return `${pin}  ${project}  ·  ${stateLabel(session.state)}  ·  ${formatWhen(session.updated_at)}`;
}

export default class CursorStatusPanelExtension extends Extension {
    enable() {
        this._settings = this.getSettings();
        this._iconName = null;
        this._styleClass = null;
        this._sessionMenuItems = [];
        this._menuSignature = '';

        this._stylesheet = Gio.File.new_for_path(
            GLib.build_filenamev([this.path, 'stylesheet.css']),
        );
        try {
            St.ThemeContext.get_for_stage(global.stage)
                .get_theme()
                .load_stylesheet(this._stylesheet);
        } catch (e) {
            console.error(`[Cursor Status Panel] stylesheet: ${e}`);
            this._stylesheet = null;
        }

        this._indicator = new PanelMenu.Button(0.0, this.metadata.name, false);

        this._box = new St.BoxLayout({
            style_class: 'cursor-status-box',
            y_align: Clutter.ActorAlign.CENTER,
        });

        this._icon = new St.Icon({
            icon_name: ICONS.idle,
            style_class: 'cursor-status-icon system-status-icon',
        });
        this._icon.y_align = Clutter.ActorAlign.CENTER;

        this._label = new St.Label({
            text: 'Cursor',
            style_class: 'cursor-status-label',
        });
        this._label.y_align = Clutter.ActorAlign.CENTER;

        this._box.add_child(this._icon);
        this._box.add_child(this._label);
        this._indicator.add_child(this._box);
        this._setStyleClass('idle');

        this._menuTitle = new PopupMenu.PopupMenuItem('Cursor Agent', {
            reactive: false,
            style_class: 'cursor-status-menu-title',
        });
        this._followRecentItem = new PopupMenu.PopupMenuItem('Follow most recent', {
            reactive: true,
        });
        this._followRecentItem.connect('activate', () => {
            this._settings.set_string('pinned-conversation-id', '');
            this._tick();
        });

        this._menuState = new PopupMenu.PopupMenuItem('Idle', {
            reactive: false,
            style_class: 'cursor-status-menu-state',
        });
        this._menuProject = new PopupMenu.PopupMenuItem('', {
            reactive: false,
            style_class: 'cursor-status-menu-project',
        });
        this._menuMessage = new PopupMenu.PopupMenuItem('No recent activity', {
            reactive: false,
            style_class: 'cursor-status-menu-detail',
        });
        this._menuMeta = new PopupMenu.PopupMenuItem('', {
            reactive: false,
            style_class: 'cursor-status-menu-meta',
        });
        this._sessionsHeader = new PopupMenu.PopupMenuItem('Open windows', {
            reactive: false,
            style_class: 'cursor-status-menu-section',
        });
        this._sessionsSection = new PopupMenu.PopupMenuSection();

        this._indicator.menu.addMenuItem(this._menuTitle);
        this._indicator.menu.addMenuItem(this._followRecentItem);
        this._indicator.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._indicator.menu.addMenuItem(this._menuState);
        this._indicator.menu.addMenuItem(this._menuProject);
        this._indicator.menu.addMenuItem(this._menuMessage);
        this._indicator.menu.addMenuItem(this._menuMeta);
        this._indicator.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._indicator.menu.addMenuItem(this._sessionsHeader);
        this._indicator.menu.addMenuItem(this._sessionsSection);

        this._positionTimers = [];
        this._pinning = false;

        delete Main.panel.statusArea[this.uuid];
        let panelSide = 'right';
        try {
            panelSide = this._settings.get_string('panel-side') || 'right';
        } catch {
            panelSide = 'right';
        }
        Main.panel.addToStatusArea(this.uuid, this._indicator, 0, panelSide);
        this._setupPositionGuard();

        this._tick();
        this._timer = GLib.timeout_add(GLib.PRIORITY_DEFAULT, POLL_MS, () => {
            this._tick();
            return GLib.SOURCE_CONTINUE;
        });
    }

    disable() {
        this._clearTimer();
        this._teardownPositionGuard();

        if (this._stylesheet) {
            St.ThemeContext.get_for_stage(global.stage)
                .get_theme()
                .unload_stylesheet(this._stylesheet);
            this._stylesheet = null;
        }

        this._clearSessionMenuItems();
        this._indicator?.destroy();
        this._indicator = null;
        this._box = null;
        this._icon = null;
        this._label = null;
        this._settings = null;
        this._menuTitle = null;
        this._followRecentItem = null;
        this._menuState = null;
        this._menuProject = null;
        this._menuMessage = null;
        this._menuMeta = null;
        this._sessionsHeader = null;
        this._sessionsSection = null;
        this._iconName = null;
        this._styleClass = null;
        this._menuSignature = '';
        this._childAddedId = 0;
        this._positionTimers = [];
        delete Main.panel.statusArea[this.uuid];
    }

    _panelBox() {
        let side = 'right';
        try {
            side = this._settings?.get_string('panel-side') || 'right';
        } catch {
            side = 'right';
        }
        return side === 'left' ? Main.panel._leftBox : Main.panel._rightBox;
    }

    _pinToFront() {
        if (this._pinning) return;
        const box = this._panelBox();
        if (!this._indicator || this._indicator.get_parent() !== box)
            return;
        const index = box.get_children().indexOf(this._indicator);
        if (index <= 0) return;

        this._pinning = true;
        box.set_child_at_index(this._indicator, 0);
        this._pinning = false;
    }

    _setupPositionGuard() {
        const box = this._panelBox();
        this._childAddedId = 0;
        this._clearPositionTimers();

        this._pinToFront();
        this._childAddedId = box.connect('child-added', (_box, child) => {
            if (this._pinning || child === this._indicator) return;
            GLib.timeout_add(GLib.PRIORITY_DEFAULT, 150, () => {
                this._pinToFront();
                return GLib.SOURCE_REMOVE;
            });
        });
        for (const delay of [2, 5, 15, 30]) {
            const id = GLib.timeout_add_seconds(GLib.PRIORITY_LOW, delay, () => {
                this._pinToFront();
                return GLib.SOURCE_REMOVE;
            });
            this._positionTimers.push(id);
        }
    }

    _clearPositionTimers() {
        for (const id of this._positionTimers || [])
            GLib.source_remove(id);
        this._positionTimers = [];
    }

    _teardownPositionGuard() {
        if (this._childAddedId) {
            this._panelBox().disconnect(this._childAddedId);
            this._childAddedId = 0;
        }
        this._clearPositionTimers();
    }

    _clearTimer() {
        if (this._timer) {
            GLib.source_remove(this._timer);
            this._timer = null;
        }
    }

    _setStyleClass(name) {
        if (this._styleClass === name) return;
        for (const cls of STATE_CLASSES) {
            this._box?.remove_style_class_name(`cursor-status-panel-${cls}`);
        }
        this._box?.add_style_class_name(`cursor-status-panel-${name}`);
        this._styleClass = name;
    }

    _setIcon(name) {
        if (this._iconName === name) return;
        this._icon.icon_name = name;
        this._iconName = name;
    }

    _clearSessionMenuItems() {
        this._sessionsSection?.removeAll();
        this._sessionMenuItems = [];
    }

    _rebuildSessionMenu(sessions, pinnedId) {
        const signature = sessions
            .map(
                session =>
                    `${session.id}:${session.state}:${session.updated_at}:${session.active}:${pinnedId}`,
            )
            .join('|');
        if (signature === this._menuSignature) return;
        this._menuSignature = signature;

        this._clearSessionMenuItems();
        const visible = sessions.filter(session => session.active !== false);
        if (!visible.length) {
            const empty = new PopupMenu.PopupMenuItem('No sessions in open windows', {
                reactive: false,
                style_class: 'cursor-status-menu-muted',
            });
            this._sessionsSection.addMenuItem(empty);
            this._sessionMenuItems.push(empty);
            return;
        }

        for (const session of visible) {
            const item = new PopupMenu.PopupMenuItem(
                sessionMenuLabel(session, pinnedId),
                { reactive: true, style_class: 'cursor-status-menu-session' },
            );
            const conversationId = session.id;
            item.connect('activate', () => {
                this._settings.set_string('pinned-conversation-id', conversationId);
                this._menuSignature = '';
                this._tick();
            });
            this._sessionsSection.addMenuItem(item);
            this._sessionMenuItems.push(item);
        }
    }

    _setMenuStateStyle(state) {
        const classes = [
            'cursor-status-menu-state-idle',
            'cursor-status-menu-state-thinking',
            'cursor-status-menu-state-working',
            'cursor-status-menu-state-error',
        ];
        for (const cls of classes)
            this._menuState?.remove_style_class_name(cls);

        const styleMap = {
            success: 'idle',
            idle: 'idle',
            waiting: 'thinking',
            thinking: 'thinking',
            running_shell: 'working',
            running_mcp: 'working',
            error: 'error',
        };
        const style = styleMap[state] || 'idle';
        this._menuState?.add_style_class_name(`cursor-status-menu-state-${style}`);
    }

    _tick() {
        if (!this._label) return;

        const registry = readJson(REGISTRY_PATH) || { sessions: [] };
        const pinnedId = this._settings.get_string('pinned-conversation-id');
        const openFolders = readOpenWorkspaceFolders();
        const sessions = registry.sessions || [];
        const visible = filterVisibleSessions(sessions, openFolders);
        const active = busyCount(visible);
        const display = pickDisplaySession({ sessions: visible }, pinnedId) || readJson(STATUS_PATH);

        const profile = profileFor(display);
        this._setIcon(profile.icon);
        this._setStyleClass(profile.style);
        this._label.text = panelLabel(display, profile, active);

        const state = display?.state ?? 'idle';
        const message = (display?.message || '').trim() || '—';
        const project = display?.project || 'workspace';
        const label = (display?.label || '').trim();
        const hook = display?.hook_event_name ?? '—';
        const ts = display?.updated_at || display?.timestamp || '—';
        const focus = pinnedId ? 'Pinned' : 'Auto';

        this._menuTitle.label.text =
            active > 0 ? `Cursor Agent  ·  ${active} active` : 'Cursor Agent';
        this._followRecentItem.label.text = pinnedId
            ? 'Unpin  ·  follow most recent'
            : 'Follow most recent';
        this._menuState.label.text = stateLabel(state);
        this._setMenuStateStyle(state);
        this._menuProject.label.text = project;
        this._menuProject.visible = Boolean(project && project !== 'workspace');
        this._menuMessage.label.text = truncate(
            label && label !== '—' ? label : message,
            64,
        );
        this._menuMeta.label.text = `${focus}  ·  ${hookLabel(hook)}  ·  ${formatWhen(ts)}`;

        this._rebuildSessionMenu(visible, pinnedId);
    }
}
