# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kodi add-on (`script.service.hue`) that controls Philips Hue lights based on media playback. Supports scene triggering on video/audio play/pause/stop, ambilight (real-time color matching from video frames), scheduling, and daytime/sunset automation. Requires Hue Bridge V2 (HTTPS).

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
