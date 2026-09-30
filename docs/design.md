# Smaran Design System: "Red Horizon"

**Status: APPROVED and FROZEN (2026-09-30).** Changes only for bugs or additions that follow these rules.

Theme: **astronauts on Mars**. Story, vocabulary and naming: [mars-theory.md](mars-theory.md); logo: [logo-options.html](../logo/logo-options.html). One visual language for every page: the mission-control dashboard, the auto-play demo, and the scroll-through story.

This document is a **one-time approval gate**. Once approved, the tokens, motifs and rules below are frozen. Later changes are limited to bug fixes and additions that follow these rules; the look itself is not reopened.

> Scope: this replaces the current look entirely. No existing image, logo, colour or illustration is carried over. Everything below is new and is built from code (CSS, inline SVG, canvas) plus open-licensed fonts, so there are no image files to manage and nothing to go stale.

---

## 1. Concept

Smaran is memory that keeps working when the network is gone. Mars is the same problem: a crew far from home, a 4 to 24 minute signal delay, and no one to phone. The metaphor is direct, so the theme is not decoration; it explains the product.

| Smaran idea | Mars metaphor | Where it shows up |
|---|---|---|
| Edge device | **Astronaut / rover** on the surface | Device cards carry a suit-helmet glyph and a call sign |
| Offline link | **On the surface** (between relay passes; not a failure) | Link switch is a "Relay" toggle; offline retracts the dish and the sky quietly darkens |
| Gateway / fleet server | **Orbital relay** ("Areostationary relay") | Sits above the horizon in diagrams |
| **Krypta** (private shard) | **Sealed habitat vault** | Locked airlock icon, no antenna |
| **Hermes** (outbox sync) | **Supply drone / data courier** | Small drone glyph on a dashed trajectory |
| **Agora** (fleet mirror) | **Colony hub** | Dome cluster glyph |
| **Themis** (conflict truth) | **Mission Control tribunal** | Two amber flags on one waypoint |
| **Argus** (placement) | **Surface scanner** | Sweeping radar arc |
| Conflict flagged | **Two crews, one waypoint** | Amber twin-beacon pulse |
| Synced / resolved | **Landing confirmed** | Green-cyan "nominal" tick |

Voice: calm, precise, a little wry. Mission-log language ("T+00:14", "Link restored", "Both reports held") but never at the cost of clarity. Every label must still read plainly to someone who has never seen a space UI.

---

## 2. Design principles

1. **Signal over spectacle.** Data is the hero. Scenery lives at the edges and in empty states, never behind dense tables.
2. **One horizon.** Every page has the same Martian horizon line as its structural anchor: ground below, sky above.
3. **Warm ground, cold instruments.** Rust and dust colours are the world; cyan and amber are the instruments. Only instruments carry meaning.
4. **Status is never colour alone.** Every state has a shape, a label and a colour.
5. **Motion explains.** Animation shows cause and effect (a packet travelling, a link dropping). If it does not teach, it is removed.
6. **Works at 60 fps on a mid laptop and a projector.** Demo day hardware is unknown.

---

## 3. Colour tokens

Dark is the default (a projector and a dim demo room). A light "Daylight on Mars" theme is defined for print and bright rooms.

### 3.1 Core palette (dark, default: "Martian Night")

| Token | Hex | Use |
|---|---|---|
| `--void` | `#0B0709` | Page background, deepest space |
| `--basalt` | `#150D10` | Base surface |
| `--regolith` | `#1F1316` | Raised card |
| `--regolith-2` | `#2A1A1D` | Hover / nested surface |
| `--ridge` | `#3A2427` | Borders, dividers |
| `--rust` | `#C1440E` | Brand primary (Mars red-orange) |
| `--rust-hot` | `#E8590C` | Primary hover, glow core |
| `--dust` | `#D9A066` | Warm secondary, highlights, rules |
| `--haze` | `#F2D3B3` | Light warm accents, dust-storm sky top |
| `--suit` | `#F5F1EA` | Astronaut-suit white: primary text, helmet |
| `--suit-dim` | `#B9AFA6` | Secondary text |
| `--suit-mute` | `#7C716B` | Tertiary text, placeholders |

