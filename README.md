# Campfire

<p align="center">
  <a href="README.md">English</a> |
  <a href="README.zh-CN.md">中文</a> |
  <a href="README.ja.md">日本語</a>
</p>

A self-contained interactive night campfire scene built with Three.js.  
The project runs from a single `index.html` file, with Three.js loaded from a CDN. No build step or dependency installation is required.

---

## Overview

**Campfire** is an interactive browser-based campfire demo. It combines particle-based flames, sparks, smoke, moonlight, fog, simple weather controls, and procedural Web Audio to create a quiet nighttime camping atmosphere.

It is suitable for learning and experimenting with:

- Three.js scene construction
- Particle-based flame, spark, and smoke effects
- Procedural Web Audio synthesis
- 3D positional sound and distance attenuation
- Simple physical simulation
- Real-time parameter control
- Multilingual UI interaction

---

## Features

### Night Campfire Scene

The scene contains flames, logs, sparks, smoke, moonlight, fog, cloud cover, light rain, and a dark outdoor environment.

### Real-time Parameter Panel

The upper-right parameter panel provides real-time sliders for:

- Flame intensity
- Thermal buoyancy
- Spark emission rate
- Smoke amount
- Wind speed
- Master volume
- Crackle frequency
- Distance attenuation
- High-frequency air absorption
- Rain intensity
- Cloud amount
- Moon phase
- Moonlight intensity
- Fog density
- Exposure

All parameters take effect immediately.

### Add Wood Interaction

Clicking **Add Wood** throws a log into the campfire. The interaction includes:

- Parabolic motion
- Rolling animation
- Spark burst
- Smoke puff
- 3D positional impact sound
- Fuel increase
- Stronger flame
- Temporarily increased crackling sounds

Fuel gradually burns down over time, and the fire slowly returns to its original state.

### Campfire Interactions

Four campfire interactions can run independently:

- **Roast Marshmallow**: a marshmallow is held over the fire and gradually caramelizes.
- **Boil Water**: a kettle is suspended above the flame and produces steam when heated.
- **Light Torch**: a torch is lit by the fire and can be extinguished by clicking again.
- **Throw Pinecone**: a pinecone lands in the fire, producing sparks and adding a small amount of fuel.

### Trilingual UI

The interface supports instant switching between:

- Chinese
- English
- Japanese

Buttons, status messages, and progress feedback update with the selected language.

### Procedural Audio

All sounds are generated in real time using the Web Audio API. No external audio files are required.

Generated sounds include:

- Low-frequency fire rumble
- Wood crackling
- Occasional loud pops
- Log impact sound
- Distance-based attenuation
- Air absorption that makes distant fire sounds softer and darker

---

## How to Run

Because this project uses ES Modules, open it through a local HTTP server.

```bash
python -m http.server 8341
```

Then visit:

```text
http://localhost:8341
```

After entering the page, click anywhere to enable audio. Most browsers require a user gesture before Web Audio can start.

---

## Controls

| Action | Description |
|---|---|
| Drag mouse | Rotate camera |
| Mouse wheel | Zoom in or out |
| Click page | Start audio |
| Click “Add Wood” | Add a log to the campfire |
| Click interaction buttons | Roast marshmallow, boil water, light torch, or throw pinecone |
| Adjust parameter panel | Change fire, audio, weather, and environment effects in real time |

---

## Physical and Visual Simulation

| Effect | Implementation |
|---|---|
| Distance-based sound attenuation | `PositionalAudio` with an inverse distance model |
| Binaural positioning | HRTF spatial audio |
| Air absorption | High frequencies decrease with distance |
| Light falloff | Point light with inverse-square decay |
| Flame motion | Thermal buoyancy, drag, turbulence, and inward force |
| Flame layers | Blue base, bright yellow-white core, and orange-red outer flame |
| Spark movement | Gravity, drag, and thermal plume lift |
| Smoke diffusion | Upward movement, expansion, wind drift, and fade-out |
| Crackling sound | Randomly scheduled short burst sounds |
| Fire rumble | Low-frequency noise linked to flame intensity |

---

## Project Structure

```text
Campfire/
├── index.html
├── README.md
├── README.zh-CN.md
├── README.ja.md
├── assets/
│   └── textures/
├── scripts/
└── .claude/
```

---

## Notes

- This project is designed as a lightweight browser-based demo.
- No build step is required.
- Audio starts only after a user gesture because of browser autoplay policies.
- For the best experience, use a modern desktop browser.

---

## License

No license has been specified yet. If you plan to share or reuse this project publicly, consider adding a license such as MIT.
