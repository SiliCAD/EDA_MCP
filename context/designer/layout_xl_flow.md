# Cadence Virtuoso Layout XL Design Flow

This guide establishes the operational specification for generating, placing, routing, optimizing, and verifying physical layouts in **Cadence Virtuoso Layout XL (VXL)** within the `cmos065` ($65\text{nm}$) PDK.

---

## 1. Fast-Agent Layout XL Execution Contract

1. **Never use basic Layout L (`geOpen`)**: Calling `geOpen` opens Layout L, which is purely polygonal and lacks schematic connectivity binding or cross-probing. Always use the 3-step `Layout XL` launch procedure (`lxSetConnRef` $\rightarrow$ `deOpen` in `"Layout XL"`).
2. **Window-First Assisted Run**: In `assisted_run`, ensure the Layout XL canvas window is opened FIRST so all component placement, routing, and pin generation are visually visible in the open window.
3. **M1 Pin Specification during GFS**: When running Generate From Source (`lxGenerateStart`/`lxGenerateFinish`), always retarget pins to Metal 1 (`"M1" "pin"`, width/height $0.2\,\mu\text{m}$) using `lxSetNetPinSpecs` to prevent default $60\text{nm}$ unlabelled poly pins.
4. **Via Creation Rule**: Never instantiate contact cells via `dbCreateInstByMasterName(..., "M1_PO")`—this triggers PDK DK popup warnings. Always use OpenAccess standard via definitions via `techFindViaDefByName` and `dbCreateVia`.
5. **Layout-to-Schematic Verification**: A layout is only considered complete when `lxCheckAgainstSource(schCV layCV)` reports 0 mismatches and `layCV~>markers` is `nil`.

---

## 2. How to Launch Cadence Layout XL

Standard `geOpen(?lib ... ?cell ... ?view "layout" ?viewType "maskLayout")` opens basic **Layout L**, operating without connectivity binding or schematic cross-probing.

To open in **Layout XL (VXL)** with active schematic correspondence:

```lisp
;; 1. Ensure empty layout cellview exists in database
cvLay = dbOpenCellViewByType("MCP" "<cell>" "layout" "maskLayout" "a")
dbSave(cvLay)
dbClose(cvLay)

;; 2. Bind XL database connectivity reference to source schematic
lxSetConnRef("MCP" "<cell>" "layout" "CELLVIEW" ?schLib "MCP" ?schCell "<cell>" ?schView "schematic")

;; 3. Open cellview in Layout XL application tier
deOpen(list(nil ?lib "MCP" ?cell "<cell>" ?view "layout") nil "a" "Layout XL")
```

### Verification
Run `lxGetConnRef(layCV)` on the open layout view. It must return:
```lisp
("CELLVIEW" "MCP" "<cell>" "schematic" "")
```

---

## 3. How to Generate From Source (GFS)

Layout XL provides a programmatic generation lifecycle API:

```lisp
schCV = dbFindOpenCellView(ddGetObj("MCP") "<cell>" "schematic")
layCV = geGetWindowCellView(hiGetCurrentWindow())

;; 1. Start generation session
lxGenerateStart(schCV layCV)

;; 2. Crucial: retarget pins to Metal 1 (M1) with valid dimensions
;; Avoids default 60nm unlabelled PO pins which fail pin CAD enclosure checks
lxSetNetPinSpecs(?nets '("IN" "OUT" "VDD" "VSS") ?lpp '("M1" "pin") ?width 0.2 ?height 0.2)

;; 3. Finish generation
lxGenerateFinish(schCV layCV)

;; 4. Create visible text labels centered on each pin figure
;; Ensures terminals are visually identifiable in the Virtuoso canvas
procedure(createPinLabel(layCV netName pt)
  dbCreateLabel(layCV list("M1" "pin") pt netName "centerCenter" "R0" "roman" 0.05)
)
```

---

## 4. How to Auto-Place (Layout XL Placer)

Cadence Layout XL provides native analog and digital placement engines:

