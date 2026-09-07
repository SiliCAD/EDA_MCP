# Calibre Physical Verification (DRC) Flow

This guide establishes the operational reference and execution methodology for running **Siemens Calibre Physical Verification (DRC)** in EDA-MCP, covering headless batch flows, interactive GUI runsets, layer mapping rules, real-time Virtuoso viewport debugging, and WorkBoard synchronization.

---

## 1. Fast-Agent Calibre DRC Execution Contract

1. **Mandatory Layer Map on Stream-Out**: When running `strmout`, ALWAYS pass the official PDK layer map (`/usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065/cmos065.layermap`) and `-case Preserve`. Omitting the layer map causes Metal 1 drawing to map to Layer 15 (`OD_33_drawing`), triggering the fatal `R_forbidden.1` trap on every M1 polygon.
2. **Batch Mode Density Rule Deactivation**: In `calibredrc`, `#DEFINE DENSITY_CHECK` is active by default. In headless batch mode, your `drc.svrf` wrapper deck MUST declare `DRC UNSELECT CHECK ALL_DENSITY_CHECK` to prevent 12 spurious density violations on leaf cells.
3. **Never Redefine SVRF Output Declarations**: The foundry deck `calibredrc` already declares `DRC RESULTS DATABASE` and `DRC SUMMARY REPORT`. Redefining them in `drc.svrf` produces syntax compilation aborts.
4. **Coordinate Unit Scaling (Nanometers to Microns)**: Calibre ASCII Results Database (`drc_results.db`) outputs polygon vertices in **integer database units (nanometers)**. You MUST divide coordinates by 1000 (`x_um = x_db / 1000.0`) before passing them to Virtuoso SKILL functions (`hiPan`, `dbCreateMarker`).
5. **Manufacturing Grid ($5\,\text{nm}$)**: All shapes must align to the $0.005\,\mu\text{m}$ grid to avoid `GEN.4` off-grid violations.
6. **Use WorkBoard for Large Reports**: Calibre DRC outputs (`drc_summary` ~150 KB, `drc_results.db` ~650 KB) contain Latin-1 characters (`0xb5` for $\mu\text{m}$). Do not read them over raw SSH streams; sync them locally via WorkBoard.

---

## 2. Calibre DRC Execution Methodologies

### Flow A: Standalone / Headless Batch Flow (Recommended for Agents)

The headless batch flow is fast, deterministic, and avoids GUI popups or display latencies.

#### 1. GDSII Stream-Out (XStream `strmout`)
Stream out the layout cellview to GDSII from the remote shell inside the dedicated DRC run directory (`~/Desktop/cmos65/drc_run`), explicitly specifying the PDK layer map and preserving case:

```bash
cd ~/Desktop/cmos65/drc_run && \
strmout -library MCP \
        -topCell <cellName> \
        -view layout \
        -strmFile <cellName>.gds \
        -cdslib ~/Desktop/cmos65/cds.lib \
        -layerMap /usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065/cmos065.layermap \
        -case Preserve
```

#### 2. SVRF Control Deck (`drc.svrf`)
Author a minimal wrapper deck. Only declare layout parameters, include the master deck, and unselect leaf-cell density rules:

```svrf
LAYOUT PATH "<cellName>.gds"
LAYOUT PRIMARY "<cellName>"
LAYOUT SYSTEM GDSII
INCLUDE "/usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/CALIBRE_CORE/calibredrc"

// Mandatory: Unselect chip-level density checks for leaf cell runs
DRC UNSELECT CHECK ALL_DENSITY_CHECK
```

#### 3. Execution
Run Calibre hierarchical DRC:

```bash
cd ~/Desktop/cmos65/drc_run && calibre -drc -hier drc.svrf
```

---

### Flow B: Calibre Interactive GUI Flow & Runset Configuration

When executing DRC through Virtuoso's GUI menu (`Calibre -> Run DRC`):

1. **Working Directory**: `~/Desktop/cmos65/drcRunDir/`
2. **Runset File (`runset_drc_global`)**:
   Must include FDI layer map settings and recipe rules to avoid layer mapping corruption and false density errors (paths match user `$HOME`):
   ```tcl
   *drcRulesFile: $U2TK_CALIBRETKITdrc
   *drcRunDir: $HOME/Desktop/cmos65/drcRunDir
   *drcLayoutPaths: <cellName>.calibre.db
   *drcLayoutPrimary: <cellName>
   *drcLayoutLibrary: MCP
   *drcLayoutView: layout
   *drcLayoutGetFromViewer: 1
   *drcResultsFile: <cellName>.drc.results
   *drcSummaryFile: <cellName>.drc.summary
   *cmnFDILayerMapFile: /usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065/cmos065.layermap
   *cmnFDICdsLibFile: $HOME/Desktop/cmos65/cds.lib
   *drcUserRecipes: {{Checks selected in the rules file (Modified)} {{group_unselect[1]} all {group_select[1]} rule_file {group_unselect[2]} density}}
   ```
3. **Calibre RVE (Results Viewing Environment)**:
   Loads `<cellName>.drc.results` to display DRC errors in an interactive tree view linked directly to the Virtuoso canvas via IPC socket.

---

## 3. Real-Time Virtuoso Viewport Debugging Loop

AI agents can guide the designer visually through DRC error coordinates directly on the open layout canvas.

