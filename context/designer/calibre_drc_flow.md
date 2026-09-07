# Calibre Physical Verification (DRC) Flow

This guide establishes the operational reference and execution methodology for running **Siemens Calibre Physical Verification (DRC)** in EDA-MCP, covering headless batch flows, interactive GUI runsets, layer mapping rules, real-time Virtuoso viewport debugging, and WorkBoard synchronization.

---

## 1. Fast-Agent Calibre DRC Execution Contract

1. **Mandatory Layer Map on Stream-Out**: When running `strmout`, ALWAYS pass the official PDK layer map (`/usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065/cmos065.layermap`). Omitting it triggers the `R_forbidden.1` trap on every Metal 1 shape.
2. **Never Redefine SVRF Output Declarations**: The foundry deck `calibredrc` already declares `DRC RESULTS DATABASE` and `DRC SUMMARY REPORT`. Redefining them in `drc.svrf` produces syntax compilation aborts.
3. **Density Rules Exclusion for Leaf Cells**: Chip density checks (`*.DEN.*`) are designed for full chip windows ($20\,\mu\text{m}$ to $150\,\mu\text{m}$). They always fail on isolated standard/leaf cells ($< 10\,\mu\text{m}$) and must be unselected (`group_unselect density`).
4. **Use WorkBoard for Large Reports**: Calibre DRC outputs (`drc_summary` ~150 KB, `drc_results.db` ~650 KB) contain Latin-1 characters (`0xb5` for $\mu\text{m}$). Do not read them over raw SSH streams; sync them locally via WorkBoard.

---

## 2. Calibre DRC Execution Methodologies

### Flow A: Standalone / Headless Batch Flow (Recommended for Agents)

The headless batch flow is fast, deterministic, and avoids GUI popups or display latencies.

#### 1. GDSII Stream-Out (XStream `strmout`)
Stream out the layout cellview to GDSII from the remote shell, explicitly specifying the PDK layer map:

```bash
strmout -library MCP \
        -topCell <cellName> \
        -view layout \
        -strmFile <cellName>.gds \
        -cdslib ~/Desktop/cmos65/cds.lib \
        -layerMap /usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065/cmos065.layermap
```

#### 2. SVRF Control Deck (`drc.svrf`)
Author a minimal wrapper deck. The foundry master deck defines outputs, so only declare layout source and include the rule set:

```svrf
LAYOUT PATH "<cellName>.gds"
LAYOUT PRIMARY "<cellName>"
LAYOUT SYSTEM GDSII
INCLUDE "/usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/CALIBRE_CORE/calibredrc"
```

#### 3. Execution
Run Calibre hierarchical DRC:

```bash
calibre -drc -hier drc.svrf
```

---

### Flow B: Calibre Interactive GUI Flow & Runset Configuration

When executing DRC through Virtuoso's GUI menu (`Calibre -> Run DRC`):

1. **Working Directory**: `~/Desktop/cmos65/drcRunDir/`
2. **Runset File (`runset_drc_global`)**:
   Must include FDI layer map settings and recipe rules to avoid layer mapping corruption and false density errors:
   ```tcl
   *drcRulesFile: $U2TK_CALIBRETKITdrc
   *drcRunDir: /home/vaibhav22555/Desktop/cmos65/drcRunDir
   *drcLayoutPaths: <cellName>.calibre.db
   *drcLayoutPrimary: <cellName>
   *drcLayoutLibrary: MCP
   *drcLayoutView: layout
   *drcLayoutGetFromViewer: 1
   *drcResultsFile: <cellName>.drc.results
   *drcSummaryFile: <cellName>.drc.summary
   *cmnFDILayerMapFile: /usr/local/cmos065_536/DK_cmos065lpgp_7m4x0y2z_2V51V8@5.3.6/DATA/LIB/lib/OpenAccess/cmos065/cmos065.layermap
   *cmnFDICdsLibFile: /home/vaibhav22555/Desktop/cmos65/cds.lib
   *drcUserRecipes: {{Checks selected in the rules file (Modified)} {{group_unselect[1]} all {group_select[1]} rule_file {group_unselect[2]} density}}
   ```
3. **Calibre RVE (Results Viewing Environment)**:
   Loads `<cellName>.drc.results` to display DRC errors in an interactive tree view linked directly to the Virtuoso canvas via IPC socket.

---

## 3. Real-Time Virtuoso Viewport Debugging Loop

AI agents can guide the designer visually through DRC error coordinates directly on the open layout canvas:

```lisp
let((win layCv pts m1)
  win = hiGetCurrentWindow()
  layCv = geGetWindowCellView(win)
  hiSetCurrentWindow(win)

  ;; 1. Focus camera directly on defect coordinates
  hiPan(win list(xCenter yCenter))
  hiZoomRelativeScale(win 2.5)

  ;; 2. Place on-screen highlighted DRC marker
  pts = list(list(x1 y1) list(x2 y1) list(x2 y2) list(x1 y2))
  m1 = dbCreateMarker(layCv "<RuleCheckName>: <Description>" "Calibre DRC" pts)
  hiRedraw(win)

  ;; 3. Apply surgical layout fix (e.g. adjust geometry, widen wire, add tap implant)
  ;; ... surgical fix code ...

  ;; 4. Clean up marker & reset camera
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
| **`R_forbidden.1`** | **The Forbidden Layer Trap**: Omitting `-layerMap` during `strmout` causes Metal 1 drawing to map to GDS Layer 15, DataType 0 (`OD_33_drawing`, forbidden 3.3V oxide). | Always provide the PDK layer map so `M1 drawing` maps to **Layer 31, DataType 0**. |
| **`*.DEN.*`** | **Chip Density Rules**: Evaluates metal/poly density across $20\mu\text{m}$ to $150\mu\text{m}$ windows. In an isolated standard cell ($< 10\mu\text{m}$), density checks fail spuriously. | Unselect density checks for leaf cell runs (`group_unselect density`). |
| **`M1.PIN.CAD.1`** | **Pin CAD Enclosure**: Pins created on `M1 pin` must have an underlying `M1 drawing` rectangle of equal or larger size. | Ensure GFS or manual routing places a full $M1$ drawing polygon under every pin figure. |
| **`PP.EN.3`, `PP.R.2`** | **Field Poly Implant Enclosure**: All poly lines outside active channels must be enclosed by {NP or PP} implants by $\ge 0.150\,\mu\text{m}$. | Extend implant boundaries (`NP drawing` or `PP drawing`) around poly interconnect lines. |
| **`OD.A.1`, `NP.A.1`** | **Diffusion & Tap Minimum Area**: Tap contacts (`M1__NW` / `M1__PT`) must not sit in isolated minimal vias; their active area and implant rectangles must meet minimum island area rules ($0.054\,\mu\text{m}^2$ for OD, $0.122\,\mu\text{m}^2$ for NP). | Draw tap diffusion and implant boxes with dimensions meeting or exceeding minimum area ($W \times L \ge \text{Area}_{\min}$). |