### 3.2 Instrument colours (the only ones that mean something)

| Token | Hex | Meaning |
|---|---|---|
| `--telemetry` | `#3DE0E6` | Online, live, in-sync, focus ring |
| `--nominal` | `#5BE39A` | Success, resolved, verified |
| `--caution` | `#FFB020` | Contested, pending, needs a human |
| `--critical` | `#FF4D5E` | Failure, safety-critical, offline error |
| `--private` | `#B79CFF` | Krypta / private / never leaves device |

Contrast: `--suit` on `--basalt` is 15.6:1; `--suit-dim` on `--regolith` is at least 7:1; every instrument colour is at least 4.5:1 on `--regolith`. Verified with a script in CI before merge, not by eye.

### 3.3 Light theme ("Daylight on Mars")

`--void #FBF3EA`, `--basalt #F5E6D6`, `--regolith #FFFFFF`, `--ridge #E4CDB6`, text `#2B1810`, rust unchanged, instruments darkened one step to hold 4.5:1.

### 3.4 Gradients (defined once, reused everywhere)

- `--sky-dusk`: `linear-gradient(180deg, #0B0709 0%, #2A1116 45%, #7A2A12 78%, #C1440E 100%)`
- `--sky-storm`: `linear-gradient(180deg, #1A0D0F 0%, #4A1F14 60%, #A5501F 100%)` (offline / degraded)
- `--glow-rust`: `radial-gradient(60% 60% at 50% 100%, rgba(232,89,12,.35), transparent 70%)`
- `--visor`: `linear-gradient(135deg, rgba(61,224,230,.25), rgba(255,176,32,.12) 60%, transparent)` (helmet-visor reflection, used on glass panels)

---

## 4. Typography

All fonts are open-licence, loaded from Google Fonts with `display=swap`, with system fallbacks so nothing blocks rendering.

| Role | Font | Weights | Notes |
|---|---|---|---|
| Display / headings | **Space Grotesk** | 500, 700 | Wide, technical, slightly retro-futurist. Tight tracking at large sizes (`-0.02em`) |
| Body / UI | **Inter** | 400, 500, 600 | Tabular numerals on (`font-feature-settings: "tnum"`) |
| Data, IDs, logs, timestamps | **JetBrains Mono** | 400, 500 | Every device id, note id, hash, T+ clock |
| Story pull-quotes only | **Fraunces** (italic) | 400 | Human warmth against the machine type; used sparingly |

Scale (rem, 1rem = 16px, fluid via `clamp`): `12 / 13 / 14 / 16 / 18 / 22 / 28 / 36 / 48 / 72`.
Line height: 1.55 body, 1.15 display. Max measure: 68 characters.
Labels use **uppercase JetBrains Mono, 11px, +0.12em tracking** ("MISSION LOG", "LINK", "T+00:14:32"). This one style is the signature of the whole system.

---

## 5. Layout, spacing, shape

- **Grid:** 12 columns, 1200px content width, 24px gutters; 16px page gutter on phones.
- **Spacing scale:** 4, 8, 12, 16, 24, 32, 48, 72, 112.
- **Radius:** `--r-sm 6px` (chips, inputs), `--r-md 12px` (cards), `--r-lg 20px` (panels), `--r-pill 999px`. A few hero elements use a **capsule / helmet-window shape** (a stadium with a chamfered corner) as the recognisable frame.
- **Borders:** 1px `--ridge`; active panels get a 1px inner top highlight `rgba(255,255,255,.06)` to feel like anodised metal.
- **Elevation:** no drop-shadow soup. Two levels only: `--e1: 0 1px 0 rgba(255,255,255,.04) inset, 0 8px 24px rgba(0,0,0,.35)` and `--e2` for modals with the rust glow.
- **The Horizon Rule:** every page ends its hero/header region with the same horizon SVG (see 7.1). Page structure is *sky (header) / horizon / ground (content)*.

