"""
YORK YCAL0134 Air-Cooled Scroll Chiller - parametric Blender build script
=========================================================================

Builds a presentation-grade, part-separated model of the YORK Millennium
YCAL0134 (Style C) air-cooled scroll chiller and exports it as GLB.

Source data: YORK Engineering Guide, Form 150.62-EG1 (406)
  * Physical Data - English Units ........ page 55 (YCAL0134 column)
  * Dimensions - YCAL0114-0134 English ... pages 68-69 (views A-A, B-B, D-D)

Every major component is its own named node in the glTF scene graph, so a
web viewer (three.js, Babylon, <model-viewer>) can pick, highlight, hide,
isolate or explode it. Each part node also carries glTF "extras" metadata
(part_id, display_name, category, description, explode vector).

Run (Blender >= 4.2 / 5.x):
    blender -b -P build_chiller.py -- [--out <dir>] [--render | --quick]
or with the bpy Python module:
    python build_chiller.py -- [--out <dir>] [--render | --quick]

Units: all drawing dimensions below are in INCHES, measured as on the
submittal drawing (x from the control-panel end, y from the cooler side,
z from the bottom of the base rails). The model is built in meters,
centered on the footprint; the GLB is exported Y-up (glTF standard).
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
GLB_NAME = "york_ycal0134_chiller.glb"

# --------------------------------------------------------------------------
# DRAWING DIMENSIONS (inches) - Form 150.62-EG1, YCAL0114-0134
# --------------------------------------------------------------------------
IN = 0.0254
L_IN = 183.0               # base / frame length                     (p.69 "183")
W_IN = 88.25               # overall width                           (p.68 "88 1/4")
PANEL_DEPTH = 7.875        # control/power panel projection          (p.69 "7 7/8" -> 190 OAL)
CASING_TOP = 91.4375       # top of casing / fan deck                (p.69 "91 7/16")
FAN_TOP = 96.0             # top of fan discharge rings              (p.69 "96")
LOWER_H = 38.0             # machinery section height                (p.69 "38")
PANEL_Z = (38.0, 67.0)     # panel bottom / top                      (p.69 "38" + "29")
PANEL_Y = (19.125, 69.125) # panel edges from the cooler side        (p.69 "19 1/8" + "50")
BASE_H = 6.0               # formed-steel base rail
RIG_HOLES_X = (7.875, 75.125, 107.875, 175.125)   # 3"x3" rigging holes (p.69 "7 7/8", "67 1/4")
END_POST = 6.5             # corner post depth along x
BAY0 = 8.0                 # first coil / fan bay starts here
N_BAYS = 4                 # 4 bays x 2 fans = 8 fans                (p.55 "Number of fans 8")
BAY = (L_IN - 2 * BAY0) / N_BAYS                      # 41.75"
BAY_X = [BAY0 + i * BAY for i in range(N_BAYS + 1)]   # bay lines
BAY_C = [BAY0 + (i + 0.5) * BAY for i in range(N_BAYS)]
FAN_Y = (W_IN * 0.25, W_IN * 0.75)
DIV_Z = (37.4, 40.5)       # divider rail between machinery and coil sections
COIL_Z = (40.5, 86.5)
COIL_DEPTH = 3.5           # 3 rows (p.55 "Number of rows 3")
COMP_X = (23.0, 42.0, 61.5, 119.0, 139.0, 158.5)      # 6 scroll compressors (p.69 view D-D)
COMP_Y = 72.0
COOLER_AX = (18.7, 17.125) # cooler axis (y, z)                      (p.68 "17 1/8")
COOLER_X = (13.6, 107.5)   # shell between heads; 15" x 8' DX cooler (p.55)
NOZZLE_X = (20.0, 103.0)   # 8" water outlet / inlet                 (p.69 "20", "83")
NOZZLE_OUT = -2.375        # nozzle ends past the unit edge          (p.68 "2 3/8")

L = L_IN * IN
W = W_IN * IN

FPS = 24
FAN_FRAMES = 48            # frames per fan revolution in the demo animation


def P(x, y, z):
    """Drawing inches (x from panel end, y from cooler side, z up) -> Blender meters."""
    return Vector((x * IN - L / 2, y * IN - W / 2, z * IN))


def to_gltf(v):
    """Blender Z-up vector -> glTF Y-up vector."""
    return [round(v[0], 4), round(v[2], 4), round(-v[1], 4)]


# --------------------------------------------------------------------------
# Scene reset
# --------------------------------------------------------------------------
bpy.ops.wm.read_factory_settings(use_empty=True)
SCENE = bpy.context.scene
SCENE.name = "Chiller"
SCENE.unit_settings.system = "IMPERIAL"
SCENE.unit_settings.length_unit = "INCHES"
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

    # Fin-and-tube coil face (tile = 0.10 m): vertical aluminum fins at 13 fpi,
    # copper tubes in staggered horizontal rows behind them.
    S = 512
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    fin_px = S / (0.10 / IN * 13)                     # px per fin
    fin = (xx % fin_px) < fin_px * 0.45
    row_px = S / (0.10 / 1.0 * 39.37)                 # 1" tube row pitch
    tube = (np.abs((yy % row_px) - row_px / 2) < row_px * 0.17)
    base = np.where(fin[..., None], np.array([172, 177, 182]), np.array([70, 74, 78])).astype(np.float32)
    copper = np.array([150, 96, 62], np.float32)
    mix = (tube & ~fin)[..., None]
    base = np.where(mix, copper, base)
    base = np.where((tube & fin)[..., None], base * 1.06, base)
    base += np.random.default_rng(7).normal(0, 3, (S, S, 1))
    Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB").save(
        os.path.join(TEX_DIR, "coil_basecolor.png"))
    h = np.where(fin, 1.0, 0.15) + np.where(tube, 0.25, 0.0)
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 2.0
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 2.0
    n = np.dstack([-dx, dy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB").save(
        os.path.join(TEX_DIR, "coil_normal.png"))

    # Millennium control center LCD: 2 lines x 20 characters, LED backlight.
    img = Image.new("RGB", (640, 180), (64, 150, 72))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 639, 179], outline=(30, 90, 40), width=6)
    f = _font(46, mono=True)
    d.text((22, 24), "LCHLT  44.0 °F  RUN", font=f, fill=(12, 40, 16))
    d.text((22, 96), "SYS1 3/3  SYS2 3/3 ", font=f, fill=(12, 40, 16))
    img.save(os.path.join(TEX_DIR, "lcd_display.png"))

    # Unit nameplate (generic demo data).
    img = Image.new("RGB", (512, 256), (198, 201, 204))
    d = ImageDraw.Draw(img)
    for yline in range(0, 256, 3):
        d.line([(0, yline), (512, yline)], fill=(188, 191, 195))
    d.rectangle([4, 4, 507, 251], outline=(40, 40, 40), width=3)
    d.text((16, 12), "AIR-COOLED SCROLL CHILLER", font=_font(28, bold=True), fill=(15, 15, 15))
    lines = ["MODEL:        YCAL0134 (DEMO)", "NOM. CAPACITY: 130 TONS",
             "REFRIGERANT:  R-407C  2 SYSTEMS", "POWER:        460 V / 3 PH / 60 HZ",
             "COMPRESSORS:  6 SCROLL"]
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
    col = srgb(hexcol) if hexcol else (1, 1, 1)
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
        nm.inputs["Strength"].default_value = 0.7
        nt.links.new(nn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    MAT[key] = m
    return m


def make_materials():
    # Galvanized steel with baked-on powder paint (spec p.4) - frame and casing.
    mat("frame", "#c9cac4", 0.15, 0.45, name="PowderCoat_Frame")
    mat("casing", "#d3d4ce", 0.10, 0.42, name="PowderCoat_Casing")
    mat("panel", "#d8d9d4", 0.05, 0.38, name="PowderCoat_Panel")
    mat("galv", "#a3a8ad", 0.85, 0.32, name="Galvanized_Steel")
    mat("gasket", "#151617", 0.0, 0.8, name="Rubber_Black")
    mat("conduit", "#2a2d30", 0.0, 0.6, name="LiquidTight_Conduit")
    mat("coil", None, 0.7, 0.4, tex="coil_basecolor.png", normal="coil_normal.png",
        name="Coil_FinAndTube_AlCu")
    mat("guard", "#18191b", 0.4, 0.45, name="Fan_Guard_Coated_Steel")
    mat("ring", "#2a2d31", 0.1, 0.5, name="Fan_Discharge_Ring")
    mat("blade", "#3a3e43", 0.05, 0.45, name="Fan_Blade_GFR_Polypropylene")
    mat("hub", "#9aa0a6", 0.9, 0.3, name="Fan_Hub_Aluminum")
    mat("motor", "#2b3036", 0.5, 0.45, name="Fan_Motor_TEAO")
    mat("comp", "#1e2a38", 0.35, 0.4, name="Compressor_Shell")
    mat("steel", "#7a8086", 0.7, 0.4, name="Steel_Machined")
    mat("insul", "#121314", 0.0, 0.88, name="Insulation_ClosedCell_Black")
    mat("cooler", "#3a3f45", 0.4, 0.45, name="Cooler_Head_Paint")
    mat("copper", "#b87333", 1.0, 0.32, name="Copper")
    mat("brass", "#b59a42", 1.0, 0.35, name="Brass")
    mat("red", "#c8102e", 0.0, 0.4, name="Paint_Safety_Red")
    mat("yellow", "#f2c200", 0.0, 0.45, name="Paint_Safety_Yellow")
    mat("blue_tag", "#1565c0", 0.0, 0.45, name="Tag_Supply_Blue")
    mat("green_tag", "#2e7d32", 0.0, 0.45, name="Tag_Return_Green")
    mat("key_blue", "#1f5fa8", 0.0, 0.5, name="Key_Display")
    mat("key_gray", "#5d6268", 0.0, 0.5, name="Key_Entry")
    mat("key_green", "#2e7d32", 0.0, 0.5, name="Key_Setpoints")
    mat("key_amber", "#d18a00", 0.0, 0.5, name="Key_Unit")
    mat("bezel", "#26292d", 0.0, 0.55, name="Bezel_Black")
    mat("lcd", None, 0.0, 0.25, emit=1.4, tex="lcd_display.png", name="LCD_Display")
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




# --------------------------------------------------------------------------
# Inch-space helpers on top of Part
# --------------------------------------------------------------------------
def ibox(p, lo, hi, m, bevel=0.0):
    """Axis-aligned box between two drawing points (inches)."""
    return p.box_minmax(tuple(P(*lo)), tuple(P(*hi)), m, bevel=bevel * IN)


def beam(p, a, b, w, h, m):
    """Rectangular bar from drawing point a to b (inches), section w x h."""
    A, B = P(*a), P(*b)
    d = (B - A)
    ln = d.length
    d.normalize()
    up = Vector((0, 0, 1)) if abs(d.z) < 0.95 else Vector((1, 0, 0))
    s = d.cross(up).normalized()
    u = d.cross(s)
    bm_ = bm_box((ln, w * IN, h * IN))
    M = Matrix((d, s, u)).transposed().to_4x4()
    M.translation = (A + B) / 2
    p.merge(xf(bm_, M), m)


def ipipe(p, pts, r, m, sides=14, bend=None, caps=True):
    return p.pipe([P(*q) for q in pts], r * IN, m, sides, None if bend is None else bend * IN, caps)


def icyl(p, r, h, start, axis, m, seg=32):
    return p.cyl(r * IN, h * IN, tuple(P(*start)), axis, m, seg)


def ilathe(p, prof_in, start, axis, m, seg=48, closed=False):
    return p.lathe([(r * IN, z * IN) for r, z in prof_in], tuple(P(*start)), axis, m, seg, closed)


def itorus(p, R, r, start, axis, m, seg=48, sides=8):
    return p.torus(R * IN, r * IN, tuple(P(*start)), axis, m, seg, sides)


def bm_merge_into(dst, src):
    me = bpy.data.meshes.new("_m")
    src.to_mesh(me)
    src.free()
    dst.from_mesh(me)
    bpy.data.meshes.remove(me)


# ==========================================================================
# P01  BASE FRAME (galvanized, powder-coated formed steel)
# ==========================================================================
def build_base_frame():
    p = Part("Base_Frame_Structure", "Base rails, posts & bracing")
    # Formed-steel base rails (C-channel, opening inward) with 3"x3" rigging holes.
    for side in (0, 1):
        y0 = 0.0 if side == 0 else W_IN
        s = 1 if side == 0 else -1
        yo, yi, yw = y0, y0 + s * 3.0, y0 + s * 0.19
        poly = [(yo, 0), (yi, 0), (yi, 0.4), (yw, 0.4), (yw, BASE_H - 0.4), (yi, BASE_H - 0.4),
                (yi, BASE_H), (yo, BASE_H)]
        poly = [((y - W_IN / 2) * IN, z * IN) for y, z in poly]
        if side == 1:
            poly = poly[::-1]
        rail = bm_prism(poly, "x", -L / 2, L / 2)
        cut = bmesh.new()
        for x in RIG_HOLES_X:
            hole = bm_box((3 * IN, 1.0 * IN, 3 * IN))
            xf(hole, Mx(tuple(P(x, y0 + s * 0.1, 3.0))))
            bm_merge_into(cut, hole)
        p.merge(bm_boolean_diff(rail, cut), "frame")
    # Cross members (cooler and compressor supports sit on these).
    for x in (1.5, 27.0, BAY_X[1], 60.0, 96.0, 120.0, BAY_X[3], 150.0, 181.5):
        ibox(p, (x - 1.5, 3.0, 2.0), (x + 1.5, W_IN - 3.0, BASE_H), "frame")
    # Corner posts (full height) and bay posts.
    for x0 in (0.0, L_IN - END_POST):
        for y0 in (0.0, W_IN - 6.0):
            ibox(p, (x0, y0, BASE_H), (x0 + END_POST, y0 + 6.0, COIL_Z[1] + 2.5), "frame", bevel=0.15)
    for x in BAY_X[1:-1]:
        for y0 in (0.0, W_IN - 2.5):
            ibox(p, (x - 1.25, y0, BASE_H), (x + 1.25, y0 + 2.5, COIL_Z[1] + 2.5), "frame")
    # Divider rail (machinery / coil sections) and top rails, both sides and ends.
    for ya_, yb_ in ((0.15, 3.0), (W_IN - 3.0, W_IN - 0.15)):          # set 0.15" behind post faces
        ibox(p, (0.15, ya_, DIV_Z[0]), (L_IN - 0.15, yb_, DIV_Z[1]), "frame")
        ibox(p, (0.15, ya_, COIL_Z[1]), (L_IN - 0.15, yb_, COIL_Z[1] + 2.5), "frame")
    for x0 in (0.0, L_IN - 3.0):
        ibox(p, (x0, 6.0, DIV_Z[0]), (x0 + 3.0, W_IN - 6.0, DIV_Z[1]), "frame")
        ibox(p, (x0, 6.0, COIL_Z[1]), (x0 + 3.0, W_IN - 6.0, COIL_Z[1] + 2.5), "frame")
    # Diagonal bracing in the machinery section (both sides, p.69 side view).
    for y in (0.6, W_IN - 0.6):
        beam(p, (56.0, y, 7.0), (89.5, y, DIV_Z[0]), 0.4, 2.0, "frame")
        beam(p, (93.0, y, DIV_Z[0]), (103.5, y, 27.0), 0.4, 2.0, "frame")
    return [p.build()]


# ==========================================================================
# P02  CONTROL / POWER PANEL (end-mounted, p.68 view B-B, p.69 view D-D)
# ==========================================================================
def build_control_panel():
    objs = []
    xf_, xb = -PANEL_DEPTH, 0.0
    (ya, yb), (za, zb) = PANEL_Y, PANEL_Z
    split = ya + 20.0                         # control section (cooler side) | power section
    face = xf_

    enc = Part("Panel_Enclosure", "Panel enclosure (NEMA 3R)")
    ibox(enc, (xf_ + 0.3, ya, za), (xb, yb, zb), "panel", bevel=0.4)
    ibox(enc, (xf_ - 0.9, ya - 0.6, zb), (xb + 0.2, yb + 0.6, zb + 0.6), "panel", bevel=0.15)   # rain hood
    for y in (ya + 1.0, yb - 1.0):                                                             # brackets
        ibox(enc, (xf_ + 1.0, y - 0.6, za - 1.2), (xb + 0.5, y + 0.6, za), "galv")
    # conduit knock-outs on the bottom (view B-B)
    for k, (r, dy) in enumerate(((1.25, 8.0), (1.0, 12.6), (0.75, 16.2))):
        icyl(enc, r, 0.15, (xf_ + 3.5, yb - dy, za - 0.1), "z", "gasket", 20)
    for k in range(8):
        icyl(enc, 0.4, 0.15, (xf_ + 2.5 + (k % 2) * 2.0, ya + 3.0 + (k // 2) * 1.6, za - 0.1),
             "z", "gasket", 12)
    objs.append(enc.build())

    # Control section door: LCD (2 x 20), colour-coded 12-key keypad, unit switch.
    cd = Part("Control_Panel_Door", "Control center door - LCD & keypad")
    ibox(cd, (face - 0.6, ya + 0.4, za + 0.5), (face + 0.4, split - 0.2, zb - 0.5), "panel", bevel=0.2)
    yc = (ya + split) / 2
    ibox(cd, (face - 1.0, yc - 6.0, 55.0), (face - 0.5, yc + 6.0, 63.5), "bezel", bevel=0.15)
    cd.quad([tuple(P(face - 1.05, yc + 4.8, 57.6)), tuple(P(face - 1.05, yc - 4.8, 57.6)),
             tuple(P(face - 1.05, yc - 4.8, 60.3)), tuple(P(face - 1.05, yc + 4.8, 60.3))], "lcd")
    keys = ["key_blue"] * 4 + ["key_gray"] * 4 + ["key_green"] * 2 + ["key_amber"] * 2
    for i, k in enumerate(keys):
        r, c = divmod(i, 4)
        y = yc + 3.6 - c * 2.4
        z = 53.0 - r * 1.9
        ibox(cd, (face - 1.15, y - 0.9, z - 0.65), (face - 0.5, y + 0.9, z + 0.65), k, bevel=0.12)
    ibox(cd, (face - 1.4, yc - 1.2, 44.0), (face - 0.5, yc + 1.2, 46.5), "bezel", bevel=0.15)   # ON/OFF
    ibox(cd, (face - 1.9, yc - 0.5, 44.6), (face - 1.3, yc + 0.5, 45.9), "red", bevel=0.1)
    for z in (za + 4, zb - 4):                                                                 # hinges
        icyl(cd, 0.35, 2.4, (face - 0.3, split - 0.1, z - 1.2), "z", "steel", 12)
    icyl(cd, 0.6, 0.6, (face - 0.6, ya + 1.8, 52.0), "-x", "steel", 16)                       # latch
    ibox(cd, (face - 1.6, ya + 1.5, 51.0), (face - 1.2, ya + 2.1, 53.0), "gasket")
    objs.append(cd.build())

    # Power section door: two lockable disconnect handles (SYS 1 / SYS 2), labels.
    pdr = Part("Power_Panel_Door", "Power panel door - disconnects")
    ibox(pdr, (face - 0.6, split + 0.2, za + 0.5), (face + 0.4, yb - 0.4, zb - 0.5), "panel", bevel=0.2)
    for i, y in enumerate((split + 8.5, split + 20.5)):
        ibox(pdr, (face - 1.0, y - 2.6, 49.0), (face - 0.5, y + 2.6, 54.2), "yellow", bevel=0.12)
        icyl(pdr, 1.0, 0.9, (face - 0.9, y, 51.6), "-x", "red", 24)
        ibox(pdr, (face - 2.8, y - 0.75, 49.0), (face - 1.6, y + 0.75, 55.5), "red", bevel=0.3)
    pdr.quad([tuple(P(face - 0.65, split + 18.0, 58.0)), tuple(P(face - 0.65, split + 4.0, 58.0)),
              tuple(P(face - 0.65, split + 4.0, 65.6)), tuple(P(face - 0.65, split + 18.0, 65.6))], "label")
    pdr.quad([tuple(P(face - 0.65, yb - 1.8, 40.5)), tuple(P(face - 0.65, yb - 11.0, 40.5)),
              tuple(P(face - 0.65, yb - 11.0, 45.1)), tuple(P(face - 0.65, yb - 1.8, 45.1))], "nameplate")
    for z in (za + 4, zb - 4):
        icyl(pdr, 0.35, 2.4, (face - 0.3, yb - 0.6, z - 1.2), "z", "steel", 12)
    for z in (44.0, 61.0):
        icyl(pdr, 0.6, 0.6, (face - 0.6, split + 1.6, z), "-x", "steel", 16)
        ibox(pdr, (face - 1.6, split + 1.3, z - 1.0), (face - 1.2, split + 1.9, z + 1.0), "gasket")
    objs.append(pdr.build())

    # Liquid-tight conduit from the power panel to each compressor terminal box.
    c = Part("Power_Conduits", "Liquid-tight conduit to compressors")
    for sysn, xs, y in ((1, COMP_X[:3], 83.6), (2, COMP_X[3:], 84.9)):
        y0 = yb - 3.0 - (sysn - 1) * 3.0
        ipipe(c, [(xf_ + 3.5, y0, za), (xf_ + 3.5, y0, 32.0), (9.0, y0, 32.0), (9.0, y, 32.0),
                  (xs[-1], y, 32.0)], 0.55, "conduit", 12, bend=2.5)
        for x in xs:
            ipipe(c, [(x, y, 32.0), (x, y, 26.5), (x, COMP_Y + 10.4, 26.5)], 0.4, "conduit", 10, bend=1.5)
    objs.append(c.build())
    return objs


# ==========================================================================
# P03  CONDENSER COILS (fin & tube, 8 panels on the long sides)
# ==========================================================================
def coil_panel(name, display, x0, x1, side):
    p = Part(name, display)
    ya = 0.75 if side == 0 else W_IN - 0.75 - COIL_DEPTH
    lo, hi = P(x0, ya, COIL_Z[0]), P(x1, ya + COIL_DEPTH, COIL_Z[1])
    size = hi - lo
    b = bm_box(tuple(size))
    uvl = b.loops.layers.uv.new("UVMap")
    b.normal_update()
    for f in b.faces:
        for l in f.loops:
            co = l.vert.co + size / 2
            n = f.normal
            if abs(n.y) > 0.5:
                l[uvl].uv = (co.x / 0.10, co.z / 0.10)
            else:
                l[uvl].uv = boxuv(co, n, 0.10)
    xf(b, Mx(tuple((lo + hi) / 2)))
    p.merge(b, "coil")
    for x in (x0 - 0.4, x1 + 0.4):                                    # galvanized tube sheets
        ibox(p, (x - 0.4, ya - 0.2, COIL_Z[0]), (x + 0.4, ya + COIL_DEPTH + 0.2, COIL_Z[1]), "galv")
    yh = ya + COIL_DEPTH + 0.9 if side == 0 else ya - 0.9               # inner-face copper headers
    for x in (x0 + 2.0, x1 - 2.0):
        ipipe(p, [(x, yh, COIL_Z[0] + 2.0), (x, yh, COIL_Z[1] - 2.0)], 0.75, "copper", 14)
    for z in np.linspace(COIL_Z[0] + 4, COIL_Z[1] - 4, 7):             # return bends at the far end
        itorus(p, 0.5, 0.19, (x1 - 0.2, ya + COIL_DEPTH / 2, float(z)), "x", "copper", 12, 6)
    return p.build()


def build_coils():
    objs = []
    for i in range(N_BAYS):
        x0 = (END_POST + 0.6) if i == 0 else BAY_X[i] + 1.5
        x1 = (L_IN - END_POST - 0.6) if i == N_BAYS - 1 else BAY_X[i + 1] - 1.5
        for side, sname in ((0, "Front"), (1, "Rear")):
            objs.append(coil_panel(f"Coil_{sname}_Bay_{i + 1}",
                                   f"Condenser coil - {sname.lower()} side, bay {i + 1}", x0, x1, side))
    return objs


# ==========================================================================
# P04  CASING & FAN DECK
# ==========================================================================
def build_casing():
    objs = []
    deck = Part("Fan_Deck", "Fan deck & top fascia")
    plate = bm_box((L, W, 0.5 * IN))
    xf(plate, Mx(tuple(P(L_IN / 2, W_IN / 2, CASING_TOP - 0.25))))
    cut = bmesh.new()
    for xc in BAY_C:
        for yc in FAN_Y:
            c = xf(bm_cyl(17.1 * IN, 4 * IN, 64), Mx(tuple(P(xc, yc, CASING_TOP - 2))))
            bm_merge_into(cut, c)
    deck.merge(bm_boolean_diff(plate, cut), "casing")
    for y0 in (0.0, W_IN - 0.15):                                       # side fascia
        ibox(deck, (0, y0, COIL_Z[1] + 2.5), (L_IN, y0 + 0.15, CASING_TOP), "casing")
    for x0 in (0.0, L_IN - 0.15):
        ibox(deck, (x0, 0, COIL_Z[1] + 2.5), (x0 + 0.15, W_IN, CASING_TOP), "casing")
    for x in BAY_X[1:-1]:                                               # deck seams
        ibox(deck, (x - 0.6, 1.0, CASING_TOP), (x + 0.6, W_IN - 1.0, CASING_TOP + 0.5), "casing", bevel=0.15)
    ibox(deck, (1.0, W_IN / 2 - 0.6, CASING_TOP), (L_IN - 1.0, W_IN / 2 + 0.6, CASING_TOP + 0.5),
         "casing", bevel=0.15)
    objs.append(deck.build())

    ends = Part("End_Panels", "Coil-section end panels")
    for x0, s in ((0.6, 1), (L_IN - 0.6, -1)):
        ibox(ends, (x0 - 0.06, 6.0, DIV_Z[1]), (x0 + 0.06, W_IN - 6.0, COIL_Z[1] + 2.5), "casing")
        xo = x0 - s * 0.9                                               # stiffeners (p.68 view A-A)
        ibox(ends, (min(x0, xo), 6.0, 68.0), (max(x0, xo), W_IN - 6.0, 72.0), "casing", bevel=0.15)
        for y in (20.5, W_IN - 20.5):
            ibox(ends, (min(x0, xo), y - 1.0, DIV_Z[1]), (max(x0, xo), y + 1.0, 68.0), "casing", bevel=0.1)
        for ya_ in (30.0, W_IN - 30.0):
            a, b2 = (x0 - s * 0.45, W_IN / 2, CASING_TOP - 3.0), (x0 - s * 0.45, ya_, 72.0)
            beam(ends, a, b2, 0.9, 2.0, "casing")
    objs.append(ends.build())
    return objs


# ==========================================================================
# P05  CONDENSER FANS (8x, 3-blade, direct drive, vertical discharge)
# ==========================================================================
def bm_blade(theta0, z0, rh, rt, nr=11, nc=7):
    b = bmesh.new()
    grid = []
    for i in range(nr):
        f = i / (nr - 1)
        r = rh + (rt - rh) * f
        chord = 0.12 + 0.16 * f - 0.10 * f ** 9             # airfoil widening outboard, rounded tip
        beta = math.radians(40 - 18 * f)
        sweep = 0.30 * f ** 1.8
        row = []
        for j in range(nc):
            c = j / (nc - 1) - 0.5
            th = theta0 - sweep + c * chord * math.cos(beta) / r
            z = z0 - c * chord * math.sin(beta) + 0.016 * math.cos(math.pi * c)
            row.append(b.verts.new((r * math.cos(th), r * math.sin(th), z)))
        grid.append(row)
    for i in range(nr - 1):
        for j in range(nc - 1):
            b.faces.new([grid[i][j], grid[i][j + 1], grid[i + 1][j + 1], grid[i + 1][j]])
    bmesh.ops.solidify(b, geom=list(b.faces), thickness=0.005)
    return finish(b)


def build_fan(idx, xc, yc):
    e = bpy.data.objects.new(f"Fan_{idx}", None)
    e.empty_display_type = "CIRCLE"
    e.empty_display_size = 0.45
    COLL.objects.link(e)
    e.location = P(xc, yc, CASING_TOP)
    e["display_name"] = f"Condenser fan {idx}"

    # Flared discharge ring (deck top = local z 0, top lip at 96").
    ri, rtop, hr = 16.75 * IN, 19.4 * IN, (FAN_TOP - CASING_TOP) * IN
    prof = [(ri, -3.5 * IN), (ri, 0.0), (ri + 0.6 * IN, hr * 0.45), (ri + 1.6 * IN, hr * 0.8),
            (rtop - 0.4 * IN, hr - 0.2 * IN), (rtop, hr), (rtop + 0.2 * IN, hr - 0.35 * IN),
            (rtop - 0.4 * IN, hr - 0.45 * IN), (ri + 1.7 * IN, hr * 0.8 - 0.15 * IN),
            (ri + 0.75 * IN, hr * 0.45 - 0.15 * IN), (ri + 0.15 * IN, 0.0), (ri + 0.15 * IN, -3.5 * IN)]
    rg = Part(f"Fan_{idx}_Discharge_Ring", f"Fan {idx} discharge ring")
    rg.lathe(prof, (0, 0, 0), "z", "ring", 72, closed=True)
    rg.lathe([(ri + 0.15 * IN, -0.5 * IN), (17.6 * IN, -0.5 * IN), (17.6 * IN, 0.0),
              (ri + 0.15 * IN, 0.0)], (0, 0, 0), "z", "ring", 72, closed=True)       # mounting flange
    rg_ob = rg.build(origin=(0, 0, 0))

    # Rotor: aluminum hub + 3 glass-fiber-reinforced polypropylene blades (p.4, p.55).
    ro = Part(f"Fan_{idx}_Rotor", f"Fan {idx} rotor (3-blade)")
    zb = 0.3 * IN
    ro.lathe([(0, zb - 0.06), (0.075, zb - 0.06), (0.10, zb - 0.035), (0.10, zb + 0.03),
              (0.07, zb + 0.055), (0, zb + 0.06)], (0, 0, 0), "z", "hub", 36)
    for k in range(3):
        ro.merge(bm_blade(2 * math.pi * k / 3, zb, 0.095, 16.2 * IN), "blade")
    ro_ob = ro.build(origin=(0, 0, 0))

    # TEAO motor below the hub, carried by 4 arms bolted to the ring.
    mo = Part(f"Fan_{idx}_Motor", f"Fan {idx} motor (TEAO, 2 hp)")
    mo.lathe([(0, -0.30), (0.075, -0.30), (0.095, -0.28), (0.095, -0.10), (0.05, -0.075),
              (0.05, -0.065), (0, -0.065)], (0, 0, 0), "z", "motor", 32)
    for k in range(10):
        a = 2 * math.pi * k / 10
        mo.box((0.006, 0.012, 0.15), (0.098 * math.cos(a), 0.098 * math.sin(a), -0.19), "motor",
               rot=(0, 0, a))
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        mo.pipe([Vector((0.09 * math.cos(a), 0.09 * math.sin(a), -0.16)),
                 Vector(((ri - 0.003) * math.cos(a), (ri - 0.003) * math.sin(a), -0.07))], 0.011, "motor", 8)
    mo_ob = mo.build(origin=(0, 0, 0))

    # Heavy-gauge coated wire guard on the ring lip.
    gu = Part(f"Fan_{idx}_Guard", f"Fan {idx} wire guard")
    zg = hr - 0.006
    rings = [0.07, 0.13, 0.19, 0.25, 0.31, 0.37, 0.43, rtop - 0.004]
    for r in rings:
        gu.torus(r, 0.0035, (0, 0, zg), "z", "guard", 72 if r > 0.25 else 40, 6)
    for k in range(18):
        a = 2 * math.pi * k / 18
        gu.pipe([(0.045 * math.cos(a), 0.045 * math.sin(a), zg + 0.005),
                 ((rtop - 0.004) * math.cos(a), (rtop - 0.004) * math.sin(a), zg + 0.005)],
                0.003, "guard", 6, caps=False)
    gu.cyl(0.055, 0.01, (0, 0, zg - 0.003), "z", "guard", 24)
    gu_ob = gu.build(origin=(0, 0, 0))

    for ch in (rg_ob, ro_ob, mo_ob, gu_ob):
        ch.parent = e

    # Demo animation: one revolution per FAN_FRAMES; all rotors share one NLA clip.
    phase = (idx * 0.83) % (2 * math.pi)
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
    act.name = f"Fan_{idx}_Spin"
    track = ro_ob.animation_data.nla_tracks.new()
    track.name = "Fans_Spin"
    track.strips.new("Fans_Spin", 0, act)
    ro_ob.animation_data.action = None
    return e


def build_fans():
    fans = []
    idx = 1
    for xc in BAY_C:
        for yc in FAN_Y:
            fans.append(build_fan(idx, xc, yc))
            idx += 1
    return fans


# ==========================================================================
# P06  SCROLL COMPRESSORS (6x, 2 trios) + tandem mounting rails
# ==========================================================================
def build_compressor(name, display, x):
    p = Part(name, display)
    y = COMP_Y
    R = 6.75
    ibox(p, (x - 5.5, y - 5.5, 7.5), (x + 5.5, y + 5.5, 8.1), "comp", bevel=0.2)      # base plate
    for dx, dy in ((-4.4, -4.4), (4.4, -4.4), (-4.4, 4.4), (4.4, 4.4)):
        icyl(p, 0.7, 0.6, (x + dx, y + dy, 6.9), "z", "gasket", 16)                 # grommets
    prof = [(0, 8.0), (R - 0.6, 8.0), (R, 8.6), (R, 27.6), (R + 0.35, 27.9), (R + 0.35, 28.6),
            (R, 28.9), (R - 0.2, 30.5), (R - 1.0, 32.4), (R - 2.6, 33.9), (R - 4.6, 34.6), (0, 34.8)]
    ilathe(p, prof, (x, y, 0), "z", "comp", 48)
    itorus(p, R + 0.05, 0.35, (x, y, 10.5), "z", "gasket", 48, 6)                     # crankcase heater
    icyl(p, 0.75, 1.6, (x, y, 34.4), "z", "steel", 20)                                # discharge stub
    icyl(p, 1.05, 2.0, (x, y - R + 0.4, 16.0), "-y", "steel", 20)                     # suction stub
    ibox(p, (x - 2.2, y + R - 0.4, 21.0), (x + 2.2, y + R + 3.0, 27.0), "comp", bevel=0.3)  # terminal box
    ibox(p, (x - 1.9, y + R + 2.9, 21.3), (x + 1.9, y + R + 3.3, 26.7), "steel", bevel=0.15)
    icyl(p, 0.5, 0.5, (x - R + 0.2, y, 11.5), "-x", "brass", 16)                      # oil sight glass
    icyl(p, 0.35, 0.8, (x + R - 0.3, y - 1.5, 11.5), "x", "copper", 12)               # oil equalizer
    return p.build()


def build_compressors():
    objs = []
    names = ["SYS1_1", "SYS1_2", "SYS1_3", "SYS2_1", "SYS2_2", "SYS2_3"]
    for nm, x in zip(names, COMP_X):
        sysn, k = nm[3], nm[-1]
        objs.append(build_compressor(f"Compressor_{nm}", f"Scroll compressor - system {sysn}, #{k}", x))
    rails = Part("Compressor_Rails", "Compressor tandem rails")
    for xs in (COMP_X[:3], COMP_X[3:]):
        for y in (COMP_Y - 4.4, COMP_Y + 4.4):
            ibox(rails, (xs[0] - 7.5, y - 1.0, BASE_H), (xs[-1] + 7.5, y + 1.0, 6.9), "galv")
    objs.append(rails.build())
    return objs


# ==========================================================================
# P07  DX COOLER (evaporator) with 8" grooved water connections
# ==========================================================================
def build_cooler():
    objs = []
    cy, cz = COOLER_AX
    xa, xb = COOLER_X
    sh = Part("Cooler_Shell", "DX cooler shell (insulated)")
    ilathe(sh, [(0, 0), (8.25, 0), (8.25, xb - xa), (0, xb - xa)], (xa, cy, cz), "x", "insul", 64)
    for k in range(1, 8):                                                       # insulation seams
        itorus(sh, 8.27, 0.12, (xa + k * (xb - xa) / 8, cy, cz), "x", "insul", 64, 6)
    for x in (27.0, 96.0):                                                      # support plates
        ibox(sh, (x - 0.25, cy - 11.5, BASE_H), (x + 0.25, cy + 11.5, cz + 11.5), "frame", bevel=0.1)
        ibox(sh, (x - 2.5, cy - 11.5, BASE_H), (x + 2.5, cy + 11.5, BASE_H + 0.4), "frame")
    icyl(sh, 0.6, 1.0, (60.0, cy, cz + 8.0), "z", "brass", 12)                  # vent
    icyl(sh, 0.6, 1.0, (60.0, cy, cz - 9.0), "z", "brass", 12)                  # drain
    objs.append(sh.build())

    hd = Part("Cooler_Heads", "Cooler heads (return & refrigerant)")
    for x0, x1, d in ((xa - 1.0, xa, -1), (xb, xb + 1.0, 1)):                    # tube-sheet flanges
        icyl(hd, 11.5, 1.0, (x0, cy, cz), "x", "cooler", 64)
        for k in range(16):
            a = 2 * math.pi * k / 16
            icyl(hd, 0.45, 2.4, (x0 - 0.7, cy + 10.4 * math.cos(a), cz + 10.4 * math.sin(a)), "x", "steel", 10)
    ilathe(hd, [(0, 0), (10.0, 0), (9.6, -1.6), (8.0, -3.4), (5.0, -4.6), (0, -5.0)],
           (xa - 1.0, cy, cz), "x", "cooler", 48)                               # return head
    ilathe(hd, [(0, 0), (10.0, 0), (10.0, 3.0), (0, 3.0)], (xb + 1.0, cy, cz), "x", "cooler", 48)
    objs.append(hd.build())

    for nm, disp, x, tag in (("Water_Outlet_Nozzle", "8\" chilled-water OUTLET (supply)", NOZZLE_X[0], "blue_tag"),
                             ("Water_Inlet_Nozzle", "8\" chilled-water INLET (return)", NOZZLE_X[1], "green_tag")):
        n = Part(nm, disp)
        ro, ri = 4.3125, 3.98                                                   # 8" sch 40 OD 8.625"
        ln = (cy - 8.0) - NOZZLE_OUT
        prof = [(ri, 0), (ro, 0), (ro, ln - 1.0), (ro - 0.2, ln - 1.0), (ro - 0.2, ln - 0.6),
                (ro, ln - 0.6), (ro, ln), (ri, ln)]
        ilathe(n, prof, (x, cy - 8.0, cz), "-y", "galv", 48, closed=True)
        ilathe(n, [(ro + 0.03, 0), (ro + 0.15, 0), (ro + 0.15, 2.0), (ro + 0.03, 2.0)],
               (x, cy - 10.5, cz), "-y", tag, 48, closed=True)
        icyl(n, 0.45, 1.8, (x, cy - 11.5, cz + ro - 0.3), "z", "brass", 12)      # thermistor well
        objs.append(n.build())
    return objs


# ==========================================================================
# P08  REFRIGERANT PIPING (2 systems)
# ==========================================================================
def build_piping(sysn):
    p = Part(f"Refrigerant_System_{sysn}", f"Refrigerant piping - system {sysn}")
    xs = COMP_X[:3] if sysn == 1 else COMP_X[3:]
    cy, cz = COOLER_AX
    xh = COOLER_X[1] + 4.0                                     # refrigerant head face
    hdr_y, hdr_z = 58.0, 33.0
    # Suction (insulated): cooler head -> header -> each compressor.
    if sysn == 1:
        ys, xr = cy + 5.8, 114.5
        run = [(xh, ys, cz + 5.0), (xr, ys, cz + 5.0), (xr, ys, hdr_z), (xr, hdr_y, hdr_z), (xs[0] - 3, hdr_y, hdr_z)]
    else:
        ys, xr = cy - 5.8, 118.0
        run = [(xh, ys, cz + 5.0), (xr, ys, cz + 5.0), (xr, ys, hdr_z), (xr, hdr_y, hdr_z), (xs[-1] + 3, hdr_y, hdr_z)]
    ipipe(p, run, 1.55, "insul", 18, bend=3.5)
    for x in xs:
        ipipe(p, [(x, hdr_y, hdr_z), (x, hdr_y, 16.0), (x, COMP_Y - 6.75 - 1.6, 16.0)], 1.05, "insul", 16, bend=2.5)
        icyl(p, 1.5, 1.2, (x, COMP_Y - 6.75 - 1.6, 16.0), "y", "brass", 20)    # rotalock valve
    # Discharge: compressor tops -> manifold -> riser -> rear-coil hot-gas header.
    zd = 36.3
    xr2 = 66.0 if sysn == 1 else 115.0
    for x in xs:
        ipipe(p, [(x, COMP_Y, 35.8), (x, COMP_Y, zd)], 0.7, "copper", 12)
    ipipe(p, [(xs[0], COMP_Y, zd), (xs[-1], COMP_Y, zd)], 0.8, "copper", 14)
    xe = xs[-1] if sysn == 1 else xs[0]
    zh = 44.0 if sysn == 1 else 47.0
    ipipe(p, [(xe, COMP_Y, zd), (xr2, COMP_Y, zd), (xr2, 80.0, zd), (xr2, 80.0, zh)], 0.8, "copper", 14, bend=2.0)
    xa_, xb_ = (BAY_X[0] + 3, BAY_X[2] - 3) if sysn == 1 else (BAY_X[2] + 3, BAY_X[4] - 3)
    ipipe(p, [(xa_, 80.0, zh), (xb_, 80.0, zh)], 0.8, "copper", 14)
    for i in ((0, 1) if sysn == 1 else (2, 3)):
        ipipe(p, [(BAY_C[i], 80.0, zh), (BAY_C[i], W_IN - 0.75 - COIL_DEPTH - 0.2, zh)], 0.5, "copper", 10)
    # Liquid: front-coil collector -> drier / sight glass / solenoid -> TXV -> cooler.
    if sysn == 1:
        xl, zc, yp, zp, xc0, xc1 = 121.0, 43.0, cy + 3.7, cz - 4.6, BAY_X[0] + 3, 121.0
    else:
        xl, zc, yp, zp, xc0, xc1 = 124.0, 46.0, cy - 3.7, cz - 8.1, BAY_X[2] + 3, BAY_X[4] - 3
    ipipe(p, [(xc0, 6.0, zc), (xc1, 6.0, zc)], 0.6, "copper", 12)
    for i in ((0, 1) if sysn == 1 else (2, 3)):
        ipipe(p, [(BAY_C[i], 6.0, zc), (BAY_C[i], 0.75 + COIL_DEPTH + 0.2, zc)], 0.45, "copper", 10)
    ipipe(p, [(xl, 6.0, zc), (xl, 6.0, zp), (xl, yp, zp), (xh, yp, zp)], 0.45, "copper", 12, bend=1.5)
    icyl(p, 1.6, 9.0, (xl, 6.0, 25.0), "z", "steel", 24)                        # filter-drier
    icyl(p, 0.75, 1.0, (xl - 0.3, 6.0, 21.5), "-x", "brass", 16)                 # sight glass
    ibox(p, (xl - 1.0, 5.0, 16.5), (xl + 1.0, 7.0, 18.5), "brass", bevel=0.15)   # solenoid valve
    icyl(p, 1.0, 2.2, (xl, 6.0, 18.5), "z", "gasket", 20)                        # solenoid coil
    ibox(p, (xh + 1.0, yp - 1.0, zp - 1.0), (xh + 3.0, yp + 1.0, zp + 1.0), "brass", bevel=0.2)  # TXV
    icyl(p, 1.2, 0.8, (xh + 2.0, yp, zp + 1.0), "z", "brass", 24)               # TXV power head
    # Oil equalizer line along the trio.
    ipipe(p, [(xs[0] + 6.5, COMP_Y - 1.5, 11.5), (xs[-1] + 6.5, COMP_Y - 1.5, 11.5)], 0.35, "copper", 10)
    return p.build()


# ==========================================================================
# Assemble
# ==========================================================================
SPEC = {
    "model": "YCAL0134",
    "source": "YORK Engineering Guide Form 150.62-EG1 (406), pp. 55, 68-69",
    "nominal_tons_R22": 130.3,
    "nominal_tons_R407C": 124.3,
    "refrigerant_circuits": 2,
    "compressors": "6 hermetic scroll (3 per circuit)",
    "condenser_fans": "8, 3-blade, 2 hp, 1140 rpm",
    "total_airflow_cfm": 106400,
    "condenser_face_area_ft2": 222.0,
    "evaporator": "Direct expansion, 15 in x 8 ft",
    "water_connections_in": 8,
    "operating_weight_lb_al_fin": 10167,
}


def assemble():
    make_textures()
    make_materials()
    parts = [
        part("P01", "Base_Frame", "Base Frame", "Structure",
             "Heavy-gauge galvanized steel frame with baked-on powder paint: formed-steel base rails "
             "with 3\" x 3\" rigging holes, corner and bay posts, divider and top rails, side bracing.",
             build_base_frame()),
        part("P02", "Control_Power_Panel", "Control & Power Panel", "Electrical",
             "End-mounted panel. Millennium control center (2-line x 20-character LCD, colour-coded "
             "12-button keypad, unit ON/OFF switch) and power panel with compressor contactors and "
             "lockable disconnect handles; liquid-tight conduit to the compressors.",
             build_control_panel(), explode=(-1.0, 0, 0)),
        part("P03", "Condenser_Coils", "Condenser Coils", "Heat Transfer",
             "Fin-and-tube condenser coils: seamless internally-enhanced copper tubes in staggered "
             "rows (3 rows, 13 fins per inch), aluminum fins, integral subcooling.",
             build_coils()),
        part("P04", "Casing_Fan_Deck", "Casing & Fan Deck", "Enclosure",
             "Powder-coated fan deck with top fascia and the coil-section end panels.",
             build_casing(), explode=(0, 0, 1.4)),
        part("P05", "Condenser_Fans", "Condenser Fans", "Air Moving",
             "8 direct-drive fans for vertical air discharge: aluminum hub, glass-fiber-reinforced "
             "polypropylene 3-blade airfoil, TEAO motor and heavy-gauge coated steel guard.",
             build_fans(), explode=(0, 0, 2.2)),
        part("P06", "Compressors", "Scroll Compressors", "Refrigeration",
             "Six suction-gas-cooled hermetic scroll compressors, three per refrigerant system, "
             "with crankcase heaters, on tandem rails and rubber grommets.",
             build_compressors(), explode=(0, 1.5, 0)),
        part("P07", "DX_Cooler", "DX Cooler (Evaporator)", "Heat Transfer",
             "Direct-expansion shell-and-tube cooler, 15\" x 8', with 3/4\" closed-cell insulation, "
             "removable heads and 8\" grooved (Victaulic) water connections.",
             build_cooler(), explode=(0, -1.5, 0)),
        part("P08", "Refrigerant_Piping", "Refrigerant Piping", "Refrigeration",
             "Suction, discharge and liquid lines for both systems, with filter-driers, sight glasses, "
             "liquid-line solenoid valves and thermal expansion valves.",
             [build_piping(1), build_piping(2)], explode=(0.6, 0, 0.6)),
    ]
    # Per-child explode offsets (Blender meters): side coils open out, nozzles pull away, doors swing.
    for i in range(N_BAYS):
        for sname, v in (("Front", (0, -1.1, 0)), ("Rear", (0, 1.1, 0))):
            ob = bpy.data.objects[f"Coil_{sname}_Bay_{i + 1}"]
            ob["explode"] = to_gltf(v)
            ob["explode_blender"] = list(v)
    for name, v in (("Water_Outlet_Nozzle", (0, -0.45, 0)), ("Water_Inlet_Nozzle", (0, -0.45, 0)),
                    ("Cooler_Heads", (0.35, 0, 0)), ("Control_Panel_Door", (-0.3, 0, 0)),
                    ("Power_Panel_Door", (-0.3, 0, 0)), ("Compressor_Rails", (0, 0, 0))):
        ob = bpy.data.objects[name]
        ob["explode"] = to_gltf(v)
        ob["explode_blender"] = list(v)

    lo, hi = world_bbox(parts)
    root = group("YCAL0134_Chiller", parts, at=(0, 0, 0))
    dims = hi - lo
    root["display_name"] = "YORK YCAL0134 Air-Cooled Scroll Chiller"
    root["units"] = "meters"
    root["length_mm"] = round(dims.x * 1000)
    root["width_mm"] = round(dims.y * 1000)
    root["height_mm"] = round(dims.z * 1000)
    root["length_in"] = round(dims.x / IN, 2)
    root["width_in"] = round(dims.y / IN, 2)
    root["height_in"] = round(dims.z / IN, 2)
    for k, v in SPEC.items():
        root[k] = v
    root["note"] = ("Presentation model built from the published submittal dimensions. "
                    "Internal layout is representative.")
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

    shot("01_hero.png", (-6.4, -5.6, 3.5), (0.15, 0, 1.05), 38)
    shot("02_panel_end.png", (-4.9, -1.9, 1.75), (-2.45, 0.05, 1.25), 45)
    shot("03_machinery.png", (-0.2, -4.1, 0.75), (-0.2, 0.3, 0.55), 30)
    shot("05_fans_closeup.png", (-0.9, -2.6, 3.7), (0.2, 0.3, 2.35), 40)
    moved = []
    for ob in bpy.data.objects:
        if "explode_blender" in ob.keys():
            v = Vector(ob["explode_blender"])
            if v.length > 0:
                ob.location += v
                moved.append((ob, v))
    shot("04_exploded.png", (-8.0, -8.6, 6.0), (0.0, 0, 1.5), 34)
    for ob, v in moved:
        ob.location -= v


def main():
    root, dims = assemble()
    os.makedirs(OUT, exist_ok=True)
    glb = os.path.join(OUT, GLB_NAME)
    export_glb(glb)
    print(f"GLB written: {glb}  ({os.path.getsize(glb) / 1e6:.2f} MB)")
    print(f"Overall L x W x H: {dims.x:.3f} x {dims.y:.3f} x {dims.z:.3f} m  "
          f"({dims.x / IN:.2f} x {dims.y / IN:.2f} x {dims.z / IN:.2f} in)")
    tris = sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
               for o in bpy.data.objects if o.type == "MESH")
    print(f"Triangles: {tris:,}")
    if DO_RENDER:
        do_renders()
    for img in bpy.data.images:
        if img.source == "FILE":
            img.pack()
    blend = os.path.join(HERE, "york_ycal0134_chiller.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend, compress=True)
    print("Blend written:", blend)


main()
