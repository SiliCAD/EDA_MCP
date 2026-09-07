# Cadence Virtuoso Layout XL Design Flow

This guide establishes the operational specification for generating, placing, routing, optimizing, and verifying physical layouts in **Cadence Virtuoso Layout XL (VXL)** within the `cmos065` ($65\text{nm}$) PDK.

---

## 1. Fast-Agent Layout XL Execution Contract

1. **Never use basic Layout L (`geOpen`)**: Calling `geOpen` opens Layout L, which is purely polygonal and lacks schematic connectivity binding or cross-probing. Always use the 3-step `Layout XL` launch procedure (`lxSetConnRef` $\rightarrow$ `deOpen` in `"Layout XL"`).
2. **The `deOpen` Return Type Trap**: `deOpen` returns a **Window ID** (e.g. `window:19`), **NOT** a database cellview pointer (`db:0x...`). You MUST extract `layCV = geGetWindowCellView(win)` and call `hiSetCurrentWindow(win)` before passing `layCV` into database functions.
3. **Dynamic Terminal Extraction for GFS**: Never hardcode pin lists or use `dbFindOpenCellView`. Open the schematic with `dbOpenCellViewByType(..., "r")`, extract `schNets = schCV~>terminals~>name`, and retarget pins to Metal 1 (`"M1" "pin"`, width/height $0.2\,\mu\text{m}$) using `lxSetNetPinSpecs`.
4. **Mandatory Underlying `M1 drawing` for `M1.PIN.CAD.1`**: GFS creates shapes on `("M1" "pin")`. Foundry rule `M1.PIN.CAD.1` strictly requires an underlying `("M1" "drawing")` polygon bound to the net (`dbAddFigToNet`) under every pin figure.
5. **OpenAccess Standard Via Definitions**: Never instantiate contact cells via `dbCreateInstByMasterName(..., "M1_PO")`—this triggers PDK DK popup warnings that block the FIFO pipe. Always use OpenAccess standard via definitions via `techFindViaDefByName` and `dbCreateVia`.
6. **Continuous Tap Straps & Dual-Tap Rule**: Minimal standalone tap vias enclose only $0.0225\,\mu\text{m}^2$, violating `OD.A.1` ($\ge 0.054\,\mu\text{m}^2$) and `NP.A.1` ($\ge 0.122\,\mu\text{m}^2$). Always place tap vias inside continuous diffusion/implant straps ($W \ge 0.5\,\mu\text{m}$). Always instantiate BOTH an N-well tap (`M1__NW` on `VDD`) and a P-substrate tap (`M1__PT` on `VSS`) within $30\,\mu\text{m}$ to satisfy latch-up rule `LUP.D.1_LUP.D.2`.
7. **Manufacturing Grid Snapping ($5\,\text{nm}$)**: All geometry coordinates must be snapped to $0.005\,\mu\text{m}$ to prevent `OFFGRID` markers in Virtuoso and `GEN.4` violations in Calibre.
8. **Layout-to-Schematic Verification Gate**: A layout is only considered complete when `lxCheckAgainstSource(schCV layCV)` reports 0 mismatches and `layCV~>markers` is `nil`.

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
;; CRITICAL: deOpen returns a Window ID object (e.g. window:19), NOT a database pointer!
win = deOpen(list(nil ?lib "MCP" ?cell "<cell>" ?view "layout") nil "a" "Layout XL")
layCV = geGetWindowCellView(win)
hiSetCurrentWindow(win)
```

### Verification
Run `lxGetConnRef(layCV)` on the open layout view. It must return:
```lisp
("CELLVIEW" "MCP" "<cell>" "schematic" "")
```

---

## 3. How to Generate From Source (GFS)

Layout XL provides a programmatic generation lifecycle API. Always load the schematic view robustly and query its terminals dynamically:

```lisp
;; 1. Safely open schematic database pointer (avoids dbFindOpenCellView returning nil)
schCV = dbOpenCellViewByType("MCP" "<cell>" "schematic" "schematic" "r")
layCV = geGetWindowCellView(hiGetCurrentWindow())

;; 2. Dynamically extract all interface pin nets (generalizes to any cell topology)
schNets = schCV~>terminals~>name

;; 3. Start generation session
lxGenerateStart(schCV layCV)

;; 4. Retarget pins to Metal 1 (M1) with valid dimensions (0.2um x 0.2um)
;; Prevents default 60nm unlabelled PO pins which fail pin CAD enclosure checks
lxSetNetPinSpecs(?nets schNets ?lpp '("M1" "pin") ?width 0.2 ?height 0.2)

;; 5. Finish generation
lxGenerateFinish(schCV layCV)

;; 6. Mandatory post-GFS fix for M1.PIN.CAD.1 compliance:
;; lxSetNetPinSpecs creates shapes on ("M1" "pin"). Foundry rule M1.PIN.CAD.1 strictly
;; requires an underlying ("M1" "drawing") rectangle of equal/larger size bound to the net:
foreach(term layCV~>terminals
  foreach(pin term~>pins
    let((fig rect)
      fig = pin~>fig
      when(fig
        rect = dbCreateRect(layCV list("M1" "drawing") fig~>bBox)
        dbAddFigToNet(rect term~>net)
      )
    )
  )
)

;; 7. Create visible text labels centered on each pin figure
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
| **Tap Via Minimum Area Violations** | Standalone tap via cuts enclose only $0.0225\,\mu\text{m}^2$, violating `OD.A.1` ($\ge 0.054\,\mu\text{m}^2$) and `NP.A.1` ($\ge 0.122\,\mu\text{m}^2$). | Draw continuous horizontal diffusion (`OD`) and implant (`NP`/`PP`) straps ($W \ge 0.5\,\mu\text{m}$) along power rails enclosing tap vias. |
| **Latch-Up Dual-Tap Missing** | Omitting substrate tap on `VSS` or well tap on `VDD` within $30\,\mu\text{m}$ triggers `LUP.D.1_LUP.D.2`. | Always instantiate BOTH an N-well tap (`M1__NW` on `VDD`) and a P-substrate tap (`M1__PT` on `VSS`). |
| **Floating Power Pins** | VDD/VSS are placed as small floating squares without distribution rails. | Create continuous top horizontal M1 `VDD` rail with N-well tap and bottom horizontal M1 `VSS` rail with substrate tap. |

### Standard Via Creation Pattern (Bypassing PDK Popups)

```lisp
tf = techGetTechFile(layCV)

;; M1 to Poly Contact
vd_po = techFindViaDefByName(tf "M1__PO")
dbCreateVia(layCV vd_po list(x_poly y_poly) "R0")

;; M1 to N-Well Tap (VDD) - place inside continuous OD & NW strap
vd_nw = techFindViaDefByName(tf "M1__NW")
dbCreateVia(layCV vd_nw list(x_tap_n y_tap_n) "R0")

;; M1 to P-Substrate Tap (VSS) - place inside continuous OD & PT strap
vd_pt = techFindViaDefByName(tf "M1__PT")
dbCreateVia(layCV vd_pt list(x_tap_p y_tap_p) "R0")
```

### Manufacturing Grid Snapping ($5\,\text{nm}$)

In `cmos065`, the manufacturing grid is strictly $0.005\,\mu\text{m}$ ($5\,\text{nm}$). Any un-snapped coordinate triggers `OFFGRID` markers in Virtuoso and `GEN.4` DRC errors in Calibre. Use this helper when calculating coordinates:

```lisp
procedure(snapGrid(val @optional (grid 0.005))
  round(val / grid) * grid
)
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
