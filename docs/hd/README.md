<a id="hd-documentation"></a>

# HD documentation index

Use this index to choose the owning guide before searching the historical
logs. The [Clash project overview](https://github.com/lisu188/clash-disassembly/blob/main/docs/CLASH_PROJECTS.md)
explains the boundaries between binary patching, recovered engine source and
save tooling.

## Entry points and authority

| Document | Owns |
| --- | --- |
| [Root README](../../README.md) | Project scope, installation entry point and stable default |
| [AGENTS.md](../../AGENTS.md) | Contributor rules, runtime authorization, evidence and disk policy |
| [Working with this repo](WORKING_WITH_THIS_REPO.md) | Short operating guide; AGENTS.md takes precedence |
| [Development and verification](DEVELOPMENT.md) | Python setup, check selection and report-writing behavior |
| [Launcher](LAUNCHER.md) | User workflow, profiles, preparation and packaging |
| [Current handoff](AGENT_HANDOFF.md) | Active work, dated observations and unresolved acceptance gaps |
| [Release runbook](FINISH_LINE_RUNBOOK.md) and [complete-HD evidence](COMPLETE_HD_EVIDENCE.md) | Candidate-bound release requirements and verifier contracts |

The handoff owns changing status. Topic guides own implementation details and
commands. Reports and captures retain the evidence for their exact revision,
candidate, resolution and environment. The
[progress log](HD_MOD_PROGRESS.md) and
[patch notes](CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md) preserve chronology; their
older instructions do not override the handoff. Ignored `.codex-loop/` notes and
[the archived autonomous prompt](AUTONOMOUS_HD_MOD_CODEX_PROMPT.md) are historical
material.

## Launcher and candidate recipes

| Topic | Guides |
| --- | --- |
| Launcher controls and display planning | [Launcher](LAUNCHER.md), [UI](LAUNCHER_UI.md), [resolution support](MULTIRESOLUTION.md) |
| Classic wide-menu extension | [Classic menu routing](CLASSIC_MENU_LAUNCHER.md) |
| Framed adventure map | [Framed launcher](FRAMED_LAUNCHER.md), [four-sided frame](FOUR_SIDED_FRAME.md) |
| Integrated Complete HD | [Candidate builder](COMPLETE_HD_CANDIDATE.md), [foundation provenance](HD_FOUNDATION_IMPORT.md) |
| Modal widgets | [Launcher profile](MODAL_WIDGET_LAUNCHER.md), [candidate](MODAL_WIDGET_CANDIDATE.md), [bounds](MODAL_WIDGET_BOUNDS.md), [runtime](MODAL_WIDGET_RUNTIME.md) |
| Separate expanded battle experiment | [Tactical battle](TACTICAL_BATTLE_HD.md), [edge controls](BATTLE_HD_EDGE_CONTROLS.md), [validation report](../../reports/battle_hd_1280_validation.md) |

## Rendering and input

| Area | Start with |
| --- | --- |
| Initial and partial painting | [Initial paint](INITIAL_MAP_PAINT.md), [partial tiles](PARTIAL_TILE_RENDERING.md), [full-paint diagnostic](FULL_PAINT_PROGRESS_DIAGNOSTIC.md) |
| Camera, bounds and small worlds | [Camera clamps](FRAMED_CAMERA_CLAMP.md), [bounded painting](FRAMED_BOUNDED_PAINT.md), [bounded input](FRAMED_BOUNDED_INPUT.md), [small-world integration](SMALL_WORLD_INPUT.md), [world clearing](FRAMED_WORLD_CLEAR_AUDIT.md) |
| Minimap | [Viewport](MINIMAP_VIEWPORT.md), [scroll validation](MINIMAP_SCROLL_VALIDATION.md) |
| Army panel and controlled input | [Composition](ARMY_PANEL_COMPOSITION.md), [selection](UNIT_SELECTION_HD.md), [transition routes](ARMY_TRANSITION_ROUTES.md), [complete-HD army input](COMPLETE_HD_ARMY_INPUT.md) |
| Ordinary input and castle admission | [Native runtime driver](ORDINARY_MAP_RUNTIME.md), [measured input planner](ORDINARY_MAP_INPUT_PLAN.md), [paused observations](ORDINARY_MAP_OBSERVATION.md), [castle admission](ORDINARY_CASTLE_ENTRY.md), [admission matrix](ORDINARY_CASTLE_ENTRY_MATRIX.md) |
| Native modal canvas and slot copies | [Canvas](FRAMED_MODAL_CANVAS.md), [slot diagnosis](FRAMED_MODAL_SLOTS_DIAGNOSIS.md), [barracks capture](MODAL_SLOTS_BARRACKS_CAPTURE.md), [lifecycle](MODAL_SLOTS_LIFECYCLE.md) |
| Modal primary composition and text | [Composition](MODAL_PRIMARY_COMPOSITION.md), [capture](MODAL_PRIMARY_CAPTURE.md), [checkpoint ledger](MODAL_PRIMARY_CHECKPOINT_LEDGER.md), [text](MODAL_PRIMARY_TEXT.md), [widget text observer](MODAL_WIDGET_TEXT_OBSERVER.md) |
| Remaining modal routes | [Screen validation](FRAMED_SCREEN_VALIDATION.md), [castle routes](FRAMED_CASTLE_REMAINING_ROUTES.md), [remaining screens](FRAMED_REMAINING_SCREEN_ROUTES.md) |

## Evidence and release work

| Work | Guide |
| --- | --- |
| Offline source/image fixtures | [Offline validation](FRAMED_OFFLINE_VALIDATION.md) |
| Hidden complete-HD execution | [Hidden harness](COMPLETE_HD_HIDDEN_HARNESS.md), [gameplay evidence](COMPLETE_HD_GAMEPLAY_EVIDENCE.md) |
| Visible diagnostics and human proof | [Visible harness](VISIBLE_INPUT_HARNESS.md), [human observation plan](COMPLETE_HD_HUMAN_OBSERVATION_PLAN.md), [manual attachment](COMPLETE_HD_MANUAL_ATTACHMENT.md) |
| Save/load and day continuity | [Continuity diagnostic](CONTINUITY_DAY_DIAGNOSTIC.md) |
| Endurance and release eligibility | [Soak roadmap](HD_SOAK_TEST_ROADMAP.md), [release runbook](FINISH_LINE_RUNBOOK.md), [complete-HD evidence](COMPLETE_HD_EVIDENCE.md) |
| Evidence storage and availability | [Captures](../../captures/README.md), [reports](../../reports/README.md), [portable fixtures](../../cloud/README.md) |
| Script, probe and tool locations | [Scripts](../../scripts/README.md), [probes](../../probes/README.md), [tools](../../tools/README.md) |

Before replaying evidence, check its raw files and pinned producer/evaluator
sources. A retained summary does not recreate missing captures. A passing
synthetic fixture, controlled native call or hidden capture does not establish
ordinary input, final visible composition or promotion.

## Maintaining documentation

Update the owning guide when behavior changes and link it from the handoff
when it affects active work. Add a dated report for new observations rather
than rewriting an earlier failure. Keep setup commands in the development
guide and current defaults in the launcher registry; use links elsewhere to
avoid competing copies. Run the documentation fixtures and guards described
in [DEVELOPMENT.md](DEVELOPMENT.md), check local links, and review the diff.