---

## 6. Signature components

Every one of these is specified once and reused. No page invents its own.

### 6.1 Mission bar (top navigation)
Slim 56px bar, `--basalt` with a hairline bottom `--ridge`. Left: **Smaran wordmark** (Space Grotesk 700, tracked) plus the **Orbit S mark** (section 7.2). Centre: four tabs with mono labels. Right: mission clock `T+HH:MM:SS` (counts from page load, ticks in mono) and a global **Relay** indicator.
Active tab: rust underline that is a 2px "landing strip" with a tiny arrow tick at the centre.

### 6.2 Panels ("Bay" cards)
`--regolith`, `--r-md`, 1px `--ridge`. Header row: mono uppercase label at left, status chip at right. Corner registration ticks (4 tiny L-shapes, `--ridge`) on the outer corners give the technical-drawing feel. Hover lifts border to `--dust` at 40 percent.

### 6.3 Status chips
Pill, mono 11px uppercase, 1px border in the instrument colour, 12 percent fill of the same colour, leading glyph:

| State | Glyph | Colour | Label |
|---|---|---|---|
| Relay in view | filled dot, pulsing | `--telemetry` | RELAY IN VIEW |
| On the surface (offline) | hollow dot + dish retracted | `--dust` | ON THE SURFACE |
| Synced | check in ring | `--nominal` | NOMINAL |
| Pending | half-ring rotating | `--caution` | IN TRANSIT |
| Contested | twin diamonds | `--caution` | CONTESTED |
| Private | padlock | `--private` | SEALED |
| Safety-critical | triangle | `--critical` | CRITICAL |

### 6.4 Buttons
- **Primary:** `--rust` fill, `--suit` text, hover `--rust-hot` plus soft outer glow, 44px minimum height.
- **Secondary:** transparent, 1px `--dust`, text `--haze`.
- **Ghost:** text only, underline on hover.
- **Danger:** `--critical` outline, fills on hover.
- Focus ring: 2px `--telemetry` offset 2px, always visible on keyboard focus.

### 6.5 Relay toggle (the offline switch)
A hardware-style toggle with a small antenna. Flipping it offline: antenna retracts, the horizon sky crossfades to a deeper dusk, chip flips to ON THE SURFACE. Offline is a place, not an error, so there is no red, no static and no error toast; the toast reads "On the surface. Notes stay on this device." Flipping online: a pulse ring expands from the antenna and queued packets visibly launch. This is the single most demo-relevant interaction and gets the best motion in the product.

### 6.6 Device card ("Crew card")
Helmet glyph (7.3) with the visor tinted by state, call sign in Space Grotesk ("ROVER-A"), device id in mono, link chip, outbox count as a **fuel-gauge** bar, last sync as mono "T-00:12 ago".

### 6.7 Data table ("Flight log")
Mono for ids and times, Inter for text. Row height 44px, zebra off, hover row `--regolith-2`. Sticky header with the mono label style. Sort arrows are tiny landing-lights. Empty state uses an illustration (7.5), never a bare "No data".

### 6.8 Conflict card ("Two crews, one waypoint")
Two report panels side by side, each with its device helmet and time, joined by a central amber **waypoint pin**. Resolve actions live in a bottom strip: "Accept A", "Accept B", "Keep both". Resolved state fills the pin `--nominal` and the card gains a "decided by" line.

### 6.9 Search bar ("Scanner")
Wide input with a sweeping radar arc that runs once when submitted. Results show a **score bar** (thin `--telemetry` line) and a "Why here" chip row explaining placement (PII rule, classifier, dedup).

### 6.10 Prove-it terminal
A recessed panel, `--void` background, mono text, green-cyan prompt, typewriter reveal for each check with a final NOMINAL / FAIL stamp. Feels like a pre-launch checklist ("GO / NO-GO").

