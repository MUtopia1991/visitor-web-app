# YORK YCAL0134 Air-Cooled Scroll Chiller: Interactive 3D Model (GLB)

A presentation model of the **YORK Millennium YCAL0134 (Style C)** 130-ton air-cooled scroll
chiller. It was built in **Blender 5.1** from the manufacturer's published submittal data and
exported as one **GLB** file in which every major component is a **separate, named, clickable node**.

Source document: **YORK Engineering Guide, Form 150.62-EG1 (406)**
* *Physical Data, English Units*: page 55 (YCAL0134 column)
* *Dimensions, YCAL0114–YCAL0134, English*: pages 68–69 (views A-A, B-B, D-D)

![Hero render](renders/01_hero.png)

| Exploded view | Control & power panel |
|---|---|
| ![Exploded](renders/04_exploded.png) | ![Panel](renders/02_panel_end.png) |
| **Machinery section (cooler side)** | **Condenser fans** |
| ![Machinery](renders/03_machinery.png) | ![Fans](renders/05_fans_closeup.png) |

---

## Deliverables

| File | What it is |
|---|---|
| `york_ycal0134_chiller.glb` | **The model.** glTF 2.0 binary, Y-up, meters, PBR materials, embedded textures, fan animation |
| `blender/york_ycal0134_chiller.blend` | Blender source scene (textures packed) with a presentation camera and lights |
| `blender/build_chiller.py` | Parametric build script. All drawing dimensions are inch parameters at the top |
| `viewer/index.html` | Web demo (three.js): click to select, part tree, explode, isolate/hide, fan animation |
| `renders/*.png` | Cycles renders for the presentation deck |

## Drawing compliance (YCAL0114–0134, pages 68–69)

