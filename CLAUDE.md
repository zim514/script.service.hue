# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kodi add-on (`script.service.hue`) that controls Philips Hue lights based on media playback. Supports scene triggering on video/audio play/pause/stop, ambilight (real-time color matching from video frames), scheduling, and daytime/sunset automation. Requires Hue Bridge V2 (HTTPS).

**Target Kodi versions:** Matrix (v19) and newer (Nexus v20, Omega v21, Piers v22). `addon.xml` requires `xbmc.python` ≥ 3.0.0; `kodi-addon-checker` is run with `--branch=matrix`. Python 3.8+. Do not introduce APIs added after Matrix without verifying compatibility.

**Target hardware:** low-power SBCs — Raspberry Pi (assume Pi 3-class as the floor) and Amlogic SoC boxes (S905-class and up, common on CoreELEC / Android TV). The addon runs alongside Kodi playback, so CPU and RAM headroom is tight. Design implications:

- Throttle hot loops. The 1 Hz main service loop and ambilight update-interval / capture-size / `MINIMUM_COLOR_DISTANCE` settings exist to keep CPU usage down — treat tightening any of them as a perf tradeoff.
- Avoid unnecessary HTTP calls; cache bridge state where it's safe (`scene_data` is fetched once on connect).
- Don't add a dependency for convenience. The codebase uses stdlib `socket`+`struct` for mDNS instead of pulling in `zeroconf` for this reason.
- No per-frame logging in the ambilight loop.
- `ThreadPoolExecutor` in `ambigroup.py` is sized to `len(ambi_lights) * 2` deliberately — don't expand it without reason.

## Kodi API rules (must follow)

These are hard rules for this addon — see also `~/.claude/projects/.../memory/kodi-service-addon-requirements.md` and `kodi-api-reference.md`.

- **All service-loop sleeps go through `xbmc.Monitor.waitForAbort(timeout)`.** Never `xbmc.sleep()`, `time.sleep()`, or `threading.Event.wait()` for waits in service code — they don't observe Kodi's abort signal and will hang shutdown. `SettingsMonitor` extends `xbmc.Monitor`; pass it down rather than instantiating new monitors.
- **`waitForAbort` can only be interrupted by abort, not by internal flags.** To stop a long wait early for non-abort reasons (e.g. `Timers.stop()`, settings change), poll in short `waitForAbort(1)` chunks and re-check your flags each tick.
- **Don't block inside Kodi callbacks** (`Monitor.on*`, `Player.on*`). They run on Kodi's thread — enqueue work, return fast.
- **Don't `setSetting*` inside `onSettingsChanged` unconditionally** — it re-fires the callback. Compare to current value first.
- **Window-property IPC (`kodiutils.cache_get/cache_set`) is not atomic across read-then-write.** The `service.py` and `plugin.py` processes share Window 10000 — any check-and-clear (e.g. `_process_action`) needs application-level coordination.
- **`xbmc.Player` subclasses must be kept alive** for the addon's lifetime, or callbacks stop firing. `HueService.light_groups` holds them — don't drop that reference.
- **Setting IDs are case-sensitive.** `setSetting('EnableSchedule', …)` ≠ `setSetting('enableSchedule', …)`.

## Code comments

This project **keeps code-restating comments** — the maintainer uses them to navigate files. This overrides Claude Code's global default of "don't explain WHAT the code does."

- **Do not strip** existing comments when editing, even if they only restate the next line.
- **Do not propose stripping** them in audits or refactors. If a comment is *factually wrong* (refers to a removed function, wrong behavior), fix it; otherwise leave it.
- **New code may include** restating comments; match the surrounding file's style.
- **Still avoid** comments that reference specific callers, fixes, or issue numbers ("used by X", "added for Y", "from #123") — those rot when surrounding code moves. Describe behavior, not history.

## Commands

**Validate addon structure:**
```
kodi-addon-checker --branch=matrix ./script.service.hue
```

**Regenerate language mappings** (after adding new translatable strings):
```
python language_gen.py
```
This reads `strings.po` (en_gb), scans source for `_("string")` calls, assigns IDs in the 30000-35000 range, and regenerates `resources/lib/language.py` below the `# GENERATED` marker.

**Install dependencies:**
```
pip install -r requirements.txt
```

## Architecture

All addon source lives under `script.service.hue/`. The outer directory is the repo root.

### Entry Points

- **`service.py`** — Persistent background service. Calls `core.core_dispatcher()` which either handles a CLI command (discover, sceneSelect, ambiLightSelect) or starts `HueService.run()` as the main loop.
- **`plugin.py`** — Plugin UI entry point. Instantiates `menu.Menu()` for user-facing navigation.

### Core Modules (`resources/lib/`)

| Module | Role |
|---|---|
| `core.py` | Service dispatcher, `HueService` main loop (1/sec polling), `CommandHandler`, `Timers` thread (sunset/morning) |
| `hue.py` | Hue Bridge API V2 client. HTTPS + `hue-application-key` auth. Discovery (N-UPnP), device/scene fetching, retry with exponential backoff |
| `lightgroup.py` | `LightGroup` extends `xbmc.Player` — triggers scenes on playback events (onAVStarted/onPlayBackPaused/onPlayBackStopped). `ActivationChecker` filters by media type, duration, daytime, schedule |
| `ambigroup.py` | `AmbiGroup` extends `LightGroup` — real-time ambilight via frame capture, PIL image processing, RGB→XY color conversion, ThreadPoolExecutor for parallel light updates |
| `settings.py` | `SettingsMonitor` extends `xbmc.Monitor` — loads/validates all addon settings, reacts to changes |
| `menu.py` | Plugin route handler for UI menus (status, toggle, actions) |
| `kodiutils.py` | Kodi helpers: logging, notifications, window-property caching, time conversion |
| `language.py` | Auto-generated i18n string mapping (do not edit below `# GENERATED` marker) |
| `reporting.py` | Rollbar error reporting with sensitive data scrubbing |
| `rgbxy/` | RGB↔CIE1931 XY color conversion library (Gamut A/B/C) |
| `__init__.py` | Global constants, threading Events (`BRIDGE_SETTINGS_CHANGED`, `AMBI_RUNNING`), addon metadata |

### Key Patterns

- **Light group IDs:** Video=0, Audio=1, Ambilight=3
- **Inter-process communication:** Window properties via `cache_get()`/`cache_set()` in `kodiutils.py`
- **Threading:** Main service loop on main thread; `Timers` on daemon thread; ambilight capture loop on separate thread with `ThreadPoolExecutor`
- **Localization:** 90+ languages managed via Weblate. Source strings in `resources/language/resource.language.en_gb/strings.po`. Use `_("string")` pattern for translatable strings.
- **Copyright header:** All source files include SPDX MIT license header
- **Logging prefix:** `[SCRIPT.SERVICE.HUE]`

### Settings

UI settings defined in `resources/settings.xml` with conditional visibility. Settings loaded by `SettingsMonitor` and accessed as properties. Bridge connection settings trigger reconnection via `BRIDGE_SETTINGS_CHANGED` event.

## CI/CD

- **check.yml** — Runs `kodi-addon-checker` on push/PR
- **release.yml** — Creates GitHub release on tag push
- **submit.yml** — Manual workflow to submit to official Kodi addon repo
- Translations synced automatically from Weblate
