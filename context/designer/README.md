# EDA-MCP Designer Context

This is an operational specification for an AI agent that designs, inspects, and simulates circuits through EDA-MCP. It is not a user tutorial and it does not prescribe one circuit-design method. Apply engineering judgment: choose an appropriate topology, analysis, execution mode, and amount of explanation from the user's objective, supplied constraints, and available tool capabilities.

## Fast-agent execution contract

Apply these defaults before consulting the detailed guides:

1. Read the live tool schema; do not invent tool actions or parameters.
2. Inspect an existing cell before editing it; never overwrite a cell without explicit authorization.
3. Create both logical net connections and physical schematic wires.
4. Require an observed `schCheck` result of `(0 0)` before claiming schematic completion.
5. Export the structural netlist, then verify its output path and subcircuit pin order.
6. When the Eldo wrapper flow is needed, preserve the original export and create its documented `M`→`X` simulation copy; never encode that transformation into schematic instance names.
7. Build `tb_<cell>.cir` in WorkBoard (use `write_to_file` without `ArtifactMetadata` for workspace files, or write `.txt` and `mv` to `.cir`), include process corner, and run Eldo from testbench—not raw `.net`.
8. Retrieve artifacts through WorkBoard and report assumptions with results.
9. After an `assisted_run` timeout, do not resend the mutating command: the cell state is unknown. Recover, inspect, and continue from observed state.
10. For layout creation, never use plain `geOpen` (Layout L). Bind connectivity reference to schematic (`lxSetConnRef`) and open in `"Layout XL"` application tier (`deOpen`).
11. In Calibre DRC stream-out (`strmout`), always pass the official PDK layer map (`DK_cmos065lpgp_.../cmos065.layermap`) to avoid the `R_forbidden.1` trap (Layer 15 vs 31). Exclude density checks (`group_unselect density`) for isolated leaf cells.

## Authority, scope, and judgment

- Treat [`mcp_tools_spec.md`](mcp_tools_spec.md) and the live MCP tool schema as the interface contract. If they disagree, use the live schema and report the documentation drift only when reporting is authorized.
- `MCP` is the default library for generated cellviews, testbenches, and layouts. A user-supplied library is an explicit override.
- Do not invent tool actions, host tools, PDK APIs, file paths, model files, or simulation results. Inspect or ask for the missing fact.
- Use confirmation when a material design choice is unspecified, an operation overwrites an existing artifact, a modal GUI action needs human input, or the user has asked to review before execution. Do not introduce confirmation gates for an already-specified and authorized task.
- Use reasoning where it adds value: derive initial sizing, choose analyses and measurements, inspect diagnostics, and revise the design based on evidence. Do not substitute generic templates for electrical reasoning.

## Non-negotiable correctness constraints

1. **Session ownership** — Use `virtuoso(action="run_terminal_command")` for Virtuoso-shell commands and `eldo(action="run_terminal_command")` for Eldo-shell commands. Use `remote_control` only for its own remote-shell/read/write operations; its environment is separate.
2. **Remote artifacts** — Do not create remote files through shell redirection or shell file-creation commands. For reviewable simulation decks and downloaded artifacts, use WorkBoard. `remote_control(action="write_file")` is permitted only when the task explicitly requires direct remote file I/O and WorkBoard is unsuitable.
3. **Schematic validity** — Logical net membership alone is insufficient for this PDK. Create physical schematic wires that touch the intended instance and pin terminals, then inspect `schCheck` output. Do not claim a clean schematic unless the observed result is `(0 0)`.
4. **MOS lifecycle and units** — For `cmos065` MOS instances, initialize CDF through `initMosTransistor(inst wMicrons lMicrons)` (or the documented DK lifecycle). Pass width and length as micron strings, for example `"2.0"` and `"0.065"`.
5. **GUI lifecycle (Window-First Execution)** — In `assisted_run`, ALWAYS open the Virtuoso GUI window FIRST before placing instances or drawing wires (`win = geOpen(?lib "MCP" ?cell "<cellName>" ?view "schematic" ?viewType "schematic" ?mode "a")`, `cv = geGetWindowCellView(win)`), then perform all instantiation, wiring, CDF initialization, `schCheck(cv)`, and `dbSave(cv)` directly in that visible window. Do not call `dbClose(cv)` when leaving that view displayed. In a headless standalone flow, close database views after saving.
6. **Netlisting** — Never use the obsolete `hnlInit` / `hnlNetlist` template. Export the structural netlist from the Virtuoso schematic using a verified CDL exporter; see [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md). A simulation deck may be authored locally, but it must include the exported structural netlist rather than duplicating transistor connectivity by hand.
7. **Simulation integrity** — Treat Level-1 MOS models only as explicitly labelled sanity checks. Include server process corner decks at `/modelfile_65nm/` (e.g. `.include "/modelfile_65nm/typNtypP.cir"`, `minNminP.cir`, `maxNmaxP.cir`) for PDK-accurate simulation results. Process corner decks at `/modelfile_65nm/` are static, pre-verified server assets; do NOT execute `remote_control` commands (`read_file`, `ls`, `cat`) to check, inspect, or verify these corner files prior to simulation.
8. **SKILL file output** — Before closing an `outfile` stream, call `drain(fileId)`.
9. **Side effects** — Creating GitHub issues is external and persistent. Use `report_issue` only with explicit user authorization or a stated project policy that authorizes autonomous reporting; first search for a duplicate.
10. **Python code inspection prohibited** — While executing circuit design tasks or invoking MCP tools, NEVER inspect or read `.py` Python codebase files. All operational context MUST be loaded from `.md` documentation files. If any context or detail is missing, ask the user directly rather than reading Python source code.
11. **Minimal server exploration & discrepancy reporting** — Assume the context provided in `.md` specification files is correct and complete; do NOT wander around the remote server executing unnecessary exploration commands (`ls`, `find`, `cat`, etc.). If you encounter an unexpected error or genuine documentation ambiguity, running direct bash commands via `remote_control` to diagnose the server state is permitted as a last resort, but is not recommended. If you must use `remote_control` for diagnosis:
    - **Notify the user immediately** describing the specific error or discrepancy you are encountering.
    - **Post-task reporting**: Upon completing the primary task, once the root cause of the discrepancy is understood, you MUST use `report_issue` to open a GitHub issue detailing the context discrepancy so documentation can be updated for future agents.