| Dimension | Drawing | Model |
|---|---|---|
| Base / frame length | 183" | 183" |
| Overall length incl. control & power panel | 190" | 190 7/8" to panel face (handles add ~3") |
| Overall width | 88 1/4" | 88 1/4" (+2 3/8" water connections) |
| Top of casing | 91 7/16" | 91 7/16" |
| Top of fan discharge rings | 96" | 96" |
| Machinery section height | 38" | 38" |
| Control/power panel | 50" wide × 29" high, 19 1/8" from side, bottom at 38" | same |
| Water connections | 8" grooved, outlet at 20", inlet 83" further, centerline 17 1/8" high, 2 3/8" beyond the unit edge | same |
| Rigging holes | (4) 3" × 3" each side at 7 7/8" / 67 1/4" spacing | same |
| Compressors (view D-D) | 6 scroll compressors in two trios along the rear side | same |
| Fans | 8 (4 bays × 2) | 8 |

From *Physical Data* (page 55, YCAL0134): 130.3 nominal tons (R-22) / 124.3 (R-407C), 2 refrigerant
systems, 6 scroll compressors (3 per system), 8 fans (3 blades, 2 hp, 1140 rpm, 106,400 CFM),
DX cooler 15" × 8', 8" water connections, operating weight 10,167 lb (aluminum fin coils).
These values are also stored in the GLB root node's metadata.

## Model specification

| | |
|---|---|
| Geometry | ~130k triangles, 8 parts, 70+ named nodes |
| File size | ~5 MB GLB, no Draco (opens in any viewer without a decoder) |
| Units / axes | meters, glTF Y-up; origin = center of the footprint at grade |
| Animation | `Fans_Spin`: one looping clip that turns all 8 fan rotors |

## Part structure (scene graph)

There are 8 top-level parts. Each one is a group node with its **origin at the part's own center**,
so it can be moved, exploded or animated as a unit. Sub-parts are child meshes.

```
YCAL0134_Chiller                              (root; spec data in extras)
├── P01_Base_Frame           Base Frame                  Structure
│   └── Base_Frame_Structure
├── P02_Control_Power_Panel  Control & Power Panel       Electrical
│   ├── Panel_Enclosure
│   ├── Control_Panel_Door        (2×20 LCD, 12-key keypad, ON/OFF switch)
│   ├── Power_Panel_Door          (2 lockable disconnect handles, labels)
│   └── Power_Conduits            (liquid-tight conduit to the compressors)
├── P03_Condenser_Coils      Condenser Coils             Heat Transfer
│   ├── Coil_Front_Bay_1 … Coil_Front_Bay_4
│   └── Coil_Rear_Bay_1  … Coil_Rear_Bay_4
├── P04_Casing_Fan_Deck      Casing & Fan Deck           Enclosure
│   ├── Fan_Deck
│   └── End_Panels
├── P05_Condenser_Fans       Condenser Fans              Air Moving
│   └── Fan_1 … Fan_8
│       ├── Fan_N_Discharge_Ring
│       ├── Fan_N_Rotor           (animated)
│       ├── Fan_N_Motor
│       └── Fan_N_Guard
├── P06_Compressors          Scroll Compressors          Refrigeration
│   ├── Compressor_SYS1_1 … Compressor_SYS1_3
│   ├── Compressor_SYS2_1 … Compressor_SYS2_3
│   └── Compressor_Rails
├── P07_DX_Cooler            DX Cooler (Evaporator)      Heat Transfer
│   ├── Cooler_Shell
│   ├── Cooler_Heads
│   ├── Water_Outlet_Nozzle       (blue band = supply)
│   └── Water_Inlet_Nozzle        (green band = return)
└── P08_Refrigerant_Piping   Refrigerant Piping          Refrigeration
    ├── Refrigerant_System_1
    └── Refrigerant_System_2
```

Node names use only `A–Z a–z 0–9 _`, so three.js, Babylon.js, Unity and Unreal import them unchanged.

### Metadata on every part (glTF `extras`)

In three.js this is available as `object.userData`:

```json
{
  "part_id": "P06",
  "display_name": "Scroll Compressors",
  "category": "Refrigeration",
  "description": "Six suction-gas-cooled hermetic scroll compressors, three per refrigerant system, ...",
  "explode": [0, 0, -1.5]
}
```

* `description` is a starting text written from the catalog wording. Replace it with your own,
  either in Blender (Object Properties → Custom Properties) or in `assemble()` in the build script.
* `explode` is an offset in glTF coordinates (meters) for an exploded view. Child nodes can carry
  their own offset; for example, the front and rear coils open outward to opposite sides.

## Using it in a web page (three.js)

```js
const gltf = await new GLTFLoader().loadAsync('york_ycal0134_chiller.glb');
scene.add(gltf.scene);

// Click → walk up to the part node that carries part_id
const hit = raycaster.intersectObject(gltf.scene, true)[0];
let part = hit?.object;
while (part && !part.userData.part_id) part = part.parent;
console.log(part.userData.part_id, part.userData.display_name, part.userData.description);

// Exploded view (t = 0…1)
gltf.scene.traverse(o => {
  if (o.userData.explode) {
    o.userData.home ??= o.position.clone();
    o.position.copy(o.userData.home).add(new THREE.Vector3(...o.userData.explode).multiplyScalar(t));
  }
});

// Fans
const mixer = new THREE.AnimationMixer(gltf.scene);
mixer.clipAction(gltf.animations[0]).play();
```

`viewer/index.html` is a complete working example. Serve the folder over HTTP, because browsers
block `file://` model loading:

```bash
cd chiller-3d-demo && npx serve .     # then open http://localhost:3000/viewer/
```

## Rebuilding / other YCAL sizes

All dimensions are inch parameters at the top of `blender/build_chiller.py`, named after the
drawing callouts. Other sizes in the same guide (for example YCAL0070–0104 on pages 62–67) use the
same construction with fewer bays, fans and compressors. Adjust `L_IN`, `N_BAYS`, `COMP_X` and the
cooler values, then run:

```bash
blender -b -P blender/build_chiller.py -- --render     # GLB + .blend + renders
blender -b -P blender/build_chiller.py --              # GLB + .blend only (~10 s)
```

## Notes

* The exterior envelope and the positions of the panel, water connections, compressors, rigging
  holes and fans follow the submittal drawing. Internal routing (refrigerant piping, conduit,
  coil headers) is representative, because the guide does not detail it.
* The condenser is modeled as the vertical side coils shown in the side view. The catalog lists
  222 ft² of total face area, so the real coil arrangement includes more surface than the side
  faces alone.
* No manufacturer logos are reproduced. The nameplate and LCD show generic demo text.