### 6.11 Toasts, modals, tooltips
Toasts slide from the bottom-right like a radio transmission, with a small waveform and auto-dismiss at 5s (pause on hover). Modals use `--e2`, a rust top edge, and a scrim of `rgba(11,7,9,.72)` with 4px blur. Tooltips are mono 12px on `--void`.

### 6.12 Forms
Inputs: `--basalt` fill, 1px `--ridge`, focus `--telemetry` ring. Labels above in mono uppercase. Errors are `--critical` with an icon and text, never colour alone.

---

## 7. New illustration and iconography set

All new, all vector, all generated in code. Single line weight (1.75px stroke, round caps) and a two-tone fill so they read as one family.

### 7.1 Horizon (structural background)
A layered SVG landscape, four depth planes from far to near: distant crater rim, mid dunes, foreground boulders, near-ground gradient. Colours step from `--ridge` to `--rust` for atmospheric depth. Two tiny moons (Phobos and Deimos) drift very slowly across the sky. Reused on every page header, at 3 heights: hero (320px), page header (140px), footer strip (48px).

### 7.2 Logo: Orbit S (approved)
A geometric **S monogram** built from two 270-degree arcs, in Suit White on a rounded Rust square, with a single **Telemetry cyan dot** at the upper terminal: the relay in view. S for Smaran, and the arcs read as an orbit. Wordmark: lowercase "smaran", Space Grotesk 700, tracked 0.02em, outlined to paths so no font is needed. Files in [logo/](logo): `smaran-mark.svg`, `smaran-lockup-dark.svg`, `smaran-lockup-light.svg`, and two one-colour marks. Clear space equals the S stroke width times two. Minimum size 16px for the mark, 96px wide for the lockup. Also used as the favicon and app icon.

### 7.3 Astronaut set (the recurring characters)
Three stylised, faceless astronauts in suit-white with rust patches, visor showing a reflected horizon. Poses: **standing/planting a flag** (success, hero), **holding a handheld scanner** (search), **seated at a rover console** (devices). Shared proportions and a small consistent patch reading the device letter (A, B, C). Also a compact helmet glyph at 24 to 64px for cards.

### 7.4 Props and icon library (about 36 icons)
Rover, orbital relay, antenna, comms dish, habitat dome, airlock/padlock, supply drone, oxygen/fuel gauge, radar, flag on waypoint, twin-beacon, checklist, crate, solar array, meteor, dust storm, star, signal bars, satellite, telescope. Drawn on a 24px grid, exported as an inline SVG sprite (`<symbol>`), so zero network requests.

### 7.5 Empty and error states
Small scenes, each with an astronaut and a line of gentle copy:
- No notes: astronaut planting a flag on empty ground ("Nothing logged yet.")
- No conflicts: two astronauts shaking hands ("All crews agree.")
- Surface mode: astronaut looking up at a dark sky, dish retracted ("Working on the surface. Next relay pass soon.")
- Error: rover with a single loose wheel ("Something came loose. Retry.")

### 7.6 Ambient layers
- **Starfield:** canvas, about 140 stars, three parallax depths, twinkle at low amplitude.
- **Dust motes:** 30 slow particles in `--dust` at 8 percent opacity, upper regions only.
- **Reduced motion:** all of the above freeze to a static frame.

---

## 8. Page templates

Every page uses the same skeleton: **Mission bar / sky header with horizon / content on ground / footer strip**.

### 8.1 Dashboard (4 views, one shell)
| View | Hero element | Signature content |
|---|---|---|
| **Devices and Sync** | Rover-console astronaut, relay above the horizon | Crew cards, Relay toggles, fuel-gauge outbox, animated packet path device to relay |
| **Memory and Search** | Scanner astronaut | Scanner bar, three shard lanes (Krypta sealed, Hermes in transit, Agora colony), result cards with Why-here chips |
| **Conflicts and Decisions** | Two astronauts at one waypoint | Conflict cards, decision history as a mission-log timeline |
| **Prove It** | Flag-planting astronaut, checklist backdrop | Terminal panel, GO / NO-GO summary with the privacy audit and benchmark stamps |

