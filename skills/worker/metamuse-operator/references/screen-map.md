# Muse screen map (measured 2026-11-11, Muse 11.1, macOS 26, 1920x1080)

All coordinates for the main window are **relative to the window's top-left** after `muse.py pin`, which puts the window at **587,30, size 1200x800**. The absolute coordinate = window origin + relative. Settings is a separate window and isn't pinned: its numbers are **absolute** and need a `shot` check first.

The window has 4 columns: the **rail** (x 0 to 78), the **list column** (x 78 to 318), the **content** (x 318 to 1200, or 318 to 900 when the Activity panel is open), and the **Activity panel** (x 900 to 1200).

## Rail (x = 39)

| y | Item | Shortcut |
|---|---|---|
| 66 | Avatar (Muse) | — |
| 212 | Chat | ⌘J |
| 268 | Search palette (recent chats) | ⌘K |
| 324 | Feed | — |
| 380 | Ideas | — |
| 436 | Goals | — |
| 492 | Library (files) | — |
| 564 | `+` new (untested) | — |
| 766 | Menu → Keyboard shortcuts (⌘/), Report an issue, Settings (⌘,) | — |

## Chat view

| Rel x,y | Element | Notes |
|---|---|---|
| 163,30 | Search box | Filters chats |
| 163,77 | **Main chat** | Justin's live desk. Agents don't post here |
| 289,114 | `+` New side chat | The chat is created when the first message sends. Esc or ⇧Esc discards it |
| 163,150 + 37·n | Side-chat rows (n = 0, 1, …) | 13 rows on 2026-11-11; blue dot = unread. The newest new chat goes to the top |
| 39,660 | Empty rail gap (between `+` and the menu) | Safe focus click before ⌘A. Not 180,700: side-chat rows reach there once you have about 15 chats |
| ~1053,30 / 1158,30 | **Call** / Invite | DANGER: Call starts a voice call. With the Activity panel open, Call moves to about 700,30 |
| 402,755 | `+` attach | Native macOS open panel (⇧⌘G path) |
| 700,755 | Composer text | Click to focus. Return sends |
| 1077,755 | Mic (dictation) | — |
| 1113,755 | Send / Stop (square while running) | Clicking the square stops the run |
| 1169,30 | X: closes the Activity panel, or closes an open SOUL/MEMORY editor | — |

## Activity panel (`/activity` in the composer)

| Rel x,y | Element |
|---|---|
| 913,319 | Tab 1, List: "N scheduled tasks", Today's run log (each run: title, status such as Interrupted, time) |
| 1020,319 | Tab 2, Shield: **Approvals history** (Timed out, Always allowed, Allowed once …) |
| 1126,319 | Tab 3, Fingerprint: name (Edit), **SOUL** card (933,543), **MEMORY** card (1106,543) |
| 1013,534 | "See all scheduled tasks" (on Tab 1): a modal with tasks grouped Daily, Hourly …; close with its X |

Scheduled tasks on 2026-11-11: **Daily funding groups new-post monitoring** (daily, next Nov 12 8:51 am) and **Heartbeat** (every 30 minutes).

## Library (rail 492)

| Rel x,y | Item |
|---|---|
| 163,113 / 151 | Spaces / Documents |
| 163,265 / 302 / 339 | Images / Videos / Podcasts |
| 163,763 | **System files** |
| 443, rows | System files rows, 49 px apart, starting at y 177: agents (246 sub-agent folders, each with `sessions/`), assets, config, data, docs, dreams, hooks, memory, side-chats, subscriptions (activity_feed, device_syncs, spaces_actions), user (holds `files/` with uploads such as `MetaMuse_charter.md`), workspace, AGENTS.md. Clicking toggles a folder open inline. Expand from the bottom up so the rows above don't move. The file table isn't copyable text: use shots, or ask Muse to print a file. |

## Settings window (⌘,), absolute pixels

Sidebar at x = 870: General 182 · Connectors 218 · Computer use 254 · File system access 290 · Dictation 326 · Wallet 362 · Secure store 398 · Permissions 434 · Messaging channels 470 · Devices 506 · Data controls 542 · Voice and avatar 578 · Help 614 · Legal 650 · **Log out 698 (never)**.

- Connectors → **Connected** tab (1419,256) → View (x 1525): Browser 328, ClickUp 377, Facebook 426, HighLevel 474, Instagram 524, Slack 573, Threads 622. Back button (1041,159).
- Inside a connector, scroll with Page Down (`muse.py pagedown`). Each tool shows Allow or Ask in a dropdown. **Never change one.**
- Close Settings with ⌘W.

## Connector tool states

Each connector lists its tools with Allow or Ask. **Check which scopes are allowed before acting, and ask Justin before any write.** Never change a dropdown. Which account each connector uses and its current scopes are Justin's private notes, given at intake if needed.

## Settings facts

- Plan and usage: check Settings → General; every scheduled task inside Muse spends the plan's allowance.
- Computer use, messaging channels, data controls and Reset Muse are Justin's settings: read only, never change.

## Keyboard

⌘J chat · ⌘K search · ⌘F find · ⇧⌘K search chat · ⌘, settings · ⌘/ shortcuts · ⌘. all panels · ⇧Esc focus composer (DON'T use it on an empty new side chat) · ⇧⌘D dictation · ⌘W close window · Esc dismiss **and stop a running response** · ⌥Space quick access (global) · ⌥⌘Space start a voice call (global) · ⌘= / ⌘- / ⌘0 zoom.

Slash: `/status`, `/compact`, `/clear`, `/usage on|off`, `/subagents [-a] [limit]`, `/stop`, `/latest`, `/activity`.

## Under the hood

- Bundle `/Applications/Muse.app`, id `com.meta.endo`, Sparkle updater, SwiftUI with one WKWebView (3 `WebContent` processes, about 650 MB).
- URL schemes `hatch://` (login only) and `endo-window://`. No useful deep links were found.
- Preferences in `defaults read com.meta.endo` (hatch_selected_model `auto/auto`, quick-invoke `optionSpace`).
- `~/Library/Application Support/Muse/ChromeBridge/` is a Chrome native-messaging host, so Muse can also drive Chrome through its extension.
- AX: System Events sees only the window frame, the Call, Dictate and traffic-light buttons. Setting `AXEnhancedUserInterface` exposes nothing more; it was tried and set back to false.

## Muse's own tools

Muse's agent runs on Meta's cloud VM, not on the Mac. Ask Muse which tools it has (Facebook and Instagram reads, scheduled tasks, its own memory and files) and which connectors are linked; asking "which tools did you use" at the end of a prompt is a cheap audit. Its scheduled tasks are listed with `cron.list`.