12. **Layout XL connectivity binding** — Do not edit layouts as disjoint polygons. Bind layout views to the source schematic via `lxSetConnRef` and verify zero mismatches with `lxCheckAgainstSource`. During Generate From Source (GFS), retarget pins to Metal 1 (`"M1" "pin"`, $0.2\,\mu\text{m} \times 0.2\,\mu\text{m}$) using `lxSetNetPinSpecs` and generate centered pin labels.
13. **Calibre layer mapping & SVRF deck** — Never stream out GDSII without `-layerMap`. Do not redefine `DRC RESULTS DATABASE` or `DRC SUMMARY REPORT` in `drc.svrf`; the foundry deck already defines them.

## Context routing

Read the smallest relevant guide before acting. If the host does not provide a tool named `view_file`, read the linked file through its normal filesystem/resource mechanism; absence of that host-specific tool is not a reason to stop.

| Intent | Read first |
| --- | --- |
| Design or edit a schematic | [`schematic_flow.md`](schematic_flow.md), then [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md) |
| Create, place, route, or optimize layout | [`layout_xl_flow.md`](layout_xl_flow.md) |
| Run Calibre DRC or debug DRC violations | [`calibre_drc_flow.md`](calibre_drc_flow.md) |
| Invoke Virtuoso or write SKILL | [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md) |
| Run Eldo or inspect waveforms | [`eldo_simulation_guide.md`](eldo_simulation_guide.md) |
| Transfer or version artifacts | [`workboard_sync_guide.md`](workboard_sync_guide.md) |
| Report a bug or enhancement | [`issue_reporting_guide.md`](issue_reporting_guide.md) |
| Determine any tool arguments or actions | [`mcp_tools_spec.md`](mcp_tools_spec.md) |

## Artifact workflow

1. Determine whether existing artifacts can be reused and whether the user has specified enough design intent.
2. Build or update the schematic, using physical wires and a clean `schCheck` result as the completion criterion.
3. Export a structural netlist with the verified Virtuoso CDL flow.
4. Create the simulation deck locally inside a WorkBoard, inspect it, export it, simulate it, and retrieve the resulting text/binary outputs for analysis.
5. Report measurements, assumptions, limitations, and any verification evidence. When results contradict intent, diagnose and iterate rather than asserting success.

## Guide index

- [`schematic_flow.md`](schematic_flow.md): judgment-driven design and validation workflow.
- [`layout_xl_flow.md`](layout_xl_flow.md): Layout XL launch, GFS pin specs, placement, routing, engineering fixes, and LVS verification.
- [`calibre_drc_flow.md`](calibre_drc_flow.md): Calibre DRC headless/GUI execution, layer mapping rules, real-time Virtuoso viewport debugging, and WorkBoard sync.
- [`mcp_tools_spec.md`](mcp_tools_spec.md): tool arguments, action modes, defaults, and side effects.
- [`virtuoso_skill_guide.md`](virtuoso_skill_guide.md): PDK-aware SKILL, wiring, CDF, GUI, and verified netlist export guidance.
- [`eldo_simulation_guide.md`](eldo_simulation_guide.md): structural-netlist simulation and results handling.
- [`workboard_sync_guide.md`](workboard_sync_guide.md): local artifact placement and synchronization semantics.
- [`issue_reporting_guide.md`](issue_reporting_guide.md): authorized, deduplicated issue reporting.
