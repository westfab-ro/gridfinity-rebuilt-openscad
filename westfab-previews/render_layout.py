#!/usr/bin/env python3
"""
Render a clean white-background product preview of a Gridfinity layout.

Usage (headless Blender):
  blender --background --python westfab-previews/render_layout.py -- \
      --config westfab-previews/layouts/WF-GF-4X4.json --color gray

Options (after the `--`):
  --config PATH   Layout JSON (see westfab-previews/layouts/WF-GF-4X4.json). Required.
  --color NAME    white | gray | black | #RRGGBB. Overrides config "color".
  --out PATH      Output PNG. Default: westfab-previews/output/<config-stem>_<color>_preview.png
  --res N         Square resolution in px (default 1600).
  --samples N     Cycles samples (default 160).

Layout JSON schema:
  {
    "baseplate": "baseplates/baseplate_4x4.stl",   // relative to stl/
    "color": "gray",                                // optional default color
    "placements": [                                 // one entry per bin
      {"stl": "bins/bin_2x2x5.stl", "col": 0, "row": 0, "w": 2, "l": 2}
    ]
  }
col/row are 0-indexed grid cells (col from left, row from bottom); w/l are the
bin footprint in grid units. Bins are auto-rotated to match w x l and seated
into the baseplate sockets. Keeping this script fixed keeps every preview
visually consistent.
"""
import bpy, math, os, sys, json
from mathutils import Vector

# ---------- args ----------
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
def arg(name, default=None):
    return argv[argv.index(name) + 1] if name in argv else default

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STL = os.path.join(REPO, "stl")

CONFIG = arg("--config")
if not CONFIG:
    raise SystemExit("--config is required")
cfg = json.load(open(CONFIG))
COLOR_NAME = arg("--color", cfg.get("color", "gray"))
RES = int(arg("--res", 1600))
SAMPLES = int(arg("--samples", 160))
stem = os.path.splitext(os.path.basename(CONFIG))[0]
OUT = arg("--out", os.path.join(REPO, "westfab-previews", "output", f"{stem}_{COLOR_NAME}_preview.png"))
os.makedirs(os.path.dirname(OUT), exist_ok=True)

# ---------- color -> (rgb, roughness, specular) ----------
NAMED = {
    "white": ((0.72, 0.72, 0.73), 0.82, 0.20),
    "gray":  ((0.22, 0.22, 0.24), 0.50, 0.50),
    "black": ((0.02, 0.02, 0.02), 0.50, 0.50),
}
if COLOR_NAME in NAMED:
    COLOR, ROUGH, SPEC = NAMED[COLOR_NAME]
else:  # hex like #RRGGBB, sRGB -> linear-ish approx
    h = COLOR_NAME.lstrip("#")
    srgb = tuple(int(h[i:i+2], 16) / 255 for i in (0, 2, 4))
    COLOR = tuple(c ** 2.2 for c in srgb)
    light = (0.2126*COLOR[0] + 0.7152*COLOR[1] + 0.0722*COLOR[2]) > 0.36
    ROUGH, SPEC = (0.82, 0.20) if light else (0.50, 0.50)
LUM = 0.2126*COLOR[0] + 0.7152*COLOR[1] + 0.0722*COLOR[2]
LIGHT_PART = LUM > 0.36  # light products need less ambient fill to read on white

# ---------- scene ----------
bpy.ops.wm.read_factory_settings(use_empty=True)

def make_mat(name, rgb, rough=0.5, spec=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec
    return m

def make_pla_mat(name, rgb, rough, spec, layer_h):
    """Matte plastic with procedural FDM layer lines (horizontal ridges in Z).

    Object-space Z (in mm) drives a sine wave with period == layer_h, fed into a
    Bump node so the surface shows fine print layers. Also adds a little
    roughness variation between layers for a realistic semi-matte PLA look.
    """
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nodes, links = nt.nodes, nt.links
    b = nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    if "Specular IOR Level" in b.inputs:
        b.inputs["Specular IOR Level"].default_value = spec

    tc = nodes.new("ShaderNodeTexCoord")
    sep = nodes.new("ShaderNodeSeparateXYZ")
    links.new(tc.outputs["Object"], sep.inputs["Vector"])
    # Z / layer_h -> one unit per printed layer
    div = nodes.new("ShaderNodeMath"); div.operation = 'DIVIDE'
    div.inputs[1].default_value = max(layer_h, 1e-4)
    links.new(sep.outputs["Z"], div.inputs[0])
    # ping-pong(x, 1) -> triangle wave 0..1 each layer = crisp scallop ridges
    tri = nodes.new("ShaderNodeMath"); tri.operation = 'PINGPONG'
    tri.inputs[1].default_value = 1.0
    links.new(div.outputs["Value"], tri.inputs[0])

    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.7
    bump.inputs["Distance"].default_value = layer_h * 0.9
    links.new(tri.outputs["Value"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], b.inputs["Normal"])

    # subtle roughness banding between layers
    rr = nodes.new("ShaderNodeMapRange")
    rr.inputs["From Min"].default_value = 0.0
    rr.inputs["From Max"].default_value = 1.0
    rr.inputs["To Min"].default_value = max(rough - 0.06, 0.0)
    rr.inputs["To Max"].default_value = min(rough + 0.06, 1.0)
    links.new(tri.outputs["Value"], rr.inputs["Value"])
    links.new(rr.outputs["Result"], b.inputs["Roughness"])
    return m

LAYER_H = float(arg("--layer-height", 0.4))  # mm; 0 disables layer lines
if LAYER_H > 0:
    part_mat = make_pla_mat("Part", COLOR, ROUGH, SPEC, LAYER_H)
else:
    part_mat = make_mat("Part", COLOR, ROUGH, SPEC)

def import_stl(path):
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=path)
    obj = (set(bpy.data.objects) - before).pop()
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT'); obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='BOUNDS')
    bpy.ops.object.shade_smooth()
    obj.data.materials.clear(); obj.data.materials.append(part_mat)
    return obj