> [!IMPORTANT]
> **Coordinate Scaling**: Vertices in `drc_results.db` are in **nanometers** (e.g. `1200 2086`). Always divide by **1000.0** to obtain Virtuoso user coordinates in microns (`1.200 2.086`).

```lisp
let((win layCv pts m1 x_um y_um)
  win = hiGetCurrentWindow()
  layCv = geGetWindowCellView(win)
  hiSetCurrentWindow(win)

  ;; 1. Convert nanometer DB coordinates to microns
  x_um = xCenter_nm / 1000.0
  y_um = yCenter_nm / 1000.0

  ;; 2. Focus camera directly on defect coordinates
  hiPan(win list(x_um y_um))
  hiZoomRelativeScale(win 2.5)

  ;; 3. Place on-screen highlighted DRC marker
  pts = list(
    list(x1_nm / 1000.0 y1_nm / 1000.0)
    list(x2_nm / 1000.0 y1_nm / 1000.0)
    list(x2_nm / 1000.0 y2_nm / 1000.0)
    list(x1_nm / 1000.0 y2_nm / 1000.0)
  )
  m1 = dbCreateMarker(layCv "<RuleCheckName>: <Description>" "Calibre DRC" pts)
  hiRedraw(win)

  ;; 4. Apply surgical layout fix (e.g. adjust geometry, widen wire, add tap implant)
  ;; ... surgical fix code ...

  ;; 5. Clean up marker & reset camera
  dbDeleteObject(m1)
  hiZoomAbsoluteScale(win 0.9)
  hiRedraw(win)
  dbSave(layCv)
)
```

---

## 4. WorkBoard Integration for Large Physical Verification Artifacts

Calibre DRC outputs are large (`drc_summary` ~150 KB, `drc_results.db` ~650 KB) and contain Latin-1 characters (e.g., `0xb5` for $\mu\text{m}$), which truncate or error when reading through raw SSH streams.

### WorkBoard Verification Workflow:
1. **Initialize WorkBoard**:
   ```json
   { "action": "initialize", "workboard_name": "<cell>_drc" }
   ```
2. **Fetch Verification Artifacts**:
   ```json
   { "action": "add", "remote_path": "~/Desktop/cmos65/drc_run/drc_summary", "local_path": "drc_summary.txt", "workboard_name": "<cell>_drc" }
   { "action": "add", "remote_path": "~/Desktop/cmos65/drc_run/drc_results.db", "local_path": "drc_results.db", "workboard_name": "<cell>_drc" }
   ```
3. **Local Analysis**:
   Parse exact violation coordinates and rule strings locally using Python or ripgrep without remote latency or pagination limits.
4. **Git Version Tracking**:
   Re-running `workboard(action="pull")` after fixes captures exact Git commit diffs showing violation counts decreasing to zero.

---

## 5. Key Gotchas & Critical Rules in 65nm (`cmos065`)

| Rule Check | Description & Failure Root Cause | Engineering Solution |
| :--- | :--- | :--- |
| **`R_forbidden.1`** | **The Forbidden Layer Trap**: Omitting `-layerMap` during `strmout` causes Metal 1 drawing to map to GDS Layer 15, DataType 0 (`OD_33_drawing`, forbidden 3.3V oxide in LPGP). | Always provide the PDK layer map and `-case Preserve` so `M1 drawing` maps to **Layer 31, DataType 0**. |
| **`*.DEN.*`** | **Chip Density Rules**: Evaluates metal/poly density across $20\mu\text{m}$ to $150\mu\text{m}$ windows. In an isolated standard cell ($< 10\mu\text{m}$), density checks fail spuriously. | Unselect density checks for leaf cell runs via `DRC UNSELECT CHECK ALL_DENSITY_CHECK` in `drc.svrf` or `group_unselect density` in GUI runsets. |
| **`M1.PIN.CAD.1`** | **Pin CAD Enclosure**: Pins created on `M1 pin` must have an underlying `M1 drawing` rectangle of equal or larger size bound to the net. | Ensure GFS post-processing runs `dbCreateRect(..., list("M1" "drawing"), fig~>bBox)` and `dbAddFigToNet`. |
| **`GEN.4` / `OFFGRID`** | **Manufacturing Grid Violation**: Coordinates not divisible by the $0.005\,\mu\text{m}$ ($5\,\text{nm}$) grid cause off-grid errors. | Snap all geometric calculations using `round(coord / 0.005) * 0.005`. |
| **`PP.EN.3`, `PP.R.2`** | **Field Poly Implant Enclosure**: All poly lines outside active channels must be enclosed by {NP or PP} implants by $\ge 0.150\,\mu\text{m}$. | Extend implant boundaries (`NP drawing` or `PP drawing`) around poly interconnect lines. |
| **`OD.A.1`, `NP.A.1`** | **Diffusion & Tap Minimum Area**: Tap contacts (`M1__NW` / `M1__PT`) must not sit in isolated minimal vias; their active area and implant rectangles must meet minimum island area rules ($0.054\,\mu\text{m}^2$ for OD, $0.122\,\mu\text{m}^2$ for NP). | Draw continuous horizontal tap straps along power rails ($W \ge 0.5\,\mu\text{m}$) meeting or exceeding minimum island area. |
| **`LUP.D.1_LUP.D.2`** | **Latch-Up Guarding**: Substrate taps on `VSS` or well taps on `VDD` omitted within $30\,\mu\text{m}$ of transistors trigger latch-up violations. | Always instantiate BOTH an N-well tap on `VDD` and a P-substrate tap on `VSS`. |