### 8.2 Auto-play demo (`?auto`)
Full-bleed cinematic mode: horizon at the bottom, narration in a lower-third "transmission" caption, mission clock prominent, a slim progress rail with chapter ticks. Reuses the same components; only the chrome is hidden.

### 8.3 Scroll-through story
Each chapter is a **stage of the mission**: 1 Landing, 2 Surface mode (offline), 3 Two crews (conflict), 4 Relay pass (sync), 5 Mission control decides (Themis), 6 Proof. Full story and vocabulary in [mars-theory.md](mars-theory.md). The horizon stays fixed while the sky darkens and shifts from dusk to storm to dawn as you scroll. Pull-quotes in Fraunces italic. Astronauts advance across the ground line as the progress marker.

---

## 9. Motion

| Token | Value |
|---|---|
| `--ease-out` | `cubic-bezier(.16, 1, .3, 1)` |
| `--ease-inout` | `cubic-bezier(.65, 0, .35, 1)` |
| Fast / base / slow | 120ms / 220ms / 480ms |
| Cinematic (story, hero) | 900 to 1400ms |

Signature motions: packet travelling along a dashed trajectory; link drop (sky crossfade plus static); radar sweep on search; conflict pin pulse (amber, 2s loop); landing confirmation (ring expands, tick draws); typewriter in the terminal. Nothing loops faster than 1.2s. `prefers-reduced-motion: reduce` disables all loops and parallax and shortens transitions to 1ms, leaving state changes intact.

---

## 10. Accessibility and performance rules (non-negotiable)

- WCAG 2.2 AA for all text and controls; 44px minimum touch target.
- Every icon-only control has an accessible name; every chip has text.
- Full keyboard path through every view; visible focus ring everywhere.
- Colour never the only carrier of meaning (see 6.3).
- Decorative SVG and canvas are `aria-hidden`; astronaut scenes have concise alt text only when they carry meaning.
- Zero raster images. Total decorative payload under 60 KB gzipped. Fonts subset to Latin. Canvas layers pause when the tab is hidden.
- Responsive: designed at 1440, checked at 1024, 768 and 375. Tables become stacked cards below 768.

---

## 11. Implementation plan (after approval)

1. **Tokens:** one CSS file of custom properties (colour, type, spacing, motion) shared by the dashboard and the story so they cannot drift.
2. **Sprite and scenes:** the icon sprite, horizon, astronaut set and empty states as reusable SVG components.
3. **Shell:** mission bar, sky header, footer strip, ambient layers.
4. **Components:** panels, chips, buttons, tables, cards, toasts, terminal, in the order above.
5. **Pages:** Devices and Sync, Memory and Search, Conflicts and Decisions, Prove It, auto-play, story.
6. **QA pass:** contrast script, keyboard walk, reduced-motion, 375 / 768 / 1440 screenshots, projector-mode check.

No functionality or API changes are part of this work; it is purely presentation.

---

## 12. Approval checklist

Reply with **"approved"** or list changes by number. After approval this file is frozen.

- [x] **A. Concept:** astronauts on Mars, with the Smaran-to-Mars mapping in section 1
- [x] **B. Palette:** Martian Night (dark default) with rust, dust and the five instrument colours; light theme as secondary
- [x] **C. Type:** Space Grotesk, Inter, JetBrains Mono, Fraunces (story quotes)
- [x] **D. Logo:** Orbit S mark and lowercase "smaran" wordmark (chosen)
- [x] **E. Illustration:** code-generated horizon, three astronauts, about 36 icons, empty-state scenes, no image files
- [x] **F. Signature interactions:** Relay toggle with a calm sky shift; packet trajectories; radar scan; GO / NO-GO terminal
- [x] **G. Story treatment:** six mission stages with a sky that changes as you scroll
- [x] **H. Dark default:** confirmed for projector demo

Open choices with my default if you say nothing: **dark default (yes)**, **astronauts are faceless and gender-neutral (yes)**, **fonts from Google Fonts CDN (yes; say if you need them self-hosted for offline demo, which fits the product story)**.