def wmin_z(o):
    return min((o.matrix_world @ Vector(c)).z for c in o.bound_box)

# baseplate
plate = import_stl(os.path.join(STL, cfg["baseplate"]))
plate.location = (0, 0, 0); bpy.context.view_layer.update()
plate.location.z -= wmin_z(plate); bpy.context.view_layer.update()
plate_x, plate_y = plate.dimensions.x, plate.dimensions.y
ncol = round(plate_x / 42.0); nrow = round(plate_y / 42.0)
cell = plate_x / ncol
edge_x, edge_y = -plate_x / 2.0, -plate_y / 2.0

# bins (seated into sockets: bin bottom = plate bottom)
parts = [plate]
for p in cfg["placements"]:
    obj = import_stl(os.path.join(STL, p["stl"]))
    w, l = p["w"], p["l"]
    ux, uy = round(obj.dimensions.x / 42.0), round(obj.dimensions.y / 42.0)
    if (ux, uy) != (w, l):
        obj.rotation_euler = (0, 0, math.radians(90)); bpy.context.view_layer.update()
    obj.location = (edge_x + cell*(p["col"] + w/2.0), edge_y + cell*(p["row"] + l/2.0), 0)
    bpy.context.view_layer.update()
    obj.location.z -= wmin_z(obj); bpy.context.view_layer.update()
    parts.append(obj)

# world: pure white to camera, low ambient fill so shapes read on white
world = bpy.data.worlds.new("W"); bpy.context.scene.world = world; world.use_nodes = True
nt = world.node_tree; nt.nodes.clear()
out = nt.nodes.new("ShaderNodeOutputWorld"); mix = nt.nodes.new("ShaderNodeMixShader")
lp = nt.nodes.new("ShaderNodeLightPath")
bg_cam = nt.nodes.new("ShaderNodeBackground"); bg_lit = nt.nodes.new("ShaderNodeBackground")
bg_cam.inputs["Color"].default_value = (1, 1, 1, 1); bg_cam.inputs["Strength"].default_value = 1.0
bg_lit.inputs["Color"].default_value = (1, 1, 1, 1)
bg_lit.inputs["Strength"].default_value = 0.15 if LIGHT_PART else 0.28
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
nt.links.new(bg_lit.outputs["Background"], mix.inputs[1])
nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

# white floor to catch soft contact shadow
bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
floor = bpy.context.active_object
fm = make_mat("Floor", (1, 1, 1), 1.0); floor.data.materials.append(fm)

# lighting (scales with plate size)
def area(name, loc, energy, size, rot):
    l = bpy.data.lights.new(name, 'AREA'); l.energy = energy; l.size = size
    o = bpy.data.objects.new(name, l); o.location = loc; o.rotation_euler = rot
    bpy.context.collection.objects.link(o)
S = plate_x
area("Key",  (-S*1.1, -S*1.1, S*1.6), S*S*22, S*1.2, (math.radians(48), 0, math.radians(-45)))
area("Fill", ( S*1.2, -S*0.7, S*1.0), S*S*11, S*1.2, (math.radians(55), 0, math.radians(50)))
area("Top",  (0, 0, S*2.0),           S*S*16, S*1.8, (0, 0, 0))

# camera: 3/4 view, auto-fit to all parts with margin
sc = bpy.context.scene
sc.render.resolution_x = RES; sc.render.resolution_y = RES
corners = [o.matrix_world @ Vector(c) for o in parts for c in o.bound_box]
mn = Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
mx = Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
target = (mn + mx) / 2.0
cam_data = bpy.data.cameras.new("Cam"); cam_data.lens = 80; cam_data.sensor_fit = 'HORIZONTAL'
th = math.tan(math.atan((cam_data.sensor_width/2)/cam_data.lens))
tv = th  # square render
cam = bpy.data.objects.new("Cam", cam_data); bpy.context.collection.objects.link(cam); sc.camera = cam
az, el = math.radians(-35), math.radians(40)
vdir = Vector((math.cos(el)*math.sin(az), -math.cos(el)*math.cos(az), math.sin(el)))
MARGIN = 1.18
def ratio(r):
    cam.location = target + vdir * r
    cam.rotation_euler = (target - cam.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted(); worst = 0.0
    for c in corners:
        q = inv @ c
        if q.z >= -1e-4: return 1e9
        worst = max(worst, abs(q.x)/(th*-q.z), abs(q.y)/(tv*-q.z))
    return worst
lo, hi = max(mx - mn)*0.5, max(mx - mn)*8.0
for _ in range(40):
    m = (lo + hi)/2
    if ratio(m) * MARGIN <= 1.0: hi = m
    else: lo = m
ratio(hi)

# render
sc.render.engine = 'CYCLES'
try:
    sc.cycles.device = 'GPU'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for ct in ('METAL', 'CUDA', 'OPTIX'):
        try: prefs.compute_device_type = ct; break
        except Exception: continue
    prefs.get_devices()
    for d in prefs.devices: d.use = True
except Exception as e:
    print("GPU skip:", e)
sc.cycles.samples = SAMPLES
sc.render.filepath = OUT
sc.render.image_settings.file_format = 'PNG'
sc.view_settings.view_transform = 'Standard'
bpy.ops.render.render(write_still=True)
print("SAVED:", OUT)