```lisp
;; 1. Place Like Schematic: Stacks PMOS pull-up on top and NMOS pull-down on bottom
nclAnalogQuickPlaceLikeSchemCB()

;; 2. Adjust Cell Pins: Relocates interface pins from negative scratch space to cell boundaries
;; nearest to their corresponding device terminals
nclAnalogAdjCellPins()

;; 3. Quick Placement alternative
nclAnalogQuickPlace()
```

---

## 5. How to Auto-Route (Virtuoso Space-based Router - VSR)

The Virtuoso Space-based Router (VSR) detail router can be invoked directly through SKILL:

```lisp
(_iaAutomaticExecuteCmd 'autoRoute 'all)
```

VSR runs rip-up cycles, places metal tracks, and inserts contact cuts automatically according to PDK design rules.

---

## 6. Identified Shortcomings of Native Auto-Tools & Engineering Fixes

Native placement and routing tools frequently produce non-optimal analog geometry, excessive parasitic resistance/capacitance, and DRC violations. Agents must apply targeted engineering optimizations:

| Native Auto Problem | Root Cause | Engineering Optimization Fix |
| :--- | :--- | :--- |
| **Transistor Misalignment** | Placer places PMOS at $X = 0.435\,\mu\text{m}$ and NMOS at $X = 0.305\,\mu\text{m}$ ($0.13\,\mu\text{m}$ offset). | Align both devices along the exact same vertical centerline ($X = 1.2\,\mu\text{m}$) using `dbMoveFig`. |
| **Circuitous Net OUT Routing** | Misaligned drains force VSR to route a giant U-turn loop out to $X = 2.2\,\mu\text{m}$, creating high parasitic $R$ and $C$. | Replace with a single straight vertical Metal 1 bar directly between drains, tapping directly right to pin `OUT`. |
| **Layer Hops & Redundant Vias** | VSR adds 5 vias and hops into Metal 2 to connect gate poly. | Replace with a continuous straight vertical Poly line (`PO drawing`). Metal 2 usage is reduced to zero. |
| **Unauthorized Via Instance Popup** | Instantiating contact cells via `dbCreateInstByMasterName(..., "M1_PO")` triggers PDK DesignKit popup warnings. | Use OpenAccess standard via definitions: `vd = techFindViaDefByName(tf "M1__PO")`, then `dbCreateVia(layCv vd pt "R0")`. |
| **Floating Power Pins** | VDD/VSS are placed as small floating squares without distribution rails. | Create continuous top horizontal M1 `VDD` rail with N-well tap (`M1__NW`) and bottom horizontal M1 `VSS` rail with substrate tap (`M1__PT`). |

### Standard Via Creation Pattern (Bypassing PDK Popups)

```lisp
tf = techGetTechFile(layCV)

;; M1 to Poly Contact
vd_po = techFindViaDefByName(tf "M1__PO")
dbCreateVia(layCV vd_po list(x_poly y_poly) "R0")

;; M1 to N-Well Tap (VDD)
vd_nw = techFindViaDefByName(tf "M1__NW")
dbCreateVia(layCV vd_nw list(x_tap_n y_tap_n) "R0")

;; M1 to P-Substrate Tap (VSS)
vd_pt = techFindViaDefByName(tf "M1__PT")
dbCreateVia(layCV vd_pt list(x_tap_p y_tap_p) "R0")
```

---

## 7. Layout-to-Schematic Verification (LVS Check)

Validate full equivalence using the native Layout XL connectivity checker:

```lisp
lxCheckAgainstSource(schCV layCV)
```

### Verification Criteria
A clean layout produces the following output:
- `INFO (LX-1023): Connectivity matches.`
- `INFO (LX-1024): Instance parameters match.`
- `INFO (LX-1026): 0 mismatches between layout and schematic.`
- `layCV~>markers`: `nil` (0 errors, 0 warnings, 0 shorts).

If `layCV~>markers` contains objects, inspect each marker's `marker~>msg` and `marker~>points` to resolve connectivity discrepancies before proceeding to Calibre DRC.
