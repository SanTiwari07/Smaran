# The Mars Theory

The story and language behind Smaran's Mars theme. [design.md](design.md) says how it looks; this file says what it means and how we talk about it. Every page, caption, label and demo line should follow it.

---

## 1. The one-sentence idea

**Going offline isn't a blackout. It's moving to Mars.**

A network outage is treated as a failure everywhere else: red banners, spinners, "connection lost". Smaran takes the opposite view. A device that loses its link has not broken; it has *landed*. It is now a self-sufficient crew on a planet where the relay is minutes away, and it keeps working, remembering and deciding on its own. When the relay comes back into view, the crew reports home.

That reframe is the product's whole argument: **offline is a normal place to live, not an error state.**

## 2. Why the metaphor is honest, not decoration

Mars is a real example of the exact problem Smaran solves:

- **Signal delay.** A message between Earth and Mars takes roughly 3 to 22 minutes one way, depending on where the planets are. You cannot hold a conversation, so the crew must act on its own.
- **Solar conjunction.** About every 26 months the Sun sits between Earth and Mars and communication is largely suspended for around two weeks. Missions plan for it in advance and carry on working.
- **Local autonomy.** Rovers and crews make decisions on the surface, log what they did, and send a report when a relay pass allows.
- **Two crews, one truth problem.** If two surface teams record opposite findings while out of contact, mission control cannot simply keep the later message. Someone has to look at both.

These are the same four facts as Smaran's four promises: works without a network, keeps private data on the device, syncs safely when the link returns, and flags conflicts instead of guessing.

## 3. The vocabulary shift

We stop using failure words. Offline states are described as places and activities, not damage.

| Old wording | Mars wording | Why |
|---|---|---|
| Offline | **On the surface** / **Surface mode** | The device is somewhere, not broken |
| Blackout | **Between relay passes** | Temporary and expected |
| Online / connected | **Relay in view** | Contact is a moment, not a default |
| Sync | **Report home** / **Relay pass** | It is a deliberate act |
| Outbox | **Manifest** (items waiting for the next pass) | What the crew carries |
| Reconnect | **Relay pass begins** | An event, not a repair |
| Conflict | **Two crews, one waypoint** | Sets up a human decision |
| Resolve | **Mission control decides** | Themis is the tribunal |
| Private note | **Sealed in the vault** | Krypta |
| Sync error | **Pass missed, next window in T-...** | Never a dead end |

Rules of voice:

1. Calm and factual. A missing relay is never an emergency.
2. Plain first, themed second. Every themed label keeps a plain meaning ("Surface mode" carries a subtitle: "Working offline").
3. No alarm colours for being offline. Red is reserved for real problems: a safety-critical note, a failed integrity check.
4. Time is expressed as mission time (T-00:12, Sol 003) in logs and mono labels, never in clock jargon that hides the meaning.

## 4. The narrative arc: six stages

The scroll-through story, the auto-play demo and the README all use the same six stages.

| Stage | Name | What happens | Sky |
|---|---|---|---|
| 1 | **Landing** | Two technicians each carry a device. Everything is in view and in sync. Baseline memory exists on every device. | Dusk |
| 2 | **Surface mode** | The factory Wi-Fi drops. Nothing breaks. Notes are still written, searched and filed; private ones go into the vault. The header simply reads "On the surface". | Deep dusk, stars out |
| 3 | **Two crews** | Rover A writes "CNC-07 running fine". Rover B writes "CNC-07 spindle vibration, stopped". Neither can see the other. Both are honest. | Dust haze |
| 4 | **Relay pass** | The relay rises. Manifests launch, most critical first. Resends are safe. Even a hard kill mid-pass loses nothing that was acknowledged. | Dawn |
| 5 | **Mission control decides** | Timestamp sync would have quietly kept one report. Smaran holds both at one waypoint. The supervisor chooses; the history of what each crew believed is kept. | Clear |
| 6 | **Proof** | GO / NO-GO checklist: zero private records on the server, zero acknowledged notes lost, both conflicts caught. | Daylight |

The emotional shape is *calm, then tension, then relief*, not *panic, then repair*.

## 5. Mapping the components

| Component | Mars role | One-line pitch |
|---|---|---|
| **Krypta** | Sealed habitat vault | What is private never leaves the habitat |
| **Hermes** | Supply drone carrying the manifest | Everything else rides the next relay pass, critical cargo first |
| **Agora** | Colony hub | What the whole colony knows, held on every crew's device |
| **Themis** | Mission control | Decides what is true when two crews disagree |
| **Argus** | Surface scanner | Reads every note and decides where it belongs, with a reason |

## 6. Screens under the theory

- **Devices and Sync:** each card shows "Relay in view" or "On the surface". The Comms switch becomes **Relay** with the same behaviour; turning it off retracts the dish and the sky quietly darkens. There is no red, no error toast. The toast reads "On the surface. Notes stay on this device."
- **Memory and Search:** search always works; the header notes "Searching locally" when on the surface and "Searching locally and colony" when the relay is in view.
- **Conflicts:** framed as a waypoint two crews reached with different findings. The amber pin is the only alert.
- **Prove It:** the GO / NO-GO preflight.
- **Auto-play:** narrated as a mission transmission, lower-third captions in mission time.

## 7. Naming options

The current name stays valid; the alternatives are here if a rename is wanted before the story ships.

| Option | Meaning | Fit | Notes |
|---|---|---|---|
| **Smaran** (keep) | Sanskrit, "remembrance / remembering" | Strong: memory is the product, and the component names are already Greek, so it sits comfortably beside them | Already in the repo, README and submission. Add the tagline **"Remember on Mars."** |
| **Tharsis** | The great volcanic plateau on Mars | Strong sound, obviously Mars, easy to say | Reads as a place, less as memory |
| **Areomnesis** | Ares (Mars) + *mnesis* (memory) | Says both ideas in one word | Long; mildly awkward to say |
| **Sol Ledger** | Sol = one Martian day; ledger = a kept record | Clear, plain, friendly | Sounds more like a logbook than a platform |
| **Regolith** | The dust that covers Mars | Earthy, unusual, memorable | Says nothing about memory |
| **Cairn** | A stack of stones left as a marker | Meaning: a memory left for the next traveller; works on Mars | Common word, harder to own |

**Recommendation:** keep **Smaran** as the product name and adopt **"Remember on Mars."** as the tagline. A rename now costs the README, repo, submission text and every demo line, and Smaran already carries the meaning we need. If a rename is chosen anyway, use **Tharsis**.

Sub-brand line for stage headings: **"Smaran: memory for the surface."**

## 8. Taglines

- Remember on Mars. *(primary)*
- Offline isn't a blackout. It's a landing.
- Your devices are on the surface. They know what to do.
- When the relay returns, nothing was lost.
- Two crews, one waypoint, no guessing.

## 9. Logo

**Orbit S** is the chosen mark: a geometric S built from two arcs on a rust rounded square, with a cyan dot for the relay in view. It ties to the theory directly (orbit, relay) and works as favicon, app icon and lockup. Files are in [logo/](logo), previewed in [logo-options.html](logo-options.html). Wordmark: lowercase **smaran**, Space Grotesk 700, +0.02em tracking, outlined.

## 10. What changes in the other files once this is approved

- **design.md:** offline state uses a neutral surface colour instead of red; the chip label set and the Comms toggle are renamed (edits already applied in this pass).
- **README and story:** headings and copy follow sections 3 and 4.
- **Dashboard:** labels renamed per the vocabulary table; offline no longer raises an error style.
- No backend or API changes. This is presentation and copy only.
