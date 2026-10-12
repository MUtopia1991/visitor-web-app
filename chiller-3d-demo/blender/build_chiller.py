"""
Air-Cooled Screw Chiller - parametric Blender build script
===========================================================

Builds a presentation-grade, part-separated model of a 14-fan air-cooled
screw chiller (V-coil layout, York YVAA-style) and exports it as GLB.

Every major component is its own named node in the glTF scene graph, so a
web viewer (three.js, Babylon, <model-viewer>) can pick, highlight, hide,
isolate or explode it. Each part node also carries glTF "extras" metadata
(part_id, display_name, category, description, explode vector).

Run (Blender >= 4.2 / 5.x):
    blender -b -P build_chiller.py -- [--out <dir>] [--render]
or with the bpy Python module:
    python build_chiller.py -- [--out <dir>] [--render]

Units: meters. Blender Z-up; the GLB is exported Y-up (glTF standard).
"""

import math
import os
import sys

import bpy  # noqa: E402  (must precede bmesh when run as a Python module)
import bmesh
import numpy as np
from mathutils import Euler, Matrix, Vector

# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = (os.path.abspath(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS
       else os.path.normpath(os.path.join(HERE, "..")))
DO_RENDER = "--render" in ARGS or "--quick" in ARGS
QUICK = "--quick" in ARGS
TEX_DIR = os.path.join(HERE, "textures")
GLB_NAME = "chiller_aircooled_screw.glb"

# --------------------------------------------------------------------------
# PARAMETERS (meters) - change these to match the client's submittal drawing
# --------------------------------------------------------------------------
N_BAYS = 7                 # fan bays along the length (2 fans per bay)
BAY = 1.16                 # bay pitch
L = N_BAYS * BAY           # overall length  (8.12 m = 319.7 in)
W = 2.242                  # overall width   (2.242 m = 88.3 in)
HW = W / 2
X0 = -L / 2                # control-panel end
X1 = L / 2                 # water-connection end

RAIL_H = 0.25              # base rail (C-channel) height
RAIL_W = 0.08
POST = 0.08                # square-tube post size
PY = HW - POST / 2         # post / rail centreline (y)
DECK_TOP = 2.35            # top of fan deck
DECK_T = 0.012
MID_RAIL_Z = 1.20
V_BOT = 1.24               # bottom of the V-coils
COIL_T = 0.045             # microchannel slab thickness
SHROUD_R = 0.412           # venturi inner radius (fan dia ~ 0.79 m / 31 in)
FAN_Y = W / 4
BAY_X = [X0 + i * BAY for i in range(N_BAYS + 1)]
BAY_C = [X0 + (i + 0.5) * BAY for i in range(N_BAYS)]

PANEL_X = (X0 + 0.02, X0 + 0.66)   # control panel enclosure, x-range
PANEL_Z = (0.29, 1.17)
PANEL_HY = 0.96

COMP_Y = 0.55              # compressor centreline |y|
COMP_Z = 0.57              # compressor axis height
COMP_X0 = -3.18            # motor end of compressor
SEP_X, SEP_Y = -1.74, 0.83 # oil separators
EVAP_Z, EVAP_R = 0.63, 0.32
EVAP_X = (-1.35, 3.40)

FPS = 24
FAN_FRAMES = 48            # frames per fan revolution in the demo animation


def to_gltf(v):
    """Blender Z-up vector -> glTF Y-up vector."""
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


# --------------------------------------------------------------------------
# Scene reset
# --------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
SCENE = bpy.context.scene
SCENE.name = "Chiller"
SCENE.unit_settings.system = "METRIC"
SCENE.render.fps = FPS
SCENE.frame_start = 0
SCENE.frame_end = FAN_FRAMES
COLL = SCENE.collection


# --------------------------------------------------------------------------
# Textures (generated procedurally so the build is fully reproducible)
# --------------------------------------------------------------------------
def _font(size, bold=False, mono=False):
    from PIL import ImageFont
    base = "/usr/share/fonts/truetype/dejavu/"
    name = ("DejaVuSansMono" if mono else "DejaVuSans") + ("-Bold" if bold else "") + ".ttf"
    try:
        return ImageFont.truetype(base + name, size)
    except OSError:
        return ImageFont.load_default(size=size)


def make_textures():
    from PIL import Image, ImageDraw
    os.makedirs(TEX_DIR, exist_ok=True)

    # Microchannel coil: horizontal flat tubes + fine louvered fins.
    S = 512
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    pitch = S / 20.0                          # 20 tubes per tile (tile = 0.20 m)
    tv = (yy % pitch) / pitch
    tube = tv < 0.22
    fin = (xx % 4) < 2
    louver = ((xx + yy * 0.6) % 9) < 1.5
    h = np.where(tube, 1.0, np.where(fin, 0.62, 0.18))
    h = np.where(~tube & louver, h * 0.8, h)
    col_tube = np.array([196, 200, 204])
    col_fin = np.array([168, 173, 178])
    col_gap = np.array([62, 66, 70])
    base = np.where(tube[..., None], col_tube,
                    np.where(fin[..., None], col_fin, col_gap)).astype(np.float32)
    noise = np.random.default_rng(7).normal(0, 4, (S, S, 1))
    base = np.clip(base + noise, 0, 255).astype(np.uint8)
    Image.fromarray(base, "RGB").save(os.path.join(TEX_DIR, "coil_basecolor.png"))
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 2.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 2.5
    n = np.dstack([-dx, dy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(
        os.path.join(TEX_DIR, "coil_normal.png"))

    # Controller HMI screen (US units).
    img = Image.new("RGB", (640, 400), (8, 18, 32))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 640, 52], fill=(0, 84, 150))
    d.text((18, 12), "CHILLER CONTROL CENTER", font=_font(26, bold=True), fill=(255, 255, 255))
    d.text((470, 16), "UNIT 1", font=_font(20, mono=True), fill=(200, 230, 255))
    rows = [("UNIT STATUS", "RUNNING", (90, 230, 120)),
            ("LEAVING CHW", "44.0 °F", (235, 245, 255)),
            ("ENTERING CHW", "54.0 °F", (235, 245, 255)),
            ("OUTDOOR AIR", "95.0 °F", (235, 245, 255)),
            ("CAPACITY", "78 %", (255, 200, 80)),
            ("SYS 1 / SYS 2", "RUN / RUN", (90, 230, 120))]
    f = _font(24, mono=True)
    for i, (k, v, c) in enumerate(rows):
        y = 72 + i * 46
        d.text((24, y), k, font=f, fill=(150, 180, 210))
        d.text((380, y), v, font=_font(24, bold=True, mono=True), fill=c)
        d.line([(24, y + 38), (616, y + 38)], fill=(30, 50, 75), width=1)
    for i, t in enumerate(["HOME", "SYSTEM", "SETPTS", "ALARMS"]):
        x = 10 + i * 157
        d.rectangle([x, 356, x + 148, 394], fill=(20, 45, 75), outline=(60, 110, 160))
        d.text((x + 30, 364), t, font=_font(18, bold=True), fill=(220, 235, 255))
    img.save(os.path.join(TEX_DIR, "hmi_display.png"))

    # Unit nameplate.
    img = Image.new("RGB", (512, 256), (198, 201, 204))
    d = ImageDraw.Draw(img)
    for yline in range(0, 256, 3):
        d.line([(0, yline), (512, yline)], fill=(188, 191, 195))
    d.rectangle([4, 4, 507, 251], outline=(40, 40, 40), width=3)
    d.text((16, 12), "AIR-COOLED SCREW CHILLER", font=_font(28, bold=True), fill=(15, 15, 15))
    lines = ["MODEL:        ACS-14F (DEMO)", "SERIAL NO.:   DEMO-0001",
             "REFRIGERANT:  R-513A  (2 CIRCUITS)", "POWER:        460 V / 3 PH / 60 HZ",
             "MCA:  ---  A        MOP:  ---  A"]
    for i, t in enumerate(lines):
        d.text((16, 62 + i * 36), t, font=_font(20, mono=True), fill=(20, 20, 20))
    img.save(os.path.join(TEX_DIR, "nameplate.png"))

    # ANSI-style safety label.
    img = Image.new("RGB", (512, 280), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 512, 80], fill=(255, 140, 0))
    d.text((150, 14), "WARNING", font=_font(46, bold=True), fill=(0, 0, 0))
    d.polygon([(40, 68), (80, 8), (120, 68)], fill=(0, 0, 0))
    d.polygon([(52, 61), (80, 20), (108, 61)], fill=(255, 140, 0))
    d.text((74, 30), "!", font=_font(30, bold=True), fill=(0, 0, 0))
    for i, t in enumerate(["HAZARDOUS VOLTAGE", "Disconnect all power", "before servicing."]):
        d.text((24, 100 + i * 56), t, font=_font(38 if i == 0 else 34, bold=(i == 0)), fill=(0, 0, 0))
    img.save(os.path.join(TEX_DIR, "label_warning.png"))


