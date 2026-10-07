# Westfab — STL & Preview Generation Guide

Internal workflow notes for producing Gridfinity STLs and clean product/listing
previews (e.g. for eMAG). This documents the westfab-specific tooling layered on
top of the upstream [kennetek/gridfinity-rebuilt-openscad](https://github.com/kennetek/gridfinity-rebuilt-openscad)
project.

---

## Prerequisites

| Tool | Purpose | Install |
|------|---------|---------|
| OpenSCAD | Generate STL geometry from `.scad` sources | `brew install --cask openscad` (binary: `openscad` on PATH) |
| Blender 5.x | Render preview images | `brew install --cask blender` (binary: `/Applications/Blender.app/Contents/MacOS/Blender`) |
| GitHub CLI | Push to fork / sync upstream | `brew install gh` |

All commands below are run from the repo root:
`/Users/petruisfan/workspace/gridfinity-rebuilt-openscad`

---

## 1. Generating STLs

STLs are **not** committed (they're in `.gitignore`); regenerate them from the
`.scad` sources as needed. Output goes to `stl/bins/` and `stl/baseplates/`.

### Bins

```bash
./generate_bins.sh
```

Produces `stl/bins/bin_<x>x<y>x<gridz>.stl` for every size in the configured
range. Edit the variables at the top of `generate_bins.sh` to control output:

| Variable | Default | Meaning |
|----------|---------|---------|
| `XMIN/XMAX`, `YMIN/YMAX` | `1..5` | Footprint size range (grid units) |
| `GRIDZ` | `5` | Height in 7 mm units (5 → 35 mm usable) |
| `INCLUDE_LIP` | `true` | Stacking lip (set `false` to remove) |
| `SCOOP` | `0` | Scoop weight (0 = none, 1 = regular) |
| `STYLE_TAB` | `5` | Label tab: 0 Full, 1 Auto, 2 Left, 3 Center, 4 Right, 5 None |
| `MAGNET_HOLES` / `SCREW_HOLES` / `REFINED_HOLES` | `false` | Base hole options |
| `ONLY_CORNERS` | `false` | Only cut holes at corners (faster prints) |

### Baseplates

```bash
./generate_baseplates.sh
```

Produces `stl/baseplates/baseplate_<x>x<y>.stl`. Options at the top of the script:

| Variable | Default | Meaning |
|----------|---------|---------|
| `XMIN/XMAX`, `YMIN/YMAX` | `1..5` | Size range (grid units) |
| `STYLE_PLATE` | `0` | 0 thin, 1 weighted, 2 skeletonized, 3 screw-together, 4 screw-together minimal |
| `STYLE_HOLE` | `0` | Mounting holes: 0 none, 1 countersink, 2 counterbore |
| `ENABLE_MAGNET` | `false` | 6 mm × 2 mm magnet holes |

### One-off custom size

Skip the scripts and call OpenSCAD directly:

```bash
openscad -o stl/bins/bin_3x2x6.stl \
  -D gridx=3 -D gridy=2 -D gridz=6 -D include_lip=true \
  gridfinity-rebuilt-bins.scad
```

---

## 2. Generating previews

Clean white-background product renders live in `westfab-previews/`. The Blender script is
the single source of visual consistency — camera framing, lighting, matte
materials, bin seating, and the white background are all fixed. You only change
the **layout JSON**. Rendered PNGs go to `westfab-previews/output/` (gitignored).

### Render a layout in all three colors

```bash
westfab-previews/render_preview.sh westfab-previews/layouts/WF-GF-4X4.json
# → westfab-previews/output/WF-GF-4X4_white_preview.png, _gray_, _black_
```

Specific colors only:

```bash
westfab-previews/render_preview.sh westfab-previews/layouts/WF-GF-4X4.json black
westfab-previews/render_preview.sh westfab-previews/layouts/WF-GF-4X4.json white gray
```

Single render / custom hex color:

```bash
/Applications/Blender.app/Contents/MacOS/Blender --background \
  --python westfab-previews/render_layout.py -- \
  --config westfab-previews/layouts/WF-GF-4X4.json --color '#ff8800' --res 2000
```

### Options (passed after `--`)

| Flag | Default | Meaning |
|------|---------|---------|
| `--config` | *(required)* | Layout JSON path |
| `--color` | JSON `color` | `white` \| `gray` \| `black` \| `#RRGGBB` |
| `--out` | `westfab-previews/output/<stem>_<color>_preview.png` | Output PNG |
| `--res` | `1600` | Square resolution (px) |
| `--samples` | `160` | Cycles samples (higher = cleaner, slower) |
| `--layer-height` | `0.4` | FDM layer-line height in mm; `0` disables (smooth matte). Bigger = more visible ridges |

### PLA / FDM look

Parts use a procedural PLA material: matte plastic plus horizontal **layer
lines** generated from the object's Z coordinate (no downloaded texture — it's
all shader nodes, so it scales to any part). `--layer-height` controls ridge
spacing:

- `0.2` — true fine layer height; realistic but nearly invisible unless you
  render high-res (`--res 3200`) and zoom in.
- `0.4` (default) — accurate and faintly visible at normal size.
- `0.6`–`1.0` — progressively more pronounced "clearly 3D-printed" ridges.
- `0` — no layer lines, smooth matte plastic.

### Defining a new layout

Create a JSON file in `westfab-previews/layouts/`. Example (`WF-GF-4X4.json`):

```json
{
  "baseplate": "baseplates/baseplate_4x4.stl",
  "color": "gray",
  "placements": [
    {"stl": "bins/bin_2x2x5.stl", "col": 0, "row": 0, "w": 2, "l": 2},
    {"stl": "bins/bin_1x3x5.stl", "col": 0, "row": 2, "w": 3, "l": 1}
  ]
}
```

- Paths are relative to `stl/`.
- `col`/`row` are 0-indexed grid cells (**col** from left, **row** from bottom).
- `w`/`l` are the bin footprint in grid units; bins auto-rotate to match.
- Bins are automatically **seated into the baseplate sockets** (bin bottom = plate
  bottom) so the plate reads as a tight base, not an oversized tray.

> Make sure the STLs referenced in the layout exist in `stl/` first (run the
> generation scripts). The 4×4 set uses `bin_1x4x5`, `bin_1x3x5`, `bin_2x2x5`,
> `bin_1x2x5`, `bin_1x1x5` and `baseplate_4x4`.

---

## 3. Git workflow (fork + upstream)

This clone is a westfab fork of kennetek's project.

- `origin` → `github.com/westfab-ro/gridfinity-rebuilt-openscad` (our fork — push here)
- `upstream` → `github.com/kennetek/gridfinity-rebuilt-openscad` (original — pull updates)

### Save our work

```bash
git add westfab-previews/ westfab-instructions.md .gitignore
git commit -m "..."
git push origin main
```

### Pull upstream updates

```bash
git fetch upstream
git merge upstream/main   # our changes live in new files, so merges are clean
git push origin main
```

---

## Products

- **First eMAG product:** 7-piece 4×4 organizer set — 1× baseplate 4×4, 1× bin
  1×4, 1× bin 1×3, 1× bin 2×2, 2× bins 1×2, 1× bin 1×1 (tiles all 16 cells).
  Layout: `westfab-previews/layouts/WF-GF-4X4.json`. Vault record: `WF-GF-4X4`.
  After rendering, see `company-os/1_Products/_docs/Product images.md` for
  OneDrive, JPEG conversion and the R2 upload.