def load_image(name, non_color=False):
    img = bpy.data.images.load(os.path.join(TEX_DIR, name), check_existing=True)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


# --------------------------------------------------------------------------
# Materials (PBR, glTF-compatible Principled BSDF)
# --------------------------------------------------------------------------
def srgb(hexstr):
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


MAT = {}


def mat(key, hexcol, metal=0.0, rough=0.5, emit=0.0, tex=None, normal=None, name=None):
    m = bpy.data.materials.new(name or key)
    try:
        m.use_nodes = True
    except AttributeError:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    col = srgb(hexstr=hexcol) if hexcol else (1, 1, 1)
    bsdf.inputs["Base Color"].default_value = (*col, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    m.diffuse_color = (*col, 1)
    if tex:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = load_image(tex)
        nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
        if emit:
            nt.links.new(tn.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emit
    if normal:
        nn = nt.nodes.new("ShaderNodeTexImage")
        nn.image = load_image(normal, non_color=True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.8
        nt.links.new(nn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    MAT[key] = m
    return m


def make_materials():
    mat("frame", "#4a5056", 0.35, 0.48, name="Frame_PowderCoat_Charcoal")
    mat("casing", "#d6d7d3", 0.05, 0.42, name="Casing_Paint_LightGray")
    mat("panel", "#dcddd9", 0.05, 0.38, name="Panel_Paint_RAL7035")
    mat("gasket", "#151617", 0.0, 0.8, name="Rubber_Black")
    mat("coil", None, 0.75, 0.38, tex="coil_basecolor.png", normal="coil_normal.png",
        name="Coil_Microchannel_Aluminum")
    mat("header", "#a9afb4", 0.85, 0.3, name="Coil_Header_Aluminum")
    mat("guard", "#18191b", 0.4, 0.45, name="Fan_Guard_Black")
    mat("shroud", "#2a2d31", 0.1, 0.55, name="Fan_Venturi_Composite")
    mat("blade", "#3d4146", 0.2, 0.4, name="Fan_Blade_Composite")
    mat("motor", "#2b3036", 0.5, 0.45, name="Fan_Motor")
    mat("comp", "#1f4e8c", 0.35, 0.38, name="Compressor_Paint_Blue")
    mat("steel", "#7a8086", 0.7, 0.4, name="Steel_Machined")
    mat("vessel", "#8a9096", 0.45, 0.42, name="Vessel_Paint_Gray")
    mat("insul", "#121314", 0.0, 0.88, name="Insulation_Elastomeric_Black")
    mat("waterbox", "#2f3439", 0.4, 0.45, name="WaterBox_Paint_Dark")
    mat("galv", "#a3a8ad", 0.85, 0.32, name="Galvanized_Steel")
    mat("copper", "#b87333", 1.0, 0.32, name="Copper")
    mat("brass", "#b59a42", 1.0, 0.35, name="Brass")
    mat("red", "#c8102e", 0.0, 0.4, name="Paint_Safety_Red")
    mat("yellow", "#f2c200", 0.0, 0.45, name="Paint_Safety_Yellow")
    mat("blue_tag", "#1565c0", 0.0, 0.45, name="Tag_Blue")
    mat("green_tag", "#2e7d32", 0.0, 0.45, name="Tag_Green")
    mat("key", "#2b2e33", 0.0, 0.55, name="Keypad_Key")
    mat("screen", None, 0.0, 0.2, emit=1.2, tex="hmi_display.png", name="HMI_Display")
    mat("nameplate", None, 0.8, 0.35, tex="nameplate.png", name="Nameplate_Aluminum")
    mat("label", None, 0.0, 0.5, tex="label_warning.png", name="Label_Warning")


# --------------------------------------------------------------------------
# Geometry primitives (bmesh)
# --------------------------------------------------------------------------
def Mx(loc=(0, 0, 0), rot=(0, 0, 0)):
    return Matrix.Translation(Vector(loc)) @ Euler(rot).to_matrix().to_4x4()


def axisM(start, axis):
    """Matrix mapping local +Z (lathe axis) onto a world axis at `start`."""
    rot = {"x": (0, math.pi / 2, 0), "-x": (0, -math.pi / 2, 0),
           "y": (-math.pi / 2, 0, 0), "-y": (math.pi / 2, 0, 0),
           "z": (0, 0, 0), "-z": (math.pi, 0, 0)}[axis]
    return Mx(start, rot)


def xf(b, M):
    bmesh.ops.transform(b, matrix=M, verts=b.verts)
    return b


def finish(b):
    bmesh.ops.remove_doubles(b, verts=b.verts, dist=1e-6)
    bmesh.ops.dissolve_degenerate(b, edges=b.edges, dist=1e-7)
    bmesh.ops.recalc_face_normals(b, faces=b.faces)
    return b


def bm_box(size, bevel=0.0, seg=3):
    b = bmesh.new()
    bmesh.ops.create_cube(b, size=1.0)
    bmesh.ops.scale(b, vec=Vector(size), verts=b.verts)
    if bevel > 0:
        bmesh.ops.bevel(b, geom=list(b.edges), offset=bevel, offset_type="OFFSET",
                        segments=seg, profile=0.5, affect="EDGES", clamp_overlap=True)
    return b


def bm_lathe(profile, seg=48, closed=False):
    """Revolve a (r, z) profile around local Z."""
    b = bmesh.new()
    rings = []
    for i in range(seg):
        a = 2 * math.pi * i / seg
        ca, sa = math.cos(a), math.sin(a)
        rings.append([b.verts.new((r * ca, r * sa, z)) for r, z in profile])
    n = len(profile)
    for i in range(seg):
        A, B = rings[i], rings[(i + 1) % seg]
        for j in range(n if closed else n - 1):
            j2 = (j + 1) % n
            b.faces.new([A[j], B[j], B[j2], A[j2]])
    return finish(b)


def bm_cyl(r, h, seg=32):
    return bm_lathe([(0, 0), (r, 0), (r, h), (0, h)], seg)


def bm_torus(R, r, seg=48, sides=8):
    prof = [(R + r * math.cos(2 * math.pi * k / sides), r * math.sin(2 * math.pi * k / sides))
            for k in range(sides)]
    return bm_lathe(prof, seg, closed=True)


def fillet(pts, rad, seg=7):
    pts = [Vector(p) for p in pts]
    out = [pts[0]]
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[i - 1], pts[i], pts[i + 1]
        d1, d2 = (p1 - p0).normalized(), (p2 - p1).normalized()
        ang = d1.angle(d2)
        if ang < 1e-3:
            out.append(p1)
            continue
        t = min(rad * math.tan(ang / 2), (p1 - p0).length * 0.49, (p2 - p1).length * 0.49)
        a, c = p1 - d1 * t, p1 + d2 * t
        for k in range(seg + 1):
            s = k / seg
            out.append((1 - s) ** 2 * a + 2 * (1 - s) * s * p1 + s * s * c)
    out.append(pts[-1])
    return out


def bm_sweep(pts, r, sides=16, caps=True, bend=None):
    """Tube along a polyline (filleted corners, parallel-transport frames)."""
    pts = fillet(pts, bend if bend is not None else r * 2.2)
    n = len(pts)
    tang = []
    for i in range(n):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == n - 1:
            t = pts[-1] - pts[-2]
        else:
            t = (pts[i + 1] - pts[i]).normalized() + (pts[i] - pts[i - 1]).normalized()
        tang.append(t.normalized())
    up = Vector((0, 0, 1)) if abs(tang[0].z) < 0.9 else Vector((1, 0, 0))
    N = tang[0].cross(up).normalized()
    b = bmesh.new()
    rings = []
    for i in range(n):
        t = tang[i]
        N = (N - t * N.dot(t)).normalized()
        B = t.cross(N)
        rings.append([b.verts.new(pts[i] + r * (math.cos(a) * N + math.sin(a) * B))
                      for a in (2 * math.pi * k / sides for k in range(sides))])
    for i in range(n - 1):
        for k in range(sides):
            k2 = (k + 1) % sides
            b.faces.new([rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]])
    if caps:
        b.faces.new(rings[0][::-1])
        b.faces.new(rings[-1])
    return finish(b)


def bm_prism(poly, axis, a0, a1):
    """Extrude a 2D polygon along a world axis between a0 and a1."""
    def P(u, v, a):
        return {"x": (a, u, v), "y": (u, a, v), "z": (u, v, a)}[axis]
    b = bmesh.new()
    lo = [b.verts.new(P(u, v, a0)) for u, v in poly]
    hi = [b.verts.new(P(u, v, a1)) for u, v in poly]
    b.faces.new(lo)
    b.faces.new(hi[::-1])
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        b.faces.new([lo[i], lo[j], hi[j], hi[i]])
    return finish(b)


def bm_boolean_diff(base, cutter):
    """EXACT boolean difference of two bmeshes (via a temporary modifier)."""
    meA, meB = bpy.data.meshes.new("_A"), bpy.data.meshes.new("_B")
    base.to_mesh(meA)
    cutter.to_mesh(meB)
    base.free()
    cutter.free()
    oA, oB = bpy.data.objects.new("_A", meA), bpy.data.objects.new("_B", meB)
    COLL.objects.link(oA)
    COLL.objects.link(oB)
    mod = oA.modifiers.new("bool", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.object = oB
    try:
        mod.solver = "EXACT"
    except TypeError:
        pass
    dg = bpy.context.evaluated_depsgraph_get()
    meC = bpy.data.meshes.new_from_object(oA.evaluated_get(dg))
    b = bmesh.new()
    b.from_mesh(meC)
    for o in (oA, oB):
        bpy.data.objects.remove(o)
    for m in (meA, meB, meC):
        bpy.data.meshes.remove(m)
    return finish(b)


def boxuv(co, n, s=1.0):
    a = max(range(3), key=lambda i: abs(n[i]))
    i, j = [(1, 2), (0, 2), (0, 1)][a]
    return (co[i] / s, co[j] / s)


# --------------------------------------------------------------------------
# Part builder: accumulates geometry + material slots into one mesh object
# --------------------------------------------------------------------------
class Part:
    def __init__(self, name, display=None):
        self.name = name
        self.display = display or name.replace("_", " ")
        self.bm = bmesh.new()
        self.uv = self.bm.loops.layers.uv.new("UVMap")
        self.mats = []

    def _mi(self, key):
        if key not in self.mats:
            self.mats.append(key)
        return self.mats.index(key)

    def merge(self, tmp, m):
        mi = self._mi(m)
        tmp.normal_update()
        tuv = tmp.loops.layers.uv.active
        vmap = {v: self.bm.verts.new(v.co) for v in tmp.verts}
        for f in tmp.faces:
            try:
                nf = self.bm.faces.new([vmap[v] for v in f.verts])
            except ValueError:
                continue
            nf.material_index = mi
            for ln, lo in zip(nf.loops, f.loops):
                ln[self.uv].uv = lo[tuv].uv if tuv else boxuv(lo.vert.co, f.normal)
        tmp.free()
        return self

    # convenience wrappers -------------------------------------------------
    def box(self, size, center, m, rot=(0, 0, 0), bevel=0.0):
        return self.merge(xf(bm_box(size, bevel), Mx(center, rot)), m)

    def box_minmax(self, lo, hi, m, bevel=0.0):
        size = [h - l for l, h in zip(lo, hi)]
        c = [(l + h) / 2 for l, h in zip(lo, hi)]
        return self.box(size, c, m, bevel=bevel)

    def cyl(self, r, h, start, axis, m, seg=32):
        return self.merge(xf(bm_cyl(r, h, seg), axisM(start, axis)), m)

    def lathe(self, profile, start, axis, m, seg=48, closed=False):
        return self.merge(xf(bm_lathe(profile, seg, closed), axisM(start, axis)), m)

    def torus(self, R, r, start, axis, m, seg=48, sides=8):
        return self.merge(xf(bm_torus(R, r, seg, sides), axisM(start, axis)), m)

    def pipe(self, pts, r, m, sides=16, bend=None, caps=True):
        return self.merge(bm_sweep(pts, r, sides, caps, bend), m)

    def prism(self, poly, axis, a0, a1, m):
        return self.merge(bm_prism(poly, axis, a0, a1), m)

    def quad(self, corners, m):
        """Single textured quad, UV (0,0)-(1,1) in corner order BL, BR, TR, TL."""
        b = bmesh.new()
        uvl = b.loops.layers.uv.new("UVMap")
        f = b.faces.new([b.verts.new(c) for c in corners])
        for l, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            l[uvl].uv = uv
        return self.merge(b, m)

    # ---------------------------------------------------------------------
    def build(self, origin="bbox", sharp_deg=35):
        if origin == "bbox":
            vs = [v.co for v in self.bm.verts]
            lo = Vector([min(v[i] for v in vs) for i in range(3)])
            hi = Vector([max(v[i] for v in vs) for i in range(3)])
            c = (lo + hi) / 2
        else:
            c = Vector(origin)
        bmesh.ops.translate(self.bm, vec=-c, verts=self.bm.verts)
        me = bpy.data.meshes.new(self.name)
        self.bm.to_mesh(me)
        self.bm.free()
        for k in self.mats:
            me.materials.append(MAT[k])
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp_deg))
        me.validate()
        ob = bpy.data.objects.new(self.name, me)
        COLL.objects.link(ob)
        ob.location = c
        ob["display_name"] = self.display
        return ob


# --------------------------------------------------------------------------
# Scene-graph helpers
# --------------------------------------------------------------------------
def world_bbox(objs):
    bpy.context.view_layer.update()
    pts = []

    def walk(o):
        if o.type == "MESH":
            pts.extend(o.matrix_world @ v.co for v in o.data.vertices)
        for ch in o.children:
            walk(ch)
    for o in objs:
        walk(o)
    lo = Vector([min(p[i] for p in pts) for i in range(3)])
    hi = Vector([max(p[i] for p in pts) for i in range(3)])
    return lo, hi


def group(name, children, at=None, **props):
    """Create an Empty node and re-parent `children` under it (world-preserving)."""
    bpy.context.view_layer.update()
    if at is None:
        lo, hi = world_bbox(children)
        at = (lo + hi) / 2
    e = bpy.data.objects.new(name, None)
    e.empty_display_type = "PLAIN_AXES"
    e.empty_display_size = 0.25
    COLL.objects.link(e)
    e.location = Vector(at)
    for ch in children:
        wl = ch.matrix_world.translation.copy()
        ch.parent = e
        ch.matrix_parent_inverse = Matrix.Identity(4)
        ch.location = wl - Vector(at)
    for k, v in props.items():
        e[k] = v
    return e


PART_INFO = {}


def part(pid, key, display, category, description, children, explode=(0, 0, 0)):
    name = f"{pid}_{key}"
    e = group(name, children, part_id=pid, display_name=display, category=category,
              description=description, explode=to_gltf(explode))
    e["explode_blender"] = list(explode)
    PART_INFO[name] = dict(id=pid, display=display, category=category,
                           children=[c.name for c in children])
    return e


# ==========================================================================
# P01  BASE FRAME (structural steel)
# ==========================================================================
def build_base_frame():
    p = Part("Base_Frame_Structure", "Base frame & posts")
    # Base rails: C-channel, web on the outside, flanges pointing inward.
    t_web, t_fl = 0.008, 0.012
    for s in (-1, 1):
        yo = s * HW
        yi = s * (HW - RAIL_W)
        yw = s * (HW - t_web)
        poly = [(yo, 0), (yi, 0), (yi, t_fl), (yw, t_fl), (yw, RAIL_H - t_fl),
                (yi, RAIL_H - t_fl), (yi, RAIL_H), (yo, RAIL_H)]
        if s < 0:
            poly = poly[::-1]
        rail = bm_prism(poly, "x", X0, X1)
        cut = bmesh.new()
        for x in (X0 + 0.45, -1.16, 1.16, X1 - 0.45):     # rigging / lifting holes
            hole = xf(bm_cyl(0.035, 0.1, 24), axisM((x, s * HW - 0.05 * s, 0.15), "y"))
            cut_me = bpy.data.meshes.new("_h")
            hole.to_mesh(cut_me)
            hole.free()
            cut.from_mesh(cut_me)
            bpy.data.meshes.remove(cut_me)
        p.merge(bm_boolean_diff(rail, cut), "frame")
    # Cross members (bay lines + equipment supports).
    xs = sorted(set([round(x, 3) for x in BAY_X] + [-3.55, -2.40]))
    for x in xs:
        x = min(max(x, X0 + 0.04), X1 - 0.04)
        p.box((0.08, W - 2 * RAIL_W, 0.12), (x, 0, RAIL_H - 0.06), "frame")
    # Posts at every bay line, both sides.
    for x in BAY_X:
        x = min(max(x, X0 + POST / 2), X1 - POST / 2)
        for s in (-1, 1):
            p.box_minmax((x - POST / 2, s * PY - POST / 2, RAIL_H),
                         (x + POST / 2, s * PY + POST / 2, DECK_TOP - DECK_T), "frame")
    # Longitudinal rails: mid (coil support) and top (deck support).
    for s in (-1, 1):
        p.box((L, 0.06, 0.06), (0, s * PY, MID_RAIL_Z), "frame")
        p.box((L, POST, 0.09), (0, s * PY, DECK_TOP - DECK_T - 0.045), "frame")
    # End frames: cross rails at mid and top height.
    for x in (X0 + POST / 2, X1 - POST / 2):
        p.box((POST, W - 2 * POST, 0.06), (x, 0, MID_RAIL_Z), "frame")
        p.box((POST, W - 2 * POST, 0.09), (x, 0, DECK_TOP - DECK_T - 0.045), "frame")
    # Corner gussets on the end frames.
    for x in (X0 + 0.004, X1 - 0.004):
        for s in (-1, 1):
            tri = [(s * (HW - POST), RAIL_H), (s * (HW - POST - 0.22), RAIL_H),
                   (s * (HW - POST), RAIL_H + 0.22)]
            if s > 0:
                tri = tri[::-1]
            p.prism(tri, "x", x - 0.004, x + 0.004, "frame")
    return [p.build()]


# ==========================================================================
# P02  CONTROL / POWER PANEL
# ==========================================================================
def build_control_panel():
    xa, xb = PANEL_X
    za, zb = PANEL_Z
    face = xa                      # front (door) plane faces -X
    objs = []

    enc = Part("Panel_Enclosure", "Panel enclosure")
    enc.box_minmax((xa, -PANEL_HY, za), (xb, PANEL_HY, zb), "panel", bevel=0.012)
    enc.box_minmax((X0 - 0.07, -PANEL_HY - 0.02, zb), (xb + 0.01, PANEL_HY + 0.02, zb + 0.016),
                   "panel", bevel=0.004)                               # rain hood
    enc.box_minmax((X0 - 0.07, -PANEL_HY - 0.02, zb - 0.035), (X0 - 0.062, PANEL_HY + 0.02, zb),
                   "panel")                                            # drip edge
    for y in (-0.7, 0.7):                                              # mounting channels
        enc.box_minmax((xa + 0.02, y - 0.04, RAIL_H), (xb - 0.02, y + 0.04, za), "frame")
    for s in (-1, 1):                                                  # side louvers
        for k in range(5):
            z = 0.45 + k * 0.05
            enc.box((0.30, 0.02, 0.006), ((xa + xb) / 2, s * (PANEL_HY + 0.006), z),
                    "panel", rot=(s * math.radians(35), 0, 0))
    objs.append(enc.build())

    door_w, gap = (2 * PANEL_HY - 4 * 0.01) / 3, 0.01
    centers = [PANEL_HY - 0.01 - door_w / 2 - i * (door_w + gap) for i in range(3)]
    dz = (za + 0.02, zb - 0.02)
    names = [("Panel_Door_1_Controls", "Door 1 - controls / HMI"),
             ("Panel_Door_2_Disconnect", "Door 2 - main disconnect"),
             ("Panel_Door_3_Power", "Door 3 - power / VSD section")]
    for i, yc in enumerate(centers):
        d = Part(*names[i])
        d.box_minmax((face - 0.022, yc - door_w / 2, dz[0]), (face, yc + door_w / 2, dz[1]),
                     "panel", bevel=0.006)
        d.box_minmax((face - 0.002, yc - door_w / 2 - 0.004, dz[0] - 0.004),
                     (face + 0.001, yc + door_w / 2 + 0.004, dz[1] + 0.004), "gasket")
        # hinges (left edge as seen from the front = +y side)
        for z in (dz[0] + 0.12, dz[1] - 0.12):
            d.cyl(0.011, 0.07, (face - 0.012, yc + door_w / 2 + 0.006, z - 0.035), "z", "steel", 16)
        # quarter-turn latches (right edge)
        for z in (dz[0] + 0.18, dz[1] - 0.18):
            d.cyl(0.016, 0.014, (face - 0.022, yc - door_w / 2 + 0.05, z), "-x", "steel", 20)
            d.box((0.012, 0.012, 0.045), (face - 0.042, yc - door_w / 2 + 0.05, z), "gasket")
        if i == 0:   # HMI: bezel, screen, keypad
            zc = 0.90
            d.box((0.016, 0.34, 0.26), (face - 0.030, yc, zc), "key", bevel=0.006)
            d.quad([(face - 0.0385, yc + 0.145, zc - 0.088), (face - 0.0385, yc - 0.145, zc - 0.088),
                    (face - 0.0385, yc - 0.145, zc + 0.093), (face - 0.0385, yc + 0.145, zc + 0.093)],
                   "screen")
            d.box((0.012, 0.25, 0.14), (face - 0.028, yc, 0.68), "key", bevel=0.004)
            for r in range(3):
                for c in range(4):
                    d.box((0.008, 0.042, 0.03), (face - 0.037, yc + 0.075 - c * 0.05, 0.72 - r * 0.04),
                          "panel", bevel=0.003)
            d.box((0.01, 0.05, 0.03), (face - 0.037, yc + 0.165, 0.92 - 0.2), "green_tag", bevel=0.003)
            d.box((0.01, 0.05, 0.03), (face - 0.037, yc + 0.165, 0.68 - 0.04), "red", bevel=0.003)
        if i == 1:   # main non-fused disconnect (lockable rotary handle)
            zc = 0.80
            d.box((0.010, 0.15, 0.15), (face - 0.027, yc, zc), "yellow", bevel=0.004)
            d.cyl(0.035, 0.03, (face - 0.032, yc, zc), "-x", "red", 32)
            d.box((0.03, 0.045, 0.19), (face - 0.065, yc, zc - 0.02), "red", bevel=0.008)
            d.quad([(face - 0.0225, yc + 0.11, 1.02), (face - 0.0225, yc - 0.11, 1.02),
                    (face - 0.0225, yc - 0.11, 1.14 - 0.0), (face - 0.0225, yc + 0.11, 1.14)], "label")
        if i == 2:   # nameplate + ventilation louvers
            d.quad([(face - 0.0225, yc + 0.15, 0.93), (face - 0.0225, yc - 0.15, 0.93),
                    (face - 0.0225, yc - 0.15, 1.08), (face - 0.0225, yc + 0.15, 1.08)], "nameplate")
            d.box_minmax((face - 0.03, yc - 0.21, 0.40), (face - 0.022, yc + 0.21, 0.66), "key")
            for k in range(7):
                d.box((0.028, 0.40, 0.006), (face - 0.034, yc, 0.42 + k * 0.034), "panel",
                      rot=(0, math.radians(40), 0))
        objs.append(d.build())

    # Power conduits from the panel to each compressor terminal box.
    c = Part("Power_Conduits", "Power conduits to compressors")
    for s in (-1, 1):
        y = s * (COMP_Y + 0.27)
        c.pipe([(xb, y, COMP_Z + 0.05), (COMP_X0 + 0.21, y, COMP_Z + 0.05)], 0.022, "gasket", 14)
        c.cyl(0.03, 0.025, (xb, y, COMP_Z + 0.05), "x", "steel", 16)
    objs.append(c.build())
    return objs


# ==========================================================================
# P03  CONDENSER COILS (microchannel, V-arrangement)
# ==========================================================================
def coil_slab(p, top, bot, y_half):
    """Slab from `top` (x,z) to `bot` (x,z) spanning +-y_half, UV-mapped to the coil tile."""
    T, B = Vector((top[0], 0, top[1])), Vector((bot[0], 0, bot[1]))
    d = (B - T)
    Ls = d.length
    d.normalize()
    n = Vector((-d.z, 0, d.x)) if d.x > 0 else Vector((d.z, 0, -d.x))
    if n.z < 0:
        n = -n
    b = bm_box((2 * y_half, Ls, COIL_T))
    uvl = b.loops.layers.uv.new("UVMap")
    b.normal_update()
    for f in b.faces:
        for l in f.loops:
            l[uvl].uv = boxuv(l.vert.co + Vector((y_half, Ls / 2, 0)), f.normal, 0.20)
    M = Matrix(((0, d.x, n.x), (1, 0, 0), (0, d.z, n.z))).to_4x4()
    M.translation = (T + B) / 2 + n * (COIL_T / 2)
    xf(b, M)
    if M.to_3x3().determinant() < 0:
        bmesh.ops.reverse_faces(b, faces=b.faces)
    p.merge(b, "coil")
    for s in (-1, 1):   # inlet / outlet headers at both tube ends
        p.pipe([T + n * 0.022 + Vector((0, s * (y_half + 0.018), 0)),
                B + n * 0.022 + Vector((0, s * (y_half + 0.018), 0))], 0.02, "header", 14)


def build_coils():
    objs = []
    y_half = HW - POST - 0.025
    for i in range(N_BAYS):
        xa, xb, xc = BAY_X[i], BAY_X[i + 1], BAY_C[i]
        p = Part(f"Coil_Bay_{i + 1:02d}", f"Condenser coil pair - bay {i + 1}")
        coil_slab(p, (xa + 0.06, DECK_TOP - DECK_T - 0.02), (xc - 0.035, V_BOT + 0.03), y_half)
        coil_slab(p, (xb - 0.06, DECK_TOP - DECK_T - 0.02), (xc + 0.035, V_BOT + 0.03), y_half)
        objs.append(p.build())
    return objs


# ==========================================================================
# P04  CASING & FAN DECK (sheet metal)
# ==========================================================================
def build_casing():
    objs = []
    deck = Part("Fan_Deck", "Fan deck (top panels)")
    plate = bm_box((L, W, DECK_T))
    xf(plate, Mx((0, 0, DECK_TOP - DECK_T / 2)))
    cut = bmesh.new()
    for xc in BAY_C:
        for s in (-1, 1):
            c = xf(bm_cyl(0.43, 0.1, 64), Mx((xc, s * FAN_Y, DECK_TOP - 0.05)))
            me = bpy.data.meshes.new("_c")
            c.to_mesh(me)
            c.free()
            cut.from_mesh(me)
            bpy.data.meshes.remove(me)
    deck.merge(bm_boolean_diff(plate, cut), "casing")
    for x in BAY_X[1:-1]:                                    # standing seams between bays
        deck.box((0.03, W - 0.02, 0.018), (x, 0, DECK_TOP + 0.009), "casing", bevel=0.004)
    deck.box((L - 0.02, 0.03, 0.018), (0, 0, DECK_TOP + 0.009), "casing", bevel=0.004)
    for s in (-1, 1):                                        # perimeter trim
        deck.box((L, 0.012, 0.06), (0, s * (HW - 0.006), DECK_TOP - 0.03), "casing")
    for x in (X0 + 0.006, X1 - 0.006):
        deck.box((0.012, W, 0.06), (x, 0, DECK_TOP - 0.03), "casing")
    objs.append(deck.build())

    vp = Part("V_End_Panels", "V-coil end panels & drain channels")
    for i in range(N_BAYS):
        xa, xb, xc = BAY_X[i] + 0.045, BAY_X[i + 1] - 0.045, BAY_C[i]
        tri = [(xa, DECK_TOP - DECK_T), (xc, V_BOT), (xb, DECK_TOP - DECK_T)]
        for s in (-1, 1):
            y = s * (HW - 0.02)
            vp.prism(tri, "y", y - 0.003, y + 0.003, "casing")
            # stiffening flange along the sloped edges
            for (ax, az), (bx, bz) in ((tri[0], tri[1]), (tri[1], tri[2])):
                vp.pipe([(ax, y - s * 0.01, az), (bx, y - s * 0.01, bz)], 0.008, "casing", 8, caps=True)
        vp.box((0.16, W - 2 * POST - 0.02, 0.05), (xc, 0, V_BOT - 0.005), "casing", bevel=0.005)
    objs.append(vp.build())
    return objs


# ==========================================================================
# P05  CONDENSER FANS (14x, animated rotors)
# ==========================================================================
def bm_blade(theta0, z0, rh=0.092, rt=0.392, nr=11, nc=6):
    b = bmesh.new()
    grid = []
    for i in range(nr):
        f = i / (nr - 1)
        r = rh + (rt - rh) * f
        chord = 0.105 + 0.085 * f - 0.07 * f ** 10          # rounded tip
        beta = math.radians(44 - 22 * f)                    # pitch angle
        sweep = 0.42 * f ** 1.7                             # sickle sweep
        row = []
        for j in range(nc):
            c = j / (nc - 1) - 0.5
            th = theta0 - sweep + c * chord * math.cos(beta) / r
            z = z0 - c * chord * math.sin(beta) + 0.012 * math.cos(math.pi * c)
            row.append(b.verts.new((r * math.cos(th), r * math.sin(th), z)))
        grid.append(row)
    for i in range(nr - 1):
        for j in range(nc - 1):
            b.faces.new([grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]])
    bmesh.ops.solidify(b, geom=list(b.faces), thickness=0.004)
    return finish(b)


def build_fan(idx, x, y):
    e = bpy.data.objects.new(f"Fan_{idx:02d}", None)
    e.empty_display_type = "CIRCLE"
    e.empty_display_size = 0.4
    COLL.objects.link(e)
    e.location = (x, y, DECK_TOP)
    e["display_name"] = f"Condenser fan {idx}"

    # Venturi / orifice ring (local z = 0 is the deck top).
    sh = Part(f"Fan_{idx:02d}_Venturi", f"Fan {idx} venturi ring")
    R = SHROUD_R
    prof = [(R + 0.06, -0.215), (R + 0.025, -0.205), (R + 0.006, -0.185), (R, -0.16), (R, 0.004),
            (R + 0.006, 0.013), (R + 0.035, 0.016), (R + 0.035, 0.010), (R + 0.008, 0.006),
            (R + 0.005, 0.0), (R + 0.005, -0.16), (R + 0.011, -0.183), (R + 0.03, -0.199),
            (R + 0.06, -0.208)]
    sh.lathe(prof, (0, 0, 0), "z", "shroud", 64, closed=True)
    sh_ob = sh.build(origin=(0, 0, 0))

    # Rotor: hub + 5 sickle blades (animated about local Z).
    ro = Part(f"Fan_{idx:02d}_Rotor", f"Fan {idx} rotor (5-blade)")
    zb = -0.075
    ro.lathe([(0, zb - 0.05), (0.07, zb - 0.05), (0.092, zb - 0.03), (0.092, zb + 0.02),
              (0.06, zb + 0.045), (0, zb + 0.05)], (0, 0, 0), "z", "motor", 32)
    for k in range(5):
        ro.merge(bm_blade(2 * math.pi * k / 5, zb), "blade")
    ro_ob = ro.build(origin=(0, 0, 0))

    # Motor + support arms.
    mo = Part(f"Fan_{idx:02d}_Motor", f"Fan {idx} motor & mount")
    mo.lathe([(0, -0.33), (0.07, -0.33), (0.088, -0.31), (0.088, -0.16), (0.05, -0.13),
              (0.05, -0.125), (0, -0.125)], (0, 0, 0), "z", "motor", 32)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        p0 = Vector((0.08 * math.cos(a), 0.08 * math.sin(a), -0.21))
        p1 = Vector(((R - 0.004) * math.cos(a), (R - 0.004) * math.sin(a), -0.16))
        mo.pipe([p0, p1], 0.011, "motor", 8)
    mo_ob = mo.build(origin=(0, 0, 0))

    # Wire guard.
    gu = Part(f"Fan_{idx:02d}_Guard", f"Fan {idx} wire guard")
    zg = 0.05
    for r in (0.07, 0.13, 0.19, 0.25, 0.31, 0.37, 0.425):
        gu.torus(r, 0.0032, (0, 0, zg), "z", "guard", 64 if r > 0.2 else 40, 6)
    for k in range(16):
        a = 2 * math.pi * k / 16 + math.pi / 16
        gu.pipe([(0.04 * math.cos(a), 0.04 * math.sin(a), zg + 0.004),
                 (0.43 * math.cos(a), 0.43 * math.sin(a), zg + 0.004)], 0.003, "guard", 6, caps=False)
    gu.cyl(0.05, 0.008, (0, 0, zg - 0.002), "z", "guard", 24)
    for k in range(4):
        a = k * math.pi / 2
        gu.pipe([(0.43 * math.cos(a), 0.43 * math.sin(a), zg),
                 (0.44 * math.cos(a), 0.44 * math.sin(a), 0.016)], 0.005, "guard", 8)
    gu_ob = gu.build(origin=(0, 0, 0))

    for ch in (sh_ob, ro_ob, mo_ob, gu_ob):
        ch.parent = e

    # Demo animation: one revolution per FAN_FRAMES (loops seamlessly).
    phase = (idx * 0.61) % (2 * math.pi)
    ro_ob.rotation_mode = "XYZ"
    for fr in range(0, FAN_FRAMES + 1, 4):
        ro_ob.rotation_euler = (0, 0, phase + 2 * math.pi * fr / FAN_FRAMES)
        ro_ob.keyframe_insert("rotation_euler", index=2, frame=fr)
    act = ro_ob.animation_data.action
    try:
        fcurves = act.fcurves
    except AttributeError:   # Blender 5 layered actions
        fcurves = [fc for layer in act.layers for strip in layer.strips
                   for bag in strip.channelbags for fc in bag.fcurves]
    for fc in fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    # Push to an NLA track: all tracks named "Fans_Spin" export as ONE glTF clip.
    act.name = f"Fan_{idx:02d}_Spin"
    track = ro_ob.animation_data.nla_tracks.new()
    track.name = "Fans_Spin"
    track.strips.new("Fans_Spin", 0, act)
    ro_ob.animation_data.action = None
    return e


def build_fans():
    fans = []
    idx = 1
    for xc in BAY_C:
        for s in (1, -1):
            fans.append(build_fan(idx, xc, s * FAN_Y))
            idx += 1
    return fans


# ==========================================================================
# P06  COMPRESSORS (2x semi-hermetic screw)
# ==========================================================================
def build_compressor(circ, sy):
    y = sy * COMP_Y
    p = Part(f"Compressor_C{circ}", f"Screw compressor - circuit {circ}")
    x0, cz = COMP_X0, COMP_Z
    st = (x0, y, cz)
    # motor housing with end dome + cooling ribs
    p.lathe([(0, 0), (0.12, 0), (0.18, 0.015), (0.205, 0.05), (0.21, 0.08), (0.21, 0.56), (0, 0.56)],
            st, "x", "comp", 48)
    for zz in (0.16, 0.24, 0.32, 0.40, 0.48):
        p.torus(0.212, 0.007, (x0 + zz, y, cz), "x", "comp", 48, 6)
    # rotor housing, discharge housing, bolted flanges
    p.lathe([(0, 0.56), (0.195, 0.56), (0.195, 0.88), (0, 0.88)], st, "x", "comp", 48)
    p.lathe([(0, 0.88), (0.17, 0.88), (0.17, 1.02), (0.12, 1.06), (0, 1.06)], st, "x", "comp", 48)
    for zz in (0.56, 0.88):
        p.cyl(0.228, 0.024, (x0 + zz - 0.012, y, cz), "x", "steel", 48)
        for k in range(12):
            a = 2 * math.pi * k / 12
            p.cyl(0.009, 0.034, (x0 + zz - 0.017, y + 0.215 * math.cos(a), cz + 0.215 * math.sin(a)),
                  "x", "steel", 10)
    # suction flange (motor end, top) and discharge flange (discharge end, top)
    p.cyl(0.07, 0.05, (x0 + 0.10, y, cz + 0.19), "z", "comp", 32)
    p.cyl(0.095, 0.02, (x0 + 0.10, y, cz + 0.235), "z", "steel", 32)
    p.cyl(0.06, 0.04, (x0 + 0.97, y, cz + 0.155), "z", "comp", 32)
    p.cyl(0.08, 0.02, (x0 + 0.97, y, cz + 0.19), "z", "steel", 32)
    # terminal box on the outboard side of the motor
    p.box((0.22, 0.12, 0.20), (x0 + 0.30, y + sy * 0.265, cz + 0.05), "comp", bevel=0.01)
    p.box((0.18, 0.012, 0.16), (x0 + 0.30, y + sy * 0.33, cz + 0.05), "steel", bevel=0.004)
    # oil filter canister on the rotor housing
    p.cyl(0.05, 0.16, (x0 + 0.72, y - sy * 0.25, cz - 0.10), "z", "steel", 24)
    # feet + neoprene isolators on the cross members
    for fx in (-2.90, -2.40):
        p.box_minmax((fx - 0.05, y - 0.17, RAIL_H + 0.045), (fx + 0.05, y + 0.17, cz - 0.15), "comp")
        for s in (-1, 1):
            p.cyl(0.035, 0.045, (fx, y + s * 0.13, RAIL_H), "z", "gasket", 20)
    return p.build()


# ==========================================================================
# P07  OIL SEPARATORS
# ==========================================================================
def build_oil_separator(circ, sy):
    y = sy * SEP_Y
    p = Part(f"Oil_Separator_C{circ}", f"Oil separator - circuit {circ}")
    r, za, zb, hh = 0.17, 0.40, 0.96, 0.085
    prof = [(0, za - hh)]
    for k in range(1, 9):
        a = math.pi / 2 * k / 8
        prof.append((r * math.sin(a), za - hh * math.cos(a)))
    for k in range(0, 9):
        a = math.pi / 2 * k / 8
        prof.append((r * math.cos(a), zb + hh * math.sin(a)))
    p.lathe(prof, (SEP_X, y, 0), "z", "vessel", 48)
    p.cyl(0.13, za - hh - RAIL_H + 0.02, (SEP_X, y, RAIL_H), "z", "vessel", 32)        # skirt
    p.box((0.12, 0.06, 0.04), (SEP_X, y + sy * (r + 0.02), 0.62), "steel")             # sight glass boss
    p.cyl(0.022, 0.02, (SEP_X, y + sy * (r + 0.05), 0.62), "y" if sy > 0 else "-y", "brass", 16)
    p.cyl(0.05, 0.03, (SEP_X - r - 0.015, y, 0.95), "-x", "steel", 24)                 # inlet nozzle
    p.cyl(0.05, 0.04, (SEP_X, y, zb + hh - 0.01), "z", "steel", 24)                    # outlet nozzle
    return p.build()


# ==========================================================================
# P08  EVAPORATOR (insulated shell, water box, CHW nozzles)
# ==========================================================================
def build_evaporator():
    objs = []
    xa, xb = EVAP_X
    st = (xa, 0, EVAP_Z)
    sh = Part("Evaporator_Shell", "Evaporator shell (insulated)")
    sh.lathe([(0, -0.1), (0.15, -0.095), (0.25, -0.07), (0.30, -0.03), (0.315, 0.0), (0, 0.0)],
             st, "x", "waterbox", 48)                                                  # dished head
    sh.lathe([(0, 0), (EVAP_R, 0), (EVAP_R, xb - xa), (0, xb - xa)], st, "x", "insul", 64)
    for k in range(1, 6):                                                              # insulation seams
        sh.torus(EVAP_R + 0.002, 0.004, (xa + k * (xb - xa) / 6, 0, EVAP_Z), "x", "insul", 64, 6)
    for k in range(3):                                                                 # holding straps
        x = xa + (k + 0.5) * (xb - xa) / 3
        sh.lathe([(EVAP_R + 0.002, 0), (EVAP_R + 0.006, 0), (EVAP_R + 0.006, 0.04),
                  (EVAP_R + 0.002, 0.04)], (x, 0, EVAP_Z), "x", "galv", 64, closed=True)
    for x in (-0.58, 2.90):                                                            # saddles
        poly = [(-0.30, RAIL_H), (0.30, RAIL_H), (0.30, RAIL_H + 0.08), (0.22, EVAP_Z - 0.21),
                (-0.22, EVAP_Z - 0.21), (-0.30, RAIL_H + 0.08)]
        sh.prism(poly, "x", x - 0.05, x + 0.05, "waterbox")
    for x, yo in ((-1.10, 0.10), (-0.60, 0.20)):                                       # refrig. stubs
        for s in (-1, 1):
            sh.cyl(0.05, 0.05, (x, s * yo, EVAP_Z + EVAP_R - 0.03), "z", "steel", 24)
    objs.append(sh.build())

    wb = Part("Evaporator_Water_Box", "Water box & tube sheet")
    wb.cyl(0.365, 0.04, (xb, 0, EVAP_Z), "x", "waterbox", 64)                          # tube sheet
    wb.cyl(0.335, 0.22, (xb + 0.04, 0, EVAP_Z), "x", "waterbox", 64)                   # box
    wb.cyl(0.37, 0.035, (xb + 0.26, 0, EVAP_Z), "x", "waterbox", 64)                   # cover flange
    wb.lathe([(0.34, 0), (0.30, 0.03), (0.2, 0.05), (0, 0.055), (0, 0)], (xb + 0.295, 0, EVAP_Z),
             "x", "waterbox", 64, closed=True)                                         # dished cover
    for k in range(20):
        a = 2 * math.pi * k / 20
        for xx in (xb - 0.008, xb + 0.255):
            wb.cyl(0.011, 0.05, (xx, 0.35 * math.cos(a), EVAP_Z + 0.35 * math.sin(a)), "x", "steel", 8)
    wb.cyl(0.012, 0.03, (xb + 0.15, 0, EVAP_Z + 0.335), "z", "brass", 12)              # vent
    wb.cyl(0.012, 0.03, (xb + 0.15, 0, EVAP_Z - 0.365), "z", "brass", 12)              # drain
    objs.append(wb.build())

    for nm, disp, z, tag in (("CHW_Inlet_Nozzle", "Chilled-water INLET (return)", EVAP_Z - 0.15, "blue_tag"),
                             ("CHW_Outlet_Nozzle", "Chilled-water OUTLET (supply)", EVAP_Z + 0.15, "green_tag")):
        n = Part(nm, disp)
        ro, ri, Ln = 0.084, 0.076, 0.55                                                # 6 in. sch-40
        prof = [(ri, 0), (ro, 0), (ro, Ln - 0.024), (ro - 0.0035, Ln - 0.024), (ro - 0.0035, Ln - 0.016),
                (ro, Ln - 0.016), (ro, Ln), (ri, Ln)]
        n.lathe(prof, (xb + 0.10, 0, z), "x", "galv", 48, closed=True)
        n.lathe([(ro + 0.001, 0), (ro + 0.004, 0), (ro + 0.004, 0.08), (ro + 0.001, 0.08)],
                (xb + 0.36, 0, z), "x", tag, 48, closed=True)                          # colour band
        n.cyl(0.015, 0.04, (xb + 0.29, 0, z + ro - 0.005), "z", "brass", 12)           # thermowell
        objs.append(n.build())
    return objs


# ==========================================================================
# P09  REFRIGERANT PIPING (2 circuits)
# ==========================================================================
def build_piping(circ, s):
    p = Part(f"Refrigerant_Circuit_{circ}", f"Refrigerant piping - circuit {circ}")
    sx = COMP_X0 + 0.10
    # Suction (insulated): evaporator -> compressor motor end
    p.pipe([(-1.10, s * 0.10, EVAP_Z + EVAP_R + 0.01), (-1.10, s * 0.10, 1.08), (-1.10, s * COMP_Y, 1.08),
            (sx, s * COMP_Y, 1.08), (sx, s * COMP_Y, COMP_Z + 0.245)], 0.062, "insul", 20, bend=0.13)
    # Discharge: compressor -> oil separator
    dx = COMP_X0 + 0.97
    p.pipe([(dx, s * COMP_Y, COMP_Z + 0.20), (dx, s * COMP_Y, 0.95), (dx, s * SEP_Y, 0.95),
            (SEP_X - 0.21, s * SEP_Y, 0.95)], 0.042, "steel", 16, bend=0.09)
    # Hot-gas riser + discharge manifold feeding every coil (under the V-bottoms)
    p.pipe([(SEP_X, s * SEP_Y, 1.075), (SEP_X, s * SEP_Y, 1.13)], 0.042, "steel", 16)
    p.pipe([(PANEL_X[1] + 0.06, s * SEP_Y, 1.13), (X1 - 0.35, s * SEP_Y, 1.13)], 0.045, "steel", 16)
    for xc in BAY_C:
        xx = max(xc, PANEL_X[1] + 0.09)
        p.pipe([(xx, s * SEP_Y, 1.16), (xx, s * SEP_Y, V_BOT - 0.03)], 0.024, "steel", 12)
    # Liquid line (copper) with filter-drier and electronic expansion valve
    p.pipe([(X1 - 0.35, s * 0.45, 1.18), (PANEL_X[1] + 0.06, s * 0.45, 1.18)], 0.024, "copper", 14)
    p.pipe([(-0.60, s * 0.45, 1.18), (-0.60, s * 0.20, 1.18), (-0.60, s * 0.20, EVAP_Z + EVAP_R + 0.01)],
           0.024, "copper", 14, bend=0.07)
    p.cyl(0.042, 0.26, (0.40, s * 0.45, 1.18), "x", "steel", 24)                       # filter-drier
    p.cyl(0.03, 0.06, (-0.60 - 0.03, s * 0.20, 1.02), "x", "brass", 20)                # EEV body
    p.cyl(0.032, 0.11, (-0.60, s * 0.20, 1.02), "-y" if s > 0 else "y", "gasket", 20)  # EEV actuator
    # Service / isolation valves
    p.cyl(0.07, 0.05, (sx - 0.025, s * COMP_Y, 0.96), "x", "brass", 24)
    p.cyl(0.055, 0.05, (dx - 0.025, s * COMP_Y, 0.90), "x", "brass", 24)
    return p.build()


# ==========================================================================
# Assemble
# ==========================================================================
def assemble():
    make_textures()
    make_materials()
    parts = [
        part("P01", "Base_Frame", "Base Frame", "Structure",
             "Welded steel skid: C-channel base rails with rigging holes, cross members, "
             "posts, mid and top rails. Carries all components.",
             build_base_frame()),
        part("P02", "Control_Panel", "Control & Power Panel", "Electrical",
             "NEMA 3R power and control enclosure with HMI controller, main disconnect, "
             "power section and conduits to the compressors.",
             build_control_panel(), explode=(-1.6, 0, 0)),
        part("P03", "Condenser_Coils", "Condenser Coils", "Heat Transfer",
             "All-aluminum microchannel condenser coils arranged in V-pairs, one pair per fan bay.",
             build_coils(), explode=(0, 0, 1.3)),
        part("P04", "Casing_Fan_Deck", "Casing & Fan Deck", "Enclosure",
             "Sheet-metal fan deck, V-end panels and drain channels that close the coil sections.",
             build_casing(), explode=(0, 0, 2.2)),
        part("P05", "Condenser_Fans", "Condenser Fans", "Air Moving",
             "14 direct-drive condenser fans (2 per bay): composite sickle blades, venturi "
             "rings, motors and wire guards.",
             build_fans(), explode=(0, 0, 3.0)),
        part("P06", "Compressors", "Screw Compressors", "Refrigeration",
             "Two semi-hermetic screw compressors (one per refrigerant circuit) on neoprene isolators.",
             [build_compressor(1, -1), build_compressor(2, 1)]),
        part("P07", "Oil_Separators", "Oil Separators", "Refrigeration",
             "Vertical oil separators on the compressor discharge of each circuit.",
             [build_oil_separator(1, -1), build_oil_separator(2, 1)]),
        part("P08", "Evaporator", "Evaporator", "Heat Transfer",
             "Shell-and-tube evaporator with closed-cell insulation, water box and grooved "
             "chilled-water inlet/outlet connections.",
             build_evaporator()),
        part("P09", "Refrigerant_Piping", "Refrigerant Piping", "Refrigeration",
             "Suction, discharge, hot-gas manifold and liquid lines for both circuits, "
             "with filter-driers, EEVs and service valves.",
             [build_piping(1, -1), build_piping(2, 1)], explode=(0, 0, 0.75)),
    ]
    # Per-child explode offsets for the side-by-side circuit components.
    for name, v in (("Compressor_C1", (0, -1.9, 0)), ("Compressor_C2", (0, 1.9, 0)),
                    ("Oil_Separator_C1", (0.4, -1.7, 0)), ("Oil_Separator_C2", (0.4, 1.7, 0)),
                    ("Evaporator_Water_Box", (0.7, 0, 0)), ("CHW_Inlet_Nozzle", (1.3, 0, 0)),
                    ("CHW_Outlet_Nozzle", (1.3, 0, 0)), ("Power_Conduits", (0, 0, 0)),
                    ("Panel_Door_1_Controls", (-0.35, 0, 0)), ("Panel_Door_2_Disconnect", (-0.35, 0, 0)),
                    ("Panel_Door_3_Power", (-0.35, 0, 0))):
        ob = bpy.data.objects[name]
        ob["explode"] = to_gltf(v)
        ob["explode_blender"] = list(v)

    lo, hi = world_bbox(parts)
    root = group("Chiller_AirCooled_Screw", parts, at=(0, 0, 0))
    dims = hi - lo
    root["display_name"] = "Air-Cooled Screw Chiller (14-fan, V-coil)"
    root["units"] = "meters"
    root["length_mm"] = round(dims.x * 1000)
    root["width_mm"] = round(dims.y * 1000)
    root["height_mm"] = round(dims.z * 1000)
    root["length_in"] = round(dims.x / 0.0254, 1)
    root["width_in"] = round(dims.y / 0.0254, 1)
    root["height_in"] = round(dims.z / 0.0254, 1)
    root["note"] = ("Presentation model. Representative geometry; final dimensions to be "
                    "matched to the manufacturer's submittal drawing.")
    return root, dims


def export_glb(path):
    kw = dict(filepath=path, export_format="GLB", export_yup=True, export_apply=True,
              export_extras=True, export_animations=True, export_animation_mode="NLA_TRACKS",
              export_cameras=False, export_lights=False, export_image_format="AUTO",
              export_texcoords=True, export_normals=True)
    bpy.ops.export_scene.gltf(**kw)


# --------------------------------------------------------------------------
# Presentation rig + Cycles renders (optional, --render)
# --------------------------------------------------------------------------
def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render_rig():
    import addon_utils
    addon_utils.enable("cycles", default_set=True)
    rig = bpy.data.collections.new("Presentation_Rig")
    SCENE.collection.children.link(rig)

    me = bpy.data.meshes.new("Ground")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=150)
    bm.to_mesh(me)
    bm.free()
    g = bpy.data.objects.new("Ground", me)
    gm = bpy.data.materials.new("Ground_Concrete")
    try:
        gm.use_nodes = True
    except AttributeError:
        pass
    bsdf = next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*srgb("#b9bcbf"), 1)
    bsdf.inputs["Roughness"].default_value = 0.85
    me.materials.append(gm)
    rig.objects.link(g)

    world = bpy.data.worlds.new("Studio")
    SCENE.world = world
    try:
        world.use_nodes = True
    except AttributeError:
        pass
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    sky = world.node_tree.nodes.new("ShaderNodeTexGradient")
    ramp = world.node_tree.nodes.new("ShaderNodeValToRGB")
    mapn = world.node_tree.nodes.new("ShaderNodeMapping")
    tc = world.node_tree.nodes.new("ShaderNodeTexCoord")
    mapn.inputs["Rotation"].default_value = (0, -math.pi / 2, 0)
    world.node_tree.links.new(tc.outputs["Generated"], mapn.inputs["Vector"])
    world.node_tree.links.new(mapn.outputs["Vector"], sky.inputs["Vector"])
    world.node_tree.links.new(sky.outputs["Fac"], ramp.inputs["Fac"])
    world.node_tree.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    ramp.color_ramp.elements[0].color = (*srgb("#eef1f4"), 1)
    ramp.color_ramp.elements[1].color = (*srgb("#9fb3c8"), 1)
    bg.inputs["Strength"].default_value = 0.9

    def area(name, loc, energy, size, target=(0, 0, 1.2)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy = energy
        ld.size = size
        lo = bpy.data.objects.new(name, ld)
        lo.location = loc
        look_at(lo, target)
        rig.objects.link(lo)
    area("Key", (-9, -10, 12), 9000, 6)
    area("Fill", (10, -6, 6), 2500, 8)
    area("Rim", (6, 12, 9), 4000, 6)

    cd = bpy.data.cameras.new("Camera")
    cam = bpy.data.objects.new("Camera", cd)
    rig.objects.link(cam)
    SCENE.camera = cam
    r = SCENE.render
    r.engine = "CYCLES"
    SCENE.cycles.device = "CPU"
    SCENE.cycles.samples = 16 if QUICK else 64
    SCENE.cycles.use_denoising = True
    r.resolution_x, r.resolution_y = 1600, 900
    r.resolution_percentage = 50 if QUICK else 100
    r.film_transparent = False
    try:
        SCENE.view_settings.view_transform = "AgX"
        SCENE.view_settings.look = "AgX - Medium High Contrast"
    except TypeError:
        pass
    return cam


def do_renders():
    cam = render_rig()
    out = os.path.join(OUT, "renders")
    os.makedirs(out, exist_ok=True)
    SCENE.frame_set(10)

    def shot(fname, loc, target, lens):
        cam.location = loc
        cam.data.lens = lens
        look_at(cam, target)
        SCENE.render.filepath = os.path.join(out, fname)
        bpy.ops.render.render(write_still=True)
        print("rendered", fname)

    shot("01_hero.png", (-9.2, -8.4, 5.6), (0.3, 0, 1.0), 40)
    shot("02_panel_end.png", (-7.4, -3.4, 1.9), (-3.6, 0.0, 0.95), 50)
    shot("03_machinery.png", (-1.6, -4.9, 1.25), (-1.9, 0, 0.75), 30)
    shot("05_fans_closeup.png", (0.6, -3.2, 3.9), (1.6, 0.2, 2.25), 45)
    # exploded view
    moved = []
    for ob in bpy.data.objects:
        if "explode_blender" in ob.keys():
            v = Vector(ob["explode_blender"])
            if v.length > 0:
                ob.location += v
                moved.append((ob, v))
    shot("04_exploded.png", (-11.5, -12.0, 8.6), (0.0, 0, 2.2), 36)
    for ob, v in moved:
        ob.location -= v


def main():
    root, dims = assemble()
    os.makedirs(OUT, exist_ok=True)
    glb = os.path.join(OUT, GLB_NAME)
    export_glb(glb)
    print(f"GLB written: {glb}  ({os.path.getsize(glb) / 1e6:.2f} MB)")
    print(f"Overall L x W x H: {dims.x:.3f} x {dims.y:.3f} x {dims.z:.3f} m")
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
               for o in bpy.data.objects if o.type == "MESH")
    print(f"Triangles: {tris:,}")
    if DO_RENDER:
        do_renders()
    for img in bpy.data.images:
        if img.source == "FILE":
            img.pack()
    blend = os.path.join(HERE, "chiller_aircooled_screw.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print("Blend written:", blend)


main()
