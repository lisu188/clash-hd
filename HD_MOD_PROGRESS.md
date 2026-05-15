# Clash95 HD Mod Progress

## 2026-04-22

Current milestone: stabilize reproducible HD testing and mouse evidence before
continuing deeper viewport patches.

### Repository Cleanup

- Removed tracked repository-root `.exe` artifacts, including the copied base
  executable and old patched candidates.
- Added `/*.exe` to `.gitignore` so local candidates are not staged by accident.
- Verified the user-owned original remains at `C:\Clash\clash95.exe` with SHA:
  `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`.

### Current Patch Direction

- Keep `gameplay-menu640-centered-map12-novswitch-relinput` as the recommended
  stage until a mouse fix is proven by CDB logs and frame/click evidence.
- Treat nonexclusive, absolute-format, absolute-assignment, and hybrid mouse
  stages as diagnostics only.
- Prefer wrapper-first or message-coordinate input experiments over promoting
  unproven DirectInput byte patches.

### Evidence Notes

- `tools/wiki_lint.py` passed using bundled Python.
- `git diff --check` passed with only line-ending warnings.
- Tool discovery found x86 CDB, GFlags, Sysinternals ProcDump/ProcMon/ProcExp,
  x32dbg, Ghidra headless, and dgVoodoo2 x86 DDraw under standard local paths.
- DxWnd is present only as an archive and must be extracted before use.
- Native input produces sane relative deltas under the same CDB sweep.
- HD mouse candidate tests still show mismatch between cursor movement and menu
  hit/click behavior.
- The click-test harness now recovers from `MainWindowHandle` becoming null by
  enumerating visible windows for the target process id.
- Fresh candidate `C:\Clash\clash95_hd_harnesscheck_20260422.exe` was built
  from the verified original using stage
  `gameplay-menu640-centered-map12-novswitch-relinput`; output SHA-256:
  `C246A71A87003B0BDCC7EB997DBE1A5A97E08CC3AA8349DE00A528321EBBD757`.
- Live full-client harness run:
  `captures\clicktest-20260422-163904\results.json`.
- The run captured three cases at `800x600` with no null-handle errors.
  `centered-exit` changed 15.68% of sampled pixels and passed; `shifted-exit`
  and `native-exit` changed 0% and failed without errors.
- Added dependency-free analyzer `tools/capture_geometry.py` and wrote:
  `captures\clicktest-20260422-163904\geometry.json`.
- Analyzer findings for `captures\clicktest-20260422-163904`:
  - all three cases are 800x600 and full-frame nonblack, so border/nonblack
    bounds alone do not prove menu placement;
  - `centered-exit` exact full-frame diff was 5.202%, click-target diff was
    3.506%, and the before-frame hash was unique among sibling cases;
  - `shifted-exit` and `native-exit` had exact 0% diff and stable before/after
    hashes;
  - therefore the current centered pass is not clean hitbox proof yet. It may
    be caused by different intro/menu readiness state.
- Added a pre-click stability/readiness gate to `scripts\smoke\test_clash_menu_click.ps1`.
  It waits for stable pre-click frames, checks coarse menu readiness via
  nonblack coverage and click-target brightness/luma, and emits
  `PreClickStable`, `PreClickReady`, `ClickAttempted`,
  `PreClickNonblackPercent`, `PreClickTargetMeanLuma`, and
  `PreClickTargetBrightPercent`.
- Live validation:
  `captures\clicktest-20260422-182440\results.json` and
  `captures\clicktest-20260422-182440\geometry.json`.
- In that readiness-gated run, centered, shifted, and native exit cases all
  reached a stable 800x600 pre-click frame with `PreClickReady=true`,
  `ClickAttempted=true`, and matching before/after hashes. All three produced
  0% post-click frame change. This makes the current failure a stronger input
  path problem rather than a menu-readiness artifact.
- Ran CDB mouse-state probe:
  `scripts\cdb\run_cdb_menu_probe.ps1 -Exe C:\Clash\clash95_hd_harnesscheck_20260422.exe -Probe probes/cdb/mouse/clash95_mouse_state_probe.cdb -Log C:\Clash\hd-cdb-harnesscheck-mouse-state-20260422.log -MouseSweep`.
- Added dependency-free parser `tools/mouse_probe_summary.py` and wrote:
  `captures\mouseprobe-20260422-183513-summary.json`.
- Mouse-state probe findings:
  - 416 `MOUSE` rows were logged at `sub_460A50`, so DirectInput/game input
    state is not absent;
  - `dx` ranged `0..2220`, `dy` ranged `0..1509`, and displayed `x/y` reached
    `1303,923`;
  - final active menu bounds were `max=(610,452)`;
  - 373 rows were already over bounds before clamp and 39 rows landed exactly
    at final max;
  - button state also toggled (`button_rows=44`, left rows 38, right rows 35).
- Interpretation: the current problem is bad coordinate mode/integration or
  clamp/hit-test alignment, not total input absence. This explains why
  readiness-gated `SendInput` clicks can be attempted yet leave the menu frame
  unchanged.

### Next Step

Trace the runtime source for the game window/client origin, then prototype a
small mouse-coordinate fix that maps DirectInput screen-quarter samples into
client/logical coordinates. Build only a new `C:\Clash` candidate and validate
with the Python click mapper plus the combined CDB probe.

### Combined Mouse/Menu-Hit Probe

- Added `probes/cdb/mouse/clash95_mouse_menu_probe.cdb` to log `sub_460A50` `MOUSE` state and
  `0x00419B80` `MENUHIT` descriptor tests in one run.
- Extended `tools/mouse_probe_summary.py` to parse `MENUHIT` rows, preserve
  row `kind` and `line_no`, and write grouped summaries.
- Validation log:
  `C:\Clash\hd-cdb-harnesscheck-mouse-menu-sample-20260422.log`.
- Summary:
  `captures\mousemenuprobe-20260422-sample-summary.json`.
- Findings:
  - 246 `MOUSE` rows and 598 `MENUHIT` rows were parsed;
  - the 598-row MENUHIT sample came from CDB/MASM treating bare `256` as hex,
    so the probe was corrected to use decimal `0n256` for future runs;
  - `MOUSE` still shows severe overlarge movement (`x` max 12165, `y` max
    6801, `dx` max 28211, `dy` max 19077), with final menu bounds `610x452`;
  - `MENUHIT` sees the cursor pinned at `610,452` for every sampled descriptor;
  - no sampled `MOUSE` or `MENUHIT` row saw left/right button state from the
    synthetic sweep click;
  - the six repeated menu descriptors were `(239,196)`, `(232,228)`,
    `(265,264)`, `(437,196)`, `(424,228)`, and `(468,264)`.
- Interpretation: menu art and descriptor scan are present, but cursor
  integration is wrong before hit testing. The next patch should target
  coordinate acquisition/integration rather than moving menu visuals again.

### Diagnostic Mouse Mapping Follow-up

- Added `gameplay-menu640-centered-map12-deltaclamp` and built
  `C:\Clash\clash95_hd_mouseclamp_20260422.exe`; SHA-256
  `EFD297A641C04484917B5142D8FAB26F0B9806FE35E8AB872FC7525F4A2F37AA`.
  The CDB probe showed this still drives the cursor to the menu edge because
  the incoming samples are positive absolute-style values, not signed relative
  deltas.
- Added `gameplay-menu640-centered-map12-absquarter` and built
  `C:\Clash\clash95_hd_mouseabsq_20260422.exe`; SHA-256
  `AD7D44C0B4C2C2CFA90897A2F1FE64D79F3537301911A6C09383B2D9DC51C074`.
  This is the current best diagnostic candidate, but it is not stable yet.
- Added `tools/mouse_path_probe.py`. It launches or targets a Clash95 process,
  skips the intro with Space pulses, moves through known client points, holds
  optional forced clicks, and records requested client/screen points plus
  actual cursor screen/client positions for every click phase.
- Added `scripts\cdb\run_cdb_python_mouse_map.ps1` to run the Python mapper while CDB logs
  `MOUSE` and `MENUHIT` rows from `probes/cdb/mouse/clash95_mouse_menu_dynamic_probe.cdb`.
- Python-only mapper evidence:
  `captures\mouseclickmap-20260422-absquarter-sendinput-v2.json`.
  It verified exact forced-click geometry at client `(239,196)`, `(320,285)`,
  and `(468,264)`: `max_abs_error=0`, `max_sample_abs_error=0`,
  `path_verified=true`, and `click_path_verified=true`.
- CDB+Python mapper evidence:
  `captures\cdb-python-mouse-map-20260422.log`,
  `captures\mouseclickmap-cdb-python-20260422.json`, and
  `captures\mousemenuprobe-20260422-cdb-python-map-summary.json`.
  Held `SendInput` clicks are visible to DirectInput when held for 250 ms:
  `button_rows=20`, `left_button_rows=20`, and `menuhit_button_rows=10`.
- The same run proves the coordinate root cause. Python recorded actual cursor
  screen `(1119,603)` and client `(239,196)`, while CDB recorded DirectInput
  sample `(280,151)` and in-game logical `(70,37)`. Since `(1119,603) / 4`
  is approximately `(280,151)`, the wrapper/device is feeding quartered screen
  coordinates. The abs-quarter patch divides once more instead of subtracting
  the client origin.
- Next technical target: find a reliable runtime client-origin source, such as
  a `ClientToScreen`/`GetClientRect` caller or existing window globals, then
  transform `DirectInput screen/4` samples to client/logical coordinates.

### DDraw Geometry And Screen-Origin Diagnostic

- Added `probes/cdb/render/clash95_win32_geometry_entry_probe.cdb` to log `USER32!GetClientRect`
  and `USER32!ClientToScreen` callers. The probe log is
  `captures\win32-geometry-entry-probe-20260422.log`.
- Added `probes/cdb/render/clash95_ddraw_geometry_callsite_probe.cdb` to break after the local
  `C:\Clash\DDRAW.dll` wrapper returns from those calls. The probe log is
  `captures\ddraw-geometry-callsite-probe-20260422.log`.
- Geometry proof from the wrapper:
  - `DDRAW_RECT rect=(0,0,800,600) size=(800,600)`;
  - `DDRAW_ORIGIN_A pt=(880,407)`;
  - `DDRAW_BOTTOMRIGHT_A pt=(1680,1007) span=(800,600)`.
- Saved DDraw call-site disassembly in
  `captures\win32-geometry-ddraw-disasm-20260422.log`. Important wrapper
  call sites are `1803fdc4`, `1803fdd2`, `1803fdda`, `1801c4e5`, and
  `1801c4f3`; related wrapper globals include `18162a34`, `18162a44`, and
  `18440e80`.
- Added temporary patch stage
  `gameplay-menu640-centered-map12-screenorigin`. It proves the equation
  `client = DirectInputSample*4 - clientOrigin` using the traced current
  origin `(880,407)`. This is diagnostic only because the origin is
  hard-coded.
- Built `C:\Clash\clash95_hd_mouseorigin_20260422.exe`; SHA-256
  `D4894C339D584A2F542FC06169267F136129D40CFB18527E04A364180A1D4EC8`.
  This aligned nonzero samples but turned zero samples into `(-880,-407)`.
- Updated the diagnostic code cave to skip zero samples and built
  `C:\Clash\clash95_hd_mouseorigin_skip0_20260422.exe`; SHA-256
  `ABBBEF097E1A61E353E064AFFBC893D3576C774506B7A01404D90B5746E39D60`.
- Validation:
  `captures\cdb-python-mouseorigin-skip0-map-20260422.log`,
  `captures\mouseclickmap-cdb-python-mouseorigin-skip0-20260422.json`, and
  `captures\mousemenuprobe-20260422-mouseorigin-skip0-summary.json`.
- Skip-zero diagnostic summary:
  - Python path was exact: `max_abs_error=0`, `max_sample_abs_error=0`;
  - CDB saw `mouse_rows=18`, `menuhit_rows=9`;
  - coordinates stayed in bounds: `preclamp_over_bounds=0`,
    `menuhit_over_bounds=0`;
  - held clicks reached the engine: `button_rows=8`,
    `menuhit_button_rows=4`;
  - mapped values match client points closely, e.g. Python client `(239,196)`
    produced CDB `MOUSE x=240 y=197`, and `(468,264)` produced
    `MOUSE x=468 y=265`.
- Interpretation: the coordinate transform is now proven. The next real fix is
  replacing hard-coded `(880,407)` with a dynamic origin source or moving input
  remapping into the wrapper where the HWND/client rect is already known.

### Dynamic-Origin Mouse Fix

- Updated `probes/cdb/mouse/clash95_hwnd_origin_probe.cdb` to log the actual `CreateWindowExA`
  store at `0x005452DC`. Validation
  `captures\hwnd-origin-probe-createhwnd-20260422.log` confirmed
  `hWnd_create` equals the wrapper HWND while the wrapper reports
  `rect=(0,0,800,600)` and origin `(880,407)`.
- Added `gameplay-menu640-centered-map12-dynorigin` to `patch_clash95_hd.py`.
  The code cave calls the existing `ClientToScreen` import at `0x004EA3E0`,
  using `HWND [0x005452DC]`, then writes
  `((DirectInputSample * 4) - clientOrigin) << 6` into the engine mouse raw
  fields. The latest version skips zero samples and transformed samples outside
  the active bounds to avoid startup/wrapper noise pinning the cursor.
- Built `C:\Clash\clash95_hd_mousedynorigin_20260422.exe`; SHA-256
  `C4EE2D3E66AFCBD6067694201FA38E95B4EAE91B7359A3AF96D7302FB2A20B0F`.
  This proved the live-origin version but still allowed some transient startup
  samples through.
- Built `C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe`; SHA-256
  `E1725A5FCB4E2BA8E7700914FE5F9312670831D3097E92A8CE41F4110D5FC7CF`.
  This is the current best mouse candidate.
- Validation:
  `captures\cdb-python-dynorigin-boundguard-map-20260422.log`,
  `captures\mouseclickmap-cdb-python-dynorigin-boundguard-20260422.json`, and
  `captures\mousemenuprobe-20260422-dynorigin-boundguard-summary.json`.
- Bounds-guarded summary:
  `mouse_rows=40`, `menuhit_rows=21`, `x=0..468`, `y=0..285`,
  `button_rows=19`, `menuhit_button_rows=10`, `preclamp_over_bounds=0`,
  `menuhit_over_bounds=0`, `path_verified=true`, and
  `click_path_verified=true`.
- Added `-ClickHoldMs` and `-ClickRepeat` to `scripts\smoke\test_clash_menu_click.ps1` so
  frame tests can use the same held-click cadence that CDB proves reaches
  DirectInput.
- Non-CDB frame smoke:
  `captures\clicktest-20260422-211114\results.json` reached a stable
  800x600 menu frame and attempted a held centered-exit click, but it did not
  exit. Because CDB proves internal cursor/button alignment, keep this as a
  separate click-target/menu-flow/harness issue.

### HD Map Patch-Stage Verification

- Added `tools/patch_stage_report.py`, a dependency-free verifier for
  `patch_clash95_hd.py` stages. It reports candidate SHA-256, PE image base,
  section-derived RVA/VA values, group counts, per-offset byte status, and a
  compact HD-map summary.
- Command:
  `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\patch_stage_report.py --exe C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe --stage gameplay-menu640-centered-map12-dynorigin --write-json captures\patch-stage-dynorigin-boundguard-20260422.json`
- Result:
  - Candidate SHA-256:
    `E1725A5FCB4E2BA8E7700914FE5F9312670831D3097E92A8CE41F4110D5FC7CF`;
  - `92/92` selected patch bytes matched the stage, with `0` original and
    `0` unexpected selected bytes;
  - map groups matched the intended 12x9 stage: `main-loops` `14/14`,
    `helpers` `25/25`, `input-bounds` `2/2`, and `viewport-init` `2/2`;
  - `viewport-switch` remains unpatched, intentionally preserving the
    menu-safe native switch for this stage.
- Interpretation: the HD-map byte layer is now reproducibly proven for the
  current best candidate. The next evidence must be runtime: enter gameplay,
  log `sub_406FA0` redraw/scroll state, and capture the first adventure-map
  frame to prove the 12x9 view on screen.

### HD Map Runtime Probe

- Added runtime map evidence files:
  `probes/cdb/map/clash95_map_runtime_probe.cdb`, `scripts\cdb\run_cdb_map_probe.ps1`, and
  `tools/map_probe_summary.py`.
- Probe target:
  `C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe`
  (`E1725A5FCB4E2BA8E7700914FE5F9312670831D3097E92A8CE41F4110D5FC7CF`).
- Runtime command:
  `Set-ExecutionPolicy -Scope Process Bypass -Force; & 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\cdb\run_cdb_map_probe.ps1' -Exe 'C:\Clash\clash95_hd_mousedynorigin_boundguard_20260422.exe' -Log 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-map-runtime-loadslot0-v2-20260422.log' -MouseJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\map-runtime-mouse-loadslot0-v2-20260422.json' -Frame 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\map-runtime-frame-loadslot0-v2-20260422.png' -Points '300,218;320,166;400,226' -RunSeconds 12 -ClickHoldMs 300 -ClickRepeat 2 -ClickIntervalMs 900`
- Mouse path evidence:
  `captures\map-runtime-mouse-loadslot0-v2-20260422.json` had
  `path_verified=true`, `click_path_verified=true`, `max_abs_error=0`,
  `max_sample_abs_error=0`, client size `800x600`, origin `(880,407)`.
- CDB log summary command:
  `C:\Users\andrz\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe tools\map_probe_summary.py captures\cdb-map-runtime-loadslot0-v2-20260422.log --patch-report captures\patch-stage-dynorigin-boundguard-20260422.json --write-json captures\map-runtime-loadslot0-v2-summary-20260422.json`
- Runtime result:
  gameplay entered with `PLAYGAME gd=035d0030 map=(50,50) scroll=(39,42)
  player=0 selected=-1 mission=1 turn=34`; the log had `redraw_rows=64` and
  `repaint_rows=64`.
- Tile-bound result:
  expected tiles from the static patch report are `12x9`. The first redraw had
  `scroll=(39,42)`, `end12=(51,51)`, and native `end9=(48,49)`. The analyzer
  now reports `edge_overrun_rows=64`, expected max scroll `(38,41)`, and
  overrun `(1,1)`.
- Crash evidence:
  CDB reported a second-chance access violation at `00403582`
  (`repne movs dword ptr es:[edi],dword ptr [esi]`) after the redraw/repaint
  probe rows. The run timed out before saving a valid first-map frame, and a
  cleanup check showed no remaining `clash95*` or `cdb` processes.
- Disassembly evidence:
  x86 CDB disassembly of the original around `0040B700..0040B7D0` shows
  PlayGame restores saved scroll at `0040B748` and `0040B764`, then continues
  into redraw setup before the patched movement/helper clamps can run.
- Interpretation:
  the 12x9 map loops are active, but existing saved per-player scroll values
  can be legal for native 9x7 and illegal for 12x9 at the right/bottom edge.
  The next proof should be a CDB-time clamp immediately after PlayGame scroll
  restoration before adding a code-cave or byte patch.

### HD Map Clamp And Copy Crash Probe

- Added `probes/cdb/map/clash95_map_runtime_clamp_probe.cdb`.
- Clamp proof:
  `captures\map-runtime-clamp-loadslot0-summary-20260422.json` shows
  `SCROLL_RESTORE before=(39,42) max=(38,41)` and
  `SCROLL_RESTORE_CLAMP after=(38,41)`. The first redraw changed to
  `scroll=(38,41)`, `end12=(50,50)`, and `edge_overrun_rows=0`.
- The crash still occurred after the in-bounds redraws:
  second-chance AV at `00403582`.
- Added `probes/cdb/map/clash95_map_runtime_clamp_crash_probe.cdb` to exit on AV and capture
  context.
- Crash probe evidence:
  `captures\map-runtime-clamp-crash-loadslot0-summary-20260422.json` reports
  `edge_overrun_rows=0`, `last_exception_address=00403582`, and
  `last_write_address=0b3cc1d0`.
- Disassembly identifies `00403582` as the `repne movs dword ptr es:[edi],
  dword ptr [esi]` copy inside `Render_BlendSurfaceRect`. The copy count at
  the fault is 64 bytes.
- The write address is just beyond a 640x480-sized region, so the remaining
  crash is likely a native-sized blit/scratch/clip extent or surface-object
  mismatch rather than the previously proven saved-scroll tile overrun.
- Added diagnostic patch stage
  `gameplay-menu640-centered-map12-dynorigin-sharedscratch`, which includes the
  current dynamic-origin stage plus `shared-surface` while leaving
  `menu-surface` native.
- Built:
  `C:\Clash\clash95_hd_mousedynorigin_sharedscratch_20260422.exe`, SHA-256
  `D2EC22AAE227A432FAA32EFFBA2A254B167F5775D274A1FA4B240F35D5FE7951`.
- Static report:
  `captures\patch-stage-dynorigin-sharedscratch-20260422.json` verified
  `94/94` selected bytes patched, including `shared-surface` `2/2`.
- Sharedscratch runtime result:
  `captures\map-runtime-sharedscratch-clamp-crash-loadslot0-summary-20260422.json`
  still reports `edge_overrun_rows=0`, `last_exception_address=00403582`, and
  write address `0b3bc1d0`.
- Interpretation:
  initial scroll clamp is still required, but it is not the whole HD-map crash
  fix. Growing `unk_51D4C0` alone is also insufficient. The next probe should
  log copy extents at `0040357A` and `00403582` to identify which surface object
  still exposes a native-sized destination.

### HD Map Redraw Copy-Extent Probes

- Added `probes/cdb/map/clash95_map_copy_extent_probe.cdb` and
  `probes/cdb/map/clash95_map_redraw_copy_extent_probe.cdb`.
- Added copy-row parsing and object/vtable aggregation to
  `tools/map_probe_summary.py`.
- Quieted `scripts\cdb\run_cdb_map_probe.ps1` so `tools\mouse_path_probe.py` still writes
  JSON evidence but no longer floods stdout with the full mouse trace.
- Automation note:
  an explicit neutral pre-click at `400,300` is needed before the Load/slot
  clicks because the startup animation can consume the first mouse click.
- Early gated copy probe:
  `captures\map-copy-extent-sharedscratch-skipclick-loadslot0-summary-20260422.json`
  reached `PLAYGAME` and clamp, but arming copy logging at scroll restore spent
  its 512-row budget before map redraw.
- Redraw-gated copy probe:
  `captures\map-redraw-copy-extent-sharedscratch-loadslot0-summary-20260422.json`
  reached `MAP_REDRAW seq=0`, clamped scroll `(38,41)`, `end12=(50,50)`,
  `edge_overrun_rows=0`, and logged 768 copy rows without an AV before the
  deliberate timeout.
- Copy aggregate:
  the first redraw-gated sample group is a single object/vtable
  `objvt=0050ed94`; exec rows were sampled in destination range
  `0b2449d0..0b24bfcc`, mostly 64-byte copies. This is lower than the earlier
  faulting write address near `0b3bc1d0`, so the crash likely happens in a later
  redraw/copy phase rather than the first logged chunk.
- Added `probes/cdb/map/clash95_map_copy_sampler_enabled_probe.cdb`, which keeps the hot
  `00403582` breakpoint disabled until the first `MAP_REDRAW`. This avoids the
  pre-redraw debugger slowdown caused by conditional breakpoints that still trap.
- Sampler evidence:
  `captures\map-copy-sampler-enabled-sharedscratch-loadslot0-summary-20260422.json`
  reached 4 redraw rows and 12 repaint rows, stayed in bounds
  (`edge_overrun_rows=0`), and sampled copy counts through `seq=45056`.
  No AV occurred during the 20-second sampler window.
- Visual evidence:
  `captures\map-copy-sampler-enabled-frame-sharedscratch-loadslot0-20260422.png`
  shows the gameplay map rendered, though the frame is partially occluded by the
  CDB console because screenshot capture grabs the screen region rather than the
  DirectDraw backbuffer.
- Current interpretation:
  the scroll clamp is proven necessary, the 12x9 redraw path can render
  in-bounds for at least several redraw passes, and all sampled map-copy rows
  still use the `0050ed94` render object. The remaining crash needs either a
  longer low-overhead run, a narrower conditional trigger near the high
  destination range, or a patch that routes the specific render object/clip
  extent to the enlarged 800x600 surface.

### HD Map Stream Surface Probe, 2026-04-23

- Static CDB evidence:
  `captures\cdb-static-stream-constructors-20260423.log` shows the
  `0050ed94` stream constructors at `00403EB0` and `00403EF0`. They read
  `word ptr [surface]` as row pitch/width, store it as stream aux at
  `[stream+8]`, and store the destination cursor at `[stream+4]`.
- Crash object detail probe:
  `captures\map-crash-object-detail-sharedscratch-loadslot0-summary-20260423.json`
  reports `ExceptionAddress=00403582`, destination `0b26c1d0`,
  `objvt=0050ed94`, `obj_cursor=0b26c1d0`, and `obj_aux=00000280`.
  The remaining crash was therefore a 640-wide destination stream.
- Added `probes/cdb/map/clash95_map_stream_constructor_probe.cdb`, which enables stream
  constructor logging only after `MAP_REDRAW` to avoid perturbing menu/startup
  timing.
- Sharedscratch stream result:
  `captures\map-stream-constructors-sharedscratch-loadslot0-summary-20260423.json`
  logged 300 stream rows, then reproduced the AV. The primary stream group was
  `surf=028bc3c8`, `size=640x480`, `base=0b210030`,
  `cursor_max=0b250808`; crash write was `0b25c1d0`.
- Added diagnostic patch stage
  `gameplay-menu640-centered-map12-dynorigin-menusurface`, which adds
  `menu-surface` to the existing dynamic-origin sharedscratch map stage.
- Built:
  `C:\Clash\clash95_hd_mousedynorigin_menusurface_20260423.exe`, SHA-256
  `7063B2FD032974D975D82175B8ADC2DC08C3C1A72F97FC86FBB7D8C7A140578B`.
- Static report:
  `captures\patch-stage-dynorigin-menusurface-20260423.json` verified
  `96/96` selected bytes patched, including `menu-surface` `2/2`.
- Runtime result:
  `captures\map-stream-constructors-menusurface-loadslot0-summary-20260423.json`
  reached gameplay, logged 12 redraws, stayed in bounds
  (`edge_overrun_rows=0`), and had `exception_rows=0`.
- Primary stream after the new stage:
  `surf=025fc3c0`, `size=800x600`, `base=0b210030`,
  `cursor_max=0b260988`. This proves the extra `menu-surface` allocation patch
  removes the remaining native 640x480 map-copy destination under the CDB-time
  saved-scroll clamp.
- Mouse/path evidence:
  `captures\map-stream-constructors-mouse-menusurface-loadslot0-20260423.json`
  reports `client_size=[800,600]`, origin `(880,407)`,
  `path_verified=true`, and `click_path_verified=true`.
- Visual caveat:
  `captures\map-stream-constructors-frame-menusurface-loadslot0-20260423.png`
  is 800x600 and shows the map, but it also includes CDB console pixels because
  the current screen capture helper can grab the wrong/occluded region. Fix the
  capture path before treating frame geometry as final visual proof.
- Follow-up:
  the permanent saved-scroll restore clamp below removes the CDB-time edit
  dependency at `0040B76A`.

### Standalone Saved-Scroll Clamp, 2026-04-23

- Static PlayGame disassembly saved in
  `captures\cdb-static-playgame-scroll-restore-20260423.log` identified the
  post-restore call at `0040B76A` as the small permanent hook point.
- Added patch group `saved-scroll-clamp` and stage
  `gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp`.
- Hook:
  file offset `0x00AB6A`, VA `0x0040B76A`, old `E8 E1 20 00 00`, new
  `E9 11 E1 0D 00`.
- Code cave:
  file offset `0x0E8C80`, VA `0x004E9880`. It clamps restored
  `gameData+0x222E8` and `gameData+0x222EC` to
  `max(0,map_width-12)` and `max(0,map_height-9)`, calls original
  `0040D850`, then jumps back to `0040B76F`.
- Built:
  `C:\Clash\clash95_hd_mousedynorigin_menusurface_scrollclamp_20260423.exe`.
- SHA-256:
  `E7BFF85DF851785522206594C1FE904C6FA77EE8EDE6C4687803B0D243714DA0`.
- Static report:
  `captures\patch-stage-dynorigin-menusurface-scrollclamp-20260423.json`
  verified `98/98` selected bytes patched, including `saved-scroll-clamp`
  `2/2`, `menu-surface` `2/2`, `main-loops` `14/14`, and `helpers` `25/25`.
  The map summary now reports `saved_scroll_restore_clamp=true`.
- Static CDB disassembly:
  `captures\cdb-static-scrollclamp-candidate-20260423.log` confirmed the hook
  jumps to `004E9880`, the cave clamps saved scroll, calls `0040D850`, and
  returns to `0040B76F`.
- Added no-edit runtime probe:
  `probes/cdb/map/clash95_map_stream_constructor_patchclamp_probe.cdb`.
- Runtime command:
  `Set-ExecutionPolicy -Scope Process Bypass -Force; & 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\cdb\run_cdb_map_probe.ps1' -Exe 'C:\Clash\clash95_hd_mousedynorigin_menusurface_scrollclamp_20260423.exe' -Probe 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\probes/cdb/map/clash95_map_stream_constructor_patchclamp_probe.cdb' -Log 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-map-stream-constructors-menusurface-scrollclamp-loadslot0-20260423.log' -MouseJson 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\map-stream-constructors-mouse-menusurface-scrollclamp-loadslot0-20260423.json' -Frame 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\map-stream-constructors-frame-menusurface-scrollclamp-loadslot0-20260423.png' -Points '400,300;300,218;320,166;400,226' -RunSeconds 20 -ClickHoldMs 300 -ClickRepeat 2 -ClickIntervalMs 1000`
- Runtime result:
  `captures\map-stream-constructors-menusurface-scrollclamp-loadslot0-summary-20260423.json`
  entered gameplay, restored scroll `(39,42)`, clamped it to `(38,41)`, logged
  12 in-bounds redraw rows, kept `edge_overrun_rows=0`, and had
  `exception_rows=0`.
- Primary stream result:
  `surf=025ac408`, `size=800x600`, `base=0b220030`,
  `cursor_max=0b270988`. This is the first standalone candidate that combines
  the saved-scroll clamp and enlarged map target stream without relying on
  CDB-time memory edits.
- Mouse/path result:
  `captures\map-stream-constructors-mouse-menusurface-scrollclamp-loadslot0-20260423.json`
  reports `client_size=[800,600]`, origin `(880,407)`,
  `path_verified=true`, and `click_path_verified=true`.
- Visual caveat:
  the frame PNG is still screen-capture evidence and may include CDB console
  pixels. The next task is a clean client/backbuffer capture or non-CDB visual
  smoke for the standalone candidate.
- Post-update validation:
  `tools\wiki_lint.py` passed; `patch_clash95_hd.py --help` lists the new
  `gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp` stage;
  `tools\patch_stage_report.py` still reports `98/98` selected bytes patched;
  `tools\map_probe_summary.py` still reports `edge_overrun_rows=0` and
  `exception_rows=0`; `git diff --check` reported only existing CRLF warnings;
  no `cdb` or `clash95*` processes were left running.

### Clean Visual Smoke And Menusurface Regression, 2026-04-23

- Added `scripts\capture\capture_clash_client_frame.ps1`, a DPI-aware capture subprocess that
  raises the Clash window, verifies the client center belongs to the target
  top-level window, captures only the client area, and writes frame metadata.
- Updated `scripts\cdb\run_cdb_map_probe.ps1` and new `scripts\smoke\run_clash_visual_smoke.ps1` to use
  that capture helper. This avoids the earlier CDB/desktop contamination caused
  by screen capture from the wrong coordinate context.
- Important DPI lesson:
  do not make the launcher/mouse-driver process DPI-aware before starting the
  game. That changes the automation/runtime coordinate path. Keep mouse driving
  in the legacy logical coordinate mode and use a separate DPI-aware process
  only for capture.
- Clean non-CDB smoke command:
  `Set-ExecutionPolicy -Scope Process Bypass -Force; & 'C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\scripts\smoke\run_clash_visual_smoke.ps1' -Exe 'C:\Clash\clash95_hd_mousedynorigin_menusurface_scrollclamp_20260423.exe' -RunSeconds 30 -ClickHoldMs 300 -ClickRepeat 2 -ClickIntervalMs 1000`
- Evidence:
  `captures\visual-smoke-20260423-113427\results.json` captured clean target
  frames with `CenterWindowMatchesTarget=true`.
- Result:
  the candidate still reaches the main menu in a clean non-CDB run, but the
  menu is stripey/corrupt. The captured frame
  `captures\visual-smoke-20260423-113427\after-map-path.png` shows the known
  `menu-surface` corruption pattern instead of a usable menu or map.
- Interpretation:
  the permanent scroll clamp is good, but the current
  `gameplay-menu640-centered-map12-dynorigin-menusurface-scrollclamp` candidate
  is not shippable because the `menu-surface` immediates corrupt the fixed
  640x480 main menu. The next patch should make the 0x447DC0/0x447DD6
  menu/game surface allocation remain 640x480 for main-menu rendering and grow
  to 800x600 only for gameplay/map rendering.
- Static hint:
  CDB disassembly around `00447DD6` shows the native branch loads
  `ebx=0x1E0`, `edx=0x280`, then calls `00403D70`. The current `menu-surface`
  patch changes those immediates globally; a smaller stable fix likely needs a
  runtime branch, hook, or later gameplay-only reallocation instead.

### Menu-Safe Map Surface Upgrade Prototype, 2026-04-23

- Added patch group `map-surface-upgrade-scrollclamp` and stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp`.
- The new stage deliberately omits the global `menu-surface` immediate patches.
  Main-menu allocation at `00447DD6` stays 640x480.
- The hook reuses the proven PlayGame point at file offset `0x00AB6A`, VA
  `0x0040B76A`, replacing old `E8 E1 20 00 00` with `E9 11 E1 0D 00`.
- Cave at file offset `0x0E8C80`, VA `0x004E9880` now:
  allocates a new 800x600 `dword_5202E0` surface if the current surface is not
  already 800 wide, stores it after menu dispatch, clamps saved scroll to
  `map_width-12` / `map_height-9`, calls original `0040D850`, then returns to
  `0040B76F`.
- Added `menu-only-center-blit-640only` for this stage. It hooks
  `00401E30` to cave `004E9920` and centers the menu blit only when
  `eax == dword_5202E0` and `word ptr [eax] == 640`. This prevents future
  800-wide map blits from being treated as menu blits.
- Built non-destructive candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_20260423.exe`,
  SHA-256
  `8DA12E7C0C0B06426B657DC199E573D346ED47D92E401296493A06945A82AC03`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-20260423.json`
  reports `97/97` selected bytes patched, including
  `map-surface-upgrade-scrollclamp` `2/2`,
  `menu-only-center-blit-640only` `2/2`, `main-loops` `14/14`, and
  `helpers` `25/25`.
- Static CDB disassembly:
  `captures\cdb-static-mapsurface-scrollclamp-640blit-caves-20260423.log`
  confirms the `0040B76A` map-surface/scroll cave and the `00401E30` 640-only
  center-blit cave.
- Clean visual smoke:
  `captures\visual-smoke-20260423-121409\results.json` reaches a clean,
  centered menu with `CenterWindowMatchesTarget=true` and enters gameplay.
  The stripey main-menu regression from the global `menu-surface` patch is gone.
- Remaining visual defect:
  `captures\visual-smoke-20260423-121409\after-map-path.png` still shows
  right/bottom gameplay artifacts. Since the stream is now 800x600 and stable,
  this is likely stale/uncleared extra surface area, old 640x480 UI/layout
  assumptions, or incomplete right/bottom redraw coverage rather than the old
  640-wide stream crash.
- No-edit runtime CDB probe:
  `captures\map-stream-constructors-mapsurface-scrollclamp-640blit-loadslot0-summary-20260423.json`
  entered gameplay, clamped restored scroll `(39,42)` to `(38,41)`, logged
  12 in-bounds redraw rows, had `edge_overrun_rows=0`, and had
  `exception_rows=0`.
- Primary map stream in the refined probe:
  `surf=0b6c5500`, `size=800x600`, `base=0b320030`,
  `cursor_max=0b370988`.
- Additional static clue:
  `captures\cdb-static-fullscreen-blit-fill-20260423.log` shows
  `sub_401E30` still uses the legacy 640x480 rectangle
  `(0,0)-(639,479)` when copying/presenting surfaces. Future work should trace
  calls around map present/clear and identify which 640x480 rectangle or UI
  draw path leaves the new right/bottom regions dirty.

## Full Redraw Helper Expansion, 2026-04-23

- Static disassembly of the active candidate showed `sub_418A90` was already
  widened to 12x9, so the remaining dirty map was not caused by the
  single-tile repaint guard.
- The next missing path was `sub_418700`, the full redraw/scroll repaint
  helper. It still used the native shape: 9 columns by 6 full rows plus a
  6-column clipped bottom row.
- Added patch group `full-redraw-12x9` and included it only in
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp`.
- Patched bytes:
  `0x017B70 09->0C` for full redraw columns,
  `0x017B81 06->08` for full redraw rows, and
  `0x017DFF 06->09` for the clipped bottom row columns.
- Rebuilt non-destructive candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_20260423.exe`,
  SHA-256
  `435218DA425C9F3C5E35C9374778FB2E0427C7EB510257A05209086C416A7E87`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-20260423.json`
  reports `100/100` selected bytes patched, including
  `full-redraw-12x9` `3/3`.
- Static CDB:
  `captures\cdb-static-sub418700-fullredraw12-20260423.log` confirms
  `cmp ecx,0Ch`, `cmp edi,8`, and bottom-row `cmp ecx,9`.
- Clean visual smoke:
  `captures\visual-smoke-20260423-135516\results.json` reached gameplay with
  the same SHA. The after-map frame shows visibly improved lower/right map
  coverage, but far-right/top and lower-right UI/minimap-like remnants remain.
- Runtime stream probe:
  `captures\map-stream-constructors-fullredraw12-loadslot0-summary-20260423.json`
  still reports gameplay entry, saved-scroll clamp `(39,42)->(38,41)`,
  an 800x600 primary stream, `edge_overrun_rows=0`, and `exception_rows=0`.
- A follow-up experiment widened `sub_418700` copy/present bounds to
  `799x591`, but it was backed out because the visual smoke harness stopped
  reaching gameplay. Treat that as unproven until a focused CDB probe separates
  harness timing from an actual rendering/input regression.

## Full Redraw Present Bounds, 2026-04-23

- Added `probes/cdb/map/clash95_map_redraw_rect_fullonly_probe.cdb`. It keeps the earlier
  partial-redraw probe intact but disables partial logging so CDB captures the
  full redraw tiles and `Render_FillRect` rectangles without exhausting the log
  budget.
- Against the active 100-patch candidate, the probe proved that
  `sub_418700` now draws 12 full columns and the bottom row on an 800x600 map
  surface:
  - full tiles reached `xy=(736,464)`;
  - bottom tiles reached `xy=(544,528)`;
  - source surface was `dword_5202E0`, `800x600`.
- The same run proved the full-redraw present rectangles were still clipped to
  the native map body:
  - top present `(32,16,607,225)`;
  - right present `(429,225,607,252)`;
  - bottom present `(32,252,607,463)`.
- Added patch group `full-redraw-present-bounds-800` with only six immediate
  patches:
  - `0x017CDE 5F020000->1F030000` top/right present edge `607->799`;
  - `0x017D6C 5F020000->1F030000` right-edge compare `607->799`;
  - `0x017D82 5F020000->1F030000` right strip present edge `607->799`;
  - `0x017D99 CF010000->4F020000` bottom-edge compare `463->591`;
  - `0x017E5E CF010000->4F020000` bottom strip present edge `463->591`;
  - `0x017E68 5F020000->1F030000` bottom strip right edge `607->799`.
- Added diagnostic stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds`
  instead of folding this directly into the stable stage.
- Built non-destructive candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_20260423.exe`,
  SHA-256
  `A4233F396DAFE2D4D5197C96C1EEBB44542271F6CA2461BE43514DCC2BE2F403`.
- Updated `tools/patch_stage_report.py` so the map summary reports
  `full_redraw_12x9` and `full_redraw_present_bounds_800`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-20260423.json`
  reports `106/106` selected bytes patched and
  `full-redraw-present-bounds-800` `6/6`.
- Focused CDB validation:
  `captures\cdb-map-redraw-rect-fullonly-presentbounds-20260423.log` reached
  gameplay, clamped saved scroll `(39,42)->(38,41)`, logged the same 12x9 tile
  coverage, and widened full-redraw presents to:
  - top `(32,16,799,225)`;
  - right `(429,225,799,252)`;
  - bottom `(32,252,799,591)`.
- Captured frame:
  `captures\map-redraw-rect-fullonly-presentbounds-frame-loadslot0-20260423.png`
  is target-owned (`1200x900`) and shows the terrain now filling the enlarged
  present area. Remaining defects are old UI/minimap/sidebar overlays in the
  right/top HD area, not clipped map presentation.
- Non-CDB visual smoke
  `captures\visual-smoke-20260423-145622\results.json` did not reach gameplay:
  both mouse probes exited `2`, and the frame stayed on the intro path. Treat
  this as a harness/foreground issue until reproduced; it does not contradict
  the CDB full-redraw proof.

## Minimap Duplicate Fix, 2026-04-23

- The widened present-bounds candidate exposed a duplicate minimap in the
  top-right HD area.
- Added `probes/cdb/map/clash95_map_overlay_probe.cdb` to log `004024E0` blits, `0040C150`
  text draws, and suspicious overlay/sprite callsites after entering gameplay.
- Overlay probe evidence:
  `captures\cdb-map-overlay-presentbounds-20260423.log` and
  `captures\map-overlay-presentbounds-frame-loadslot0-20260423.png`.
  The CDB log showed repeated minimap blits returning through `0040D633` with
  source/destination extents beyond the native 214-wide minimap backing surface.
- Static disassembly identified `0040D560` as the minimap dirty-rectangle
  helper. It uses minimap left/top/width/height globals at
  `00523344..0052334A` and the minimap backing surface at `0052334C`.
- Added patch group `minimap-right-clip`:
  - hook `0x00C960`, VA `0040D560`,
    `56558b35e4025200 -> e91bc40d00909090`;
  - cave `0x0E8D80`, VA `004E9980`, that computes
    `left + width - 1`, skips chunks starting beyond that right edge, clamps
    partial chunks to that right edge, and resumes the original helper.
- The first cave version clamped `bx` only and crashed on an inverted rectangle.
  The current v2 cave also skips fully-outside chunks by jumping to the original
  `0040D6C7` epilogue.
- Built non-destructive candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapclip2_20260423.exe`,
  SHA-256
  `03F1BE6C72B6BB7E4DC84068274F50A95F9A039DF1B0C44C3EA96CB55D263A3C`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapclip2-20260423.json`
  reports `108/108` selected bytes patched and `minimap-right-clip` `2/2`.
- Runtime overlay validation:
  `captures\cdb-map-overlay-presentbounds-minimapclip2-20260423.log` reached
  gameplay without an AV. The captured frame
  `captures\map-overlay-presentbounds-minimapclip2-frame-loadslot0-20260423.png`
  shows the duplicated minimap is gone.
- Full-redraw validation still proves 12x9 tile draw and widened presents:
  `captures\cdb-map-redraw-rect-fullonly-presentbounds-minimapclip2-20260423.log`
  reports the widened top `(32,16,799,225)`, right `(429,225,799,252)`, and
  bottom `(32,252,799,591)` rectangles.
- Current remaining defect:
  the top-right area no longer duplicates the minimap, but a black/stale band
  and old vertical border texture remain above part of the widened map body.
  Next trace should target post-full-redraw blits/fills/presents intersecting
  x `608..799` and y `16..225`.

## Minimap Top-Right Anchor, 2026-04-23

- Added `probes/cdb/map/clash95_map_topband_probe.cdb` to sample `dword_5202E0` pixels in the
  suspect top/right band and log blits intersecting logical x `608..799`,
  y `16..225`.
- Top-band probe against the minimapclip2 candidate:
  `captures\cdb-map-topband-minimapclip2-20260423.log`.
  It reached gameplay and showed top/right source pixels were already black in
  `dword_5202E0` before the widened top present. No post-full-redraw
  `TOPBAND_WRITE` rows were recorded, so the black band is not currently proven
  to be a later overwrite.
- Static CDB disassembly of `sub_40D330` showed the minimap left coordinate is
  computed as `right_anchor - minimap_width`; the original right anchor is
  `608` at VA `0040D390`, file offset `0x00C790`.
- Added patch group `minimap-hd-right-anchor`:
  `0x00C790 BA60020000 -> BA20030000`, moving the minimap right anchor
  `608 -> 800`.
- Added diagnostic stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright`.
  It combines the present-bounds diagnostic, minimap dirty-rectangle clip, and
  the new HD minimap anchor.
- Built non-destructive candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_20260423.exe`,
  SHA-256
  `D326BD782F7B30FAE4F6622ACA5AF176D4D9B2B036CB67C13A5E4A47F086E11A`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-20260423.json`
  reports `109/109` selected bytes patched and
  `minimap_hd_right_anchor=true`.
- Runtime overlay validation:
  `captures\cdb-map-overlay-presentbounds-minimapright-20260423.log` reached
  gameplay without an AV and logged minimap dirty blits at the new top-right
  destination range, including `(586,16)`, `(608,16)`, `(672,16)`, and
  `(736,16)`.
- Captured frame:
  `captures\map-overlay-presentbounds-minimapright-frame-loadslot0-20260423.png`
  is target-owned at `1200x900`; it shows the minimap in the upper-right corner
  and the old minimap location now reveals terrain.
- Next risk:
  hit testing/navigation on the minimap has not yet been proven after the move.
  Because the patch updates the initializer that writes the minimap globals,
  dirty blits already follow the new location; still verify actual minimap
  clicks before promoting this stage.
- Final validation commands:
  - Bundled Python `tools\wiki_lint.py`: `wiki_lint: ok`.
  - Bundled Python `tools\patch_stage_report.py --stage ...minimapright`:
    `109 patched, 0 original, 0 unexpected`, SHA-256
    `D326BD782F7B30FAE4F6622ACA5AF176D4D9B2B036CB67C13A5E4A47F086E11A`.
  - `git diff --check`: exit `0`; only existing LF-to-CRLF warnings were
    emitted.

## Minimap Click Probe And Mouse Bounds, 2026-04-23

- Added `probes/cdb/map/clash95_map_minimap_click_probe.cdb` to log minimap initialization,
  play-game entry, redraw state, mouse rows, minimap hit-test calls, minimap
  hit-test successes, and any access violation during moved-minimap clicks.
- Added `tools\minimap_probe_summary.py`, a small log parser that reports
  minimap bounds, old-anchor rejection, new-box acceptance, scroll changes,
  mouse ranges, and AV rows from the CDB probe.
- First minimapright runtime pass:
  `captures\cdb-map-minimapclick-minimapright-20260423.log` and
  `captures\map-minimapclick-minimapright-frame-20260423.png`.
  This pass remained at the load menu because the click cadence only sent one
  click per point; it produced no gameplay/minimap rows.
- Second minimapright runtime pass:
  `captures\cdb-map-minimapclick-minimapright-v2-20260423.log`,
  `captures\map-minimapclick-minimapright-summary-v2-20260423.json`, and
  `captures\map-minimapclick-minimapright-frame-v2-20260423.png`.
  It reached gameplay with no AV and captured a target-owned `1200x900` frame.
- Probe result:
  `init=1`, `tests=240`, `true=120`, `button_true=48`, `redraw=120`,
  `mouse=66`, `av=0`. The minimap globals are now
  `left=586`, `top=16`, `width=214`, `height=214`, `right=799`,
  `bottom=229`.
- Hit-test evidence:
  rows in the old-only x range were tested but never accepted
  (`old_only_test_rows=127`, `old_only_true_rows=0`), while rows inside the new
  minimap box were accepted (`new_box_true_rows=120`). This proves the
  minimap test helper follows the moved globals rather than the original
  native left anchor.
- Remaining input evidence:
  the logged internal mouse bounds stayed at `max=(610,452)`, and high
  requested client x positions such as `650`, `760`, and `700` collapsed to
  internal x around `448`. The scroll value remained `(38,41)`, so minimap
  navigation is not proven yet.
- Static disassembly of the viewport switch path showed native constants at
  `00460E11 push 1E0h` and `00460E1D mov ecx,280h`; the callee at
  `00460B20` writes mouse/view bounds into object fields. This is the next
  likely root cause for the moved minimap being visible/tested but not
  reachable by input.
- Added diagnostic stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch`.
  It is intentionally diagnostic: it combines the minimap-right layout with
  the full viewport switch instead of the menu-safe viewport switch to test
  whether gameplay mouse bounds must widen after the map-surface swap.
- Built non-destructive candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_vswitch_20260423.exe`,
  SHA-256
  `079CC3ADEA88B3C96276E0FA0F16DD886A9628C858806C131847BA814C778941`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch-20260423.json`
  reports `111/111` selected bytes patched,
  `viewport_switch_800x600=true`, and `menu_safe_switch=false`.
- Runtime attempt against the diagnostic vswitch candidate did not produce
  useful game evidence because the Python mouse driver hit
  `PermissionError: [WinError 5] SetCursorPos` before the probe reached
  gameplay. Treat this as a harness/foreground permission failure, not as a
  candidate failure.
- Next step:
  prove the bound writes at `00460B20` and mouse rows at `00460A9D` for the
  vswitch candidate without relying first on `SetCursorPos`; only rerun the
  click path after the internal max x/y bounds are known to widen.

## Viewport Switch Bounds Proof And Rerun, 2026-04-23

- Added `probes/cdb/render/clash95_viewport_bounds_probe.cdb` to log:
  - initial viewport call args at `0046053F`;
  - later viewport-switch call args at `00460E32`;
  - `sub_460B20` entry/exit around `00460B20` / `00460BA7`;
  - mouse-bound rows at `00460A9D`.
- Added `scripts\cdb\run_cdb_viewport_bounds_probe.ps1`, a timed CDB-only harness that
  kills stale/new `clash95*` and `cdb` processes after the run and only sends
  optional space pulses to skip the intro. It does not depend on
  `SetCursorPos`.
- Added `tools\viewport_bounds_summary.py` and wrote machine-readable compare
  output to `captures\viewport-bounds-compare-20260423.json`.
- Baseline timed probe:
  `captures\cdb-viewport-bounds-minimapright-20260423.log`.
  It proves the menu-safe minimapright candidate still ends on a native later
  viewport-switch write:
  `VIEWPORT_SWITCH_CALL right_arg=640 bottom_arg=480` and final
  `VIEWPORT_SET max=(610,452)` for metadata `005196a0`.
- Diagnostic timed probe:
  `captures\cdb-viewport-bounds-minimapright-vswitch-20260423.log`.
  It proves the full viewport-switch candidate keeps the widened later bounds:
  `VIEWPORT_SWITCH_CALL right_arg=800 bottom_arg=600` and final
  `VIEWPORT_SET max=(770,572)` for metadata `005196a0`.
- Parser summary:
  `tools\viewport_bounds_summary.py` reports:
  - baseline `final_set_is_native_640x480=true`;
  - diagnostic `final_set_is_hd_800x600=true`.
- This closes the earlier ambiguity: the moved-minimap input problem was
  primarily caused by the later `sub_460D80` viewport switch collapsing the
  gameplay bounds back to native values in the menu-safe stage.
- With that bound proof in hand, reran the moved-minimap click probe under
  elevated CDB against the full viewport-switch candidate:
  `captures\cdb-map-minimapclick-minimapright-vswitch-rerun-20260423.log`,
  `captures\map-minimapclick-minimapright-vswitch-rerun-summary-20260423.json`,
  `captures\map-minimapclick-minimapright-vswitch-rerun-mouse-20260423.json`,
  and target-owned frame
  `captures\map-minimapclick-minimapright-vswitch-rerun-frame-20260423.png`
  with SHA-256
  `73E6ED40279168E996EF28EC40C14F6F09BB1991AA1CBCBF52598B902F47FBA4`.
- Result:
  the widened gameplay bounds now really take effect during the click run.
  Internal mouse rows reach `x=648`, `x=700`, and `x=760` with
  `max=(770,572)` instead of collapsing around `x=448`.
- The moved minimap still hit-tests correctly in the HD box:
  `old_only_test_rows=113`, `old_only_true_rows=0`,
  `new_box_true_rows=120`, `button_true_rows=56`, `av_rows=0`.
- Remaining blocker:
  scroll still stays `(38,41)` through the whole run, so moved-minimap
  navigation is still not proven even though the cursor now reaches the new
  top-right minimap area and `MINIMAP_TRUE` fires there.
- New static clue:
  `sub_40DC10` at `0040DC10` is the minimap-driven scroll updater. It still
  contains native visible-area clamps:
  - `0040DCB0 83EE09` (`map_width - 9`);
  - `0040DCDA 83EA07` (`map_height - 7`).
  This path is not currently in the patcher and should be traced next before
  promoting the vswitch stage.

## Minimap Action Clamp, 2026-04-23

- Added focused probe `probes/cdb/map/clash95_minimap_action_probe.cdb` and parser
  `tools\minimap_action_summary.py`.
- First focused action run:
  `captures\cdb-map-minimapaction-minimapright-vswitch-20260423.log`.
- First focused action summary:
  `captures\map-minimapaction-minimapright-vswitch-summary-20260423.json`.
- First result:
  `sub_40DC10` is active and reaches the write path during moved-minimap
  clicks. It wrote `scroll=(13,6)` for the mid-box click, but the lower-right
  click accepted target `(41,44)` and still ended at native-like
  `scroll=(41,43)`.
- Folded the remaining minimap-action clamp bytes into the existing 12x9
  `helpers` group in `patch_clash95_hd.py`:
  - `0x00D0B0 83EE09 -> 83EE0C`
  - `0x00D0DA 83EA07 -> 83EA09`
  - `0x00D124 83EA07 -> 83EA09`
- Rebuilt fresh candidate from the verified original:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_vswitch_minimapclamp_20260423.exe`
  with SHA-256
  `438543C90A82373ED60DE50F4A451B89FABDE48E7DA759C407CFFD76BABACE29`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-vswitch-minimapclamp-20260423.json`
  reports `114/114` selected bytes patched and `helpers 28/28`.
- Second focused action run:
  `captures\cdb-map-minimapaction-minimapright-vswitch-minimapclamp-20260423.log`.
- Second focused action summary:
  `captures\map-minimapaction-minimapright-vswitch-minimapclamp-summary-20260423.json`.
- Second result:
  the same lower-right minimap target `(41,44)` now produces explicit clamp
  rows `x 41 -> 38` and `y 44 -> 41`, and final scroll values become
  `{(13,6), (26,24), (38,41)}` with `av_rows=0`.
- Interpretation:
  moved-minimap navigation now matches the 12x9 gameplay viewport under the
  full `viewport-switch` diagnostic. The remaining work is to preserve those
  widened gameplay bounds without depending on the all-diagnostic full switch.

## Conditional Viewport Switch V2, 2026-04-24

- Reworked `viewport-switch-dynamic-surface` into a metadata-based conditional
  viewport switch. The hook now treats `edx == 005196A0` as the gameplay/map
  metadata path and uses widened `800x600` bounds there, while other metadata
  keeps native `640x480` bounds for menu safety.
- First build:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_dynvswitch_20260424.exe`
  with SHA-256
  `C98709257AF61E7EF87F1B71650F07A5EC2F6A3EB2B74DA0D708C2D39FE90CCD`.
  Static verification passed, but runtime CDB exposed a bad short-jump
  displacement: `VIEWPORT_ENTRY` saw `right_arg=3 bottom_arg=27`, then invalid
  bounds `max=(65509,65535)` and an access violation. This candidate is bad.
- Fixed the short jump from `74 0A` to `74 0C` in the cave so the HD branch
  lands on `push 600` / `mov ecx,800`.
- Current v2 candidate:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_dynvswitch_v2_20260424.exe`
  with SHA-256
  `FDFE9A346D709A44E612E1FF1ED9AA42C1B191D566EC1E013ADA86CF0802F1AD`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-v2-20260424.json`
  reports `114/114` selected bytes patched, including
  `viewport-switch-dynamic-surface 2/2`.
- Viewport bounds proof:
  `captures\viewport-bounds-minimapright-dynvswitch-v2-20260424.json`
  reports `final_set_is_hd_800x600=true`, `av=0`, final metadata
  `005196a0`, and final max bounds `(770,572)`. Mouse-bound rows reached high
  HD minimap positions including `x=648`, `x=700`, and `x=760` while retaining
  `max=(770,572)`.
- Minimap action proof:
  `captures\map-minimapaction-minimapright-dynvswitch-v2-summary-20260424.json`
  reports `action_path_reached=true`, `write_path_reached=true`,
  `scroll_changed=true`, and `av=0`. Accepted target values are
  `{(13,6), (26,24), (41,44)}`; final scroll values are
  `{(13,6), (26,24), (38,41)}`, matching the 12x9 minimap clamp behavior from
  the full diagnostic switch.
- Interpretation:
  the conditional metadata switch now preserves menu-safe native bounds while
  restoring widened gameplay bounds for the map metadata. The next validation
  should be a less breakpoint-heavy visual/gameplay smoke run before promoting
  this stage as the recommended path.

## Visual Smoke Fallback And Default Promotion, 2026-04-24

- Promoted the patcher default stage to
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
  Reason: CDB evidence proves the old `novswitch` default collapses gameplay
  bounds back to native `max=(610,452)`, while the v2 conditional switch keeps
  map metadata `005196a0` at `max=(770,572)` and preserves moved-minimap scroll
  behavior.
- Hardened `scripts\capture\capture_clash_client_frame.ps1`:
  - it can reacquire a same-process top-level HWND when the wrapper exposes more
    than one visible window;
  - if another top-level window still covers the target center, it falls back to
    a window-DC capture and records `CaptureMode=windowdc-contaminated-fallback`.
- Hardened `tools\mouse_path_probe.py`:
  - added `--move-mode auto` to fall back from `SetCursorPos` to absolute
    `SendInput`;
  - added `--move-mode none` for PostMessage-only liveness checks;
  - cursor API failures now write explicit `cursor_error` rows instead of
    aborting before JSON is saved.
- Extended `scripts\smoke\run_clash_visual_smoke.ps1` with `-MoveMode`, `-ClickMode`, and
  `-PostIntroWaitSec`.
- Runtime smoke attempts in the Codex desktop context:
  - `captures\visual-smoke-20260424-073707`: failed at contaminated capture.
  - `captures\visual-smoke-20260424-073924`: failed at `SetCursorPos`
    `[WinError 5]`.
  - `captures\visual-smoke-20260424-074428`: fallback run completed without a
    crash; first frame was still the intro animation and the final frame was
    the menu.
  - `captures\visual-smoke-20260424-074630`: longer fallback run completed
    without a crash and captured a stable centered 800x600 menu frame inside
    the 1200x900 client. Menu and post-path frame hashes match, so
    PostMessage-only input did not enter gameplay.
- Current interpretation:
  the v2 candidate is promoted as the best patcher default because the
  breakpoint-backed gameplay evidence is strong and the normal liveness smoke
  did not crash. A true clean gameplay smoke remains blocked in this runner by
  Windows cursor API permission failures (`SetCursorPos`, absolute
  `SendInput`, and `GetCursorPos` all returned `[WinError 5]`).

## Top-Band Probe Parser, 2026-04-24

- Added `tools\topband_probe_summary.py` to parse `probes/cdb/map/clash95_map_topband_probe.cdb`
  logs into repeatable JSON summaries.
- Parsed existing evidence:
  `captures\cdb-map-topband-minimapclip2-20260423.log` ->
  `captures\map-topband-minimapclip2-summary-20260424.json`.
- Summary result:
  - `PLAYGAME=1`, `FULLREDRAW_ENTER=8`, `TOPBAND_PRESENT=240`, `av_rows=0`;
  - top present call sites are `00418BDC` (`224` rows), `004188EB` (`8` rows),
    and `0041898D` (`8` rows);
  - sampled source pixels in `dword_5202E0` are already zero at x `672` and
    `736` for y `16`, `80`, and `144`, both before and after the widened
    top-band present call;
  - x `608` is nonzero in the same top rows, and y `208` later has nonzero
    samples at x `608`, `672`, and `736`.
- Interpretation:
  the top/right band is not a presentation-copy bug. The 800x600 map target is
  being presented, but parts of the top rows past the first new column were
  never filled before present. Next probe should trace the tile/body writer or
  dirty-region path that should populate top-row columns x `672..799`.

## Top-Band Image Region Summary, 2026-04-24

- Added `tools\topband_image_summary.py`, a dependency-free PNG analyzer that
  measures whole logical tile regions in captured frames. It imports the
  existing PNG reader from `tools\capture_geometry.py` and converts logical
  `800x600` coordinates to scaled capture pixels.
- Ran:
  `python tools\topband_image_summary.py captures\map-overlay-presentbounds-minimapclip2-frame-loadslot0-20260423.png captures\map-overlay-presentbounds-minimapright-frame-loadslot0-20260423.png captures\map-viewportbounds-minimapright-dynvswitch-v2-frame-20260424.png --write-json captures\topband-image-summary-20260424.json`
- Result:
  - the older `minimapclip2` frame has `0.0%` nonblack coverage for the
    suspect x `672..799`, y `16..207` logical tile regions;
  - the `minimapright` frame has `98.958..100.0%` nonblack coverage across the
    same upper-right regions;
  - the current v2 `minimapright-dynvswitch` frame has `98.806..100.0%`
    nonblack coverage across those regions.
- Interpretation:
  the black top/right band was real in the intermediate minimap-clip-only
  candidate, but the moved-minimap anchor fills the exposed upper-right HD area.
  Do not keep chasing `00418BDC` as a v2 map-body-fill bug unless a fresh v2
  frame reproduces region-level blanking.

## Bottom-Right Tile Coverage Fix, 2026-04-24

- Added `tools\map_tile_coverage.py`, a dependency-free gameplay-frame analyzer
  that maps scaled captures back to the logical 12x9 tile grid, masks the moved
  minimap, and reports blank or suspicious active cells.
- Ran it against the current v2 frame:
  `captures\map-viewportbounds-minimapright-dynvswitch-v2-frame-20260424.png`
  -> `captures\map-tile-coverage-v2-bottom12-20260424.json`.
- Result:
  the lower-right active cells are blank in the pre-fix frame:
  - `r8c9`: `3.103%` nonblack
  - `r8c10`: `1.042%` nonblack
  - `r8c11`: `1.031%` nonblack
- Root cause:
  `full-redraw-12x9` still used `0x017DFF 06->09`, so the clipped bottom row
  drew only 9 columns.
- Patch change:
  `patch_clash95_hd.py` now uses `0x017DFF 06->0C`, changing
  `sub_418700` clipped bottom row columns from `6` to `12`.
- Built fresh candidate outside the repo:
  `C:\Clash\clash95_hd_mousedynorigin_mapsurface_scrollclamp_presentbounds_minimapright_dynvswitch_bottom12_20260424.exe`
  with SHA-256
  `A85E9E7FD0E16B26773B0479C987DC3648D38E4B07209FA849D39C1AD9DAFEAB`.
- Static verifier:
  `captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-bottom12-20260424.json`
  reports `114/114` selected bytes patched.
- Runtime CDB liveness/viewport probe:
  `captures\cdb-viewport-bounds-minimapright-dynvswitch-bottom12-20260424.log`
  summarized to
  `captures\viewport-bounds-minimapright-dynvswitch-bottom12-20260424.json`.
  It reached the map metadata switch, saw final metadata `005196a0`, final HD
  max `(770,572)`, and `av=0`.
- Remaining proof:
  capture a fresh gameplay frame from the bottom12 candidate and rerun
  `tools\map_tile_coverage.py`; expected result is no blank cells at `r8c9`,
  `r8c10`, or `r8c11`.

## Windows Sandbox UI Harness, 2026-04-24

- Added `scripts\smoke\run_clash_windows_sandbox.ps1` to support a disposable UI testing
  route where the game window runs inside Windows Sandbox instead of disrupting
  the host desktop.
- Behavior:
  - maps the repo as writable `C:\Repo`;
  - maps host `C:\Clash` read-only as `C:\HostClash`;
  - maps the bundled Python runtime read-only as `C:\HostPython`;
  - copies the game install only into sandbox-local `C:\Clash`, skipping
    obvious `crack.exe` / `keygen.exe` names;
  - builds a patched candidate inside the sandbox;
  - runs `scripts\smoke\run_clash_visual_smoke.ps1`;
  - runs `tools\map_tile_coverage.py` against `after-map-path.png` when a frame
    exists.
- Validation:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\run_clash_windows_sandbox.ps1 -NoLaunch`
  generated:
  `captures\sandbox-20260424-091715\clash-hd-sandbox.wsb`,
  `captures\sandbox-20260424-091715\sandbox-entry.ps1`, and
  `captures\sandbox-20260424-091715\host-summary.json`.
- Host status:
  `WindowsSandbox.exe` is currently missing on this machine, so the feature
  `Containers-DisposableClientVM` must be enabled and the host rebooted before
  launch runs can execute.

## Retired Route Notes Removed, 2026-05-12

The obsolete route evidence block from 2026-04-24/25 has been removed. Current validation notes resume below with the no-popup CDB surface dump path.

## No-Popup CDB Surface Dump Harness, 2026-04-28

- Added `scripts\cdb\run_cdb_surface_dump.ps1`.
- Added `probes/cdb/render/clash95_surface_dump_probe.cdb`.
- Added `tools\cdb_surface_dump_to_png.py`.
- Harness behavior:
  builds a unique patched candidate from `C:\Clash\clash95.exe`, runs x86 CDB
  on a separate hidden Windows desktop, refuses visible-desktop fallback unless
  `-AllowVisibleDesktop` is passed, generates a per-run CDB script with an
  absolute `.writemem` path, and cleans up only the launched CDB/candidate
  processes.
- Probe behavior:
  route-injects toward load-slot gameplay, bypasses hidden-desktop DirectInput
  acquire loops, waits for gameplay redraw, reads `dword_5202E0`, and is ready
  to dump `base..base+(width*height)-1`.
- Converter behavior:
  dependency-free raw 8-bit to PNG conversion with a deterministic grayscale
  index palette plus metadata JSON. `--self-test` passed.
- Runtime command:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_cdb_surface_dump.ps1 -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-surface-dump -RunSeconds 20`.
- Runtime result:
  `captures\cdb-surface-dump-20260428-105423\RUN-SUMMARY.md` reports a clean
  hidden-desktop diagnostic failure, not a timeout:
  `App_RequestQuit=True` and
  `DirectDraw Error DDERR_UNSUPPORTED`.
- DLL-load evidence:
  the isolated candidate directory loaded system
  `C:\WINDOWS\SysWOW64\DDRAW.dll` instead of `C:\Clash\DDRAW.dll`.
- Interpretation:
  the no-popup CDB path is implemented, but raw DirectDraw cannot create the
  required mode on a hidden desktop. The next no-popup route should prototype a
  process-local DirectDraw proxy/wrapper that can satisfy surface creation and
  expose dumpable 8-bit surface memory without showing a host-desktop window.

## No-Popup DirectDraw Proxy Surface Dump, 2026-04-28

- Added `ddraw_surfdump_proxy\ddraw_surfdump_proxy.cpp` and
  `ddraw_surfdump_proxy\ddraw_surfdump_proxy.def`.
- Added `scripts\build\build_ddraw_surfdump_proxy.ps1` to build a 32-bit local `ddraw.dll`
  into `C:\ClashTests\cdb-surface-dump` or another isolated candidate folder.
- Extended `scripts\cdb\run_cdb_surface_dump.ps1` with `-UseDdrawProxy`,
  `-NoSkipStartAnims`, `-FastForwardStartAnims`, forward-slash CDB dump paths,
  and post-dump cleanup polling.
- Successful runtime command:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-surface-dump -RunSeconds 120`.
- Successful run folder:
  `captures\cdb-surface-dump-20260428-123224`.
- Runtime evidence:
  local `C:\ClashTests\cdb-surface-dump\DDRAW.dll` loaded, the probe reached
  gameplay, emitted `SURFDUMP_READY` for an 800x600 surface, wrote a 480000-byte
  raw dump, and reconstructed
  `captures\cdb-surface-dump-20260428-123224\surface.png`.
- Coverage evidence:
  `gameplay_frame_likely=True`, `active=108`, `measurable=99`, `blank=13`,
  `edge_coverage.overall=72.711%`, with right-side blank cells still flagged.
- Caveats:
  `-FastForwardStartAnims` and the older blunt `UI_StartAnims` skip reproduce
  the `00487cf4` / address `0x38` AV. Full startup with `-NoSkipStartAnims`
  works but can stall before menu routing. The CDB `.writemem` path must use
  forward slashes inside breakpoint commands.

## No-Popup Surface Dump Visibility Classification, 2026-04-29

- Updated `probes/cdb/render/clash95_surface_dump_probe.cdb` to emit `SCROLL_VISDUMP` and the
  matching CDB `db` visibility-memory dump for the 12x9 viewport before the
  surface dump action.
- Updated `scripts\cdb\run_cdb_surface_dump.ps1` so the default dump method is host-side
  `ReadProcessMemory` after `SURFDUMP_READY`; the old CDB `.writemem` route is
  still available with `-UseCdbWriteMem`.
- Updated the harness to run `tools\visibility_coverage.py` after
  `tools\map_tile_coverage.py` and include the visibility summary in
  `summary.json` / `RUN-SUMMARY.md`.
- Runtime command:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-surface-dump -RunSeconds 120`.
- Successful run folder:
  `captures\cdb-surface-dump-20260429-111340`.
- Runtime result:
  `Passed=true`, `LaunchMode=hidden-desktop`, `StoppedAfterDump=true`,
  `DumpMethod=host-readprocessmemory`, `HostDumpedMemory=true`, and
  `TimedOut=false`.
- CDB evidence:
  `SURFDUMP_PLAYGAME`, `SURFDUMP_READY`, `SCROLL_VISDUMP`, and
  `SURFDUMP_HOST_READY` all appear in the same log. No `AV_SURFDUMP` or CDB
  syntax error was observed.
- Surface evidence:
  `surface.raw` is 480000 bytes; `surface.png` is an 800x600 grayscale-index
  reconstruction with PNG SHA-256
  `0f989b85671be733914098b3a33a74a5ab4afadfe1c3fa6471d1665b4bf1a34f`.
- Image-only coverage:
  `gameplay_frame_likely=True`, `active=108`, `measurable=99`, and `blank=13`.
- Visibility-aware coverage:
  `observation_points=108`, every one of the 13 blank cells is explained,
  `unexplained_blank_cells=[]`, and `status_counts.visibility_zero=13`.
- Interpretation:
  the current no-popup grayscale dump confirms the right/bottom dark cells are
  visibility-zero fog/unexplored state for this save, not a missing 12x9 tile
  draw. Next HD map work should move to a controlled visible-edge or alternate
  save proof instead of patching visibility in the normal mod.

## No-Popup Visible-Edge Experiment, 2026-04-29

- Added experimental `-ForceVisibleEdges` to `scripts\cdb\run_cdb_surface_dump.ps1`.
- Updated `probes/cdb/render/clash95_surface_dump_probe.cdb` with placeholders for debugger-only
  visibility injection at `PlayGame` and before surface dumping.
- The switch is not a normal HD patch. It temporarily targets the current
  load-slot-0 `scroll=(10,17)` viewport and sets player-0 visibility bytes for
  the right/bottom cells that `map_tile_coverage.py` flags.
- Failed syntax runs:
  `captures\cdb-surface-dump-20260429-115600` and
  `captures\cdb-surface-dump-20260429-120508` exposed CDB quoting/expression
  issues in generated breakpoint actions; those generator bugs were fixed.
- Useful partial run:
  `captures\cdb-surface-dump-20260429-124928`.
- Evidence from that run:
  it reached gameplay, emitted `SURFDUMP_FORCE_VISIBLE_EDGES`, dumped an
  800x600 surface, and `SCROLL_VISDUMP` showed nonzero visibility values for
  the target cells.
- Result:
  `map_tile_coverage.py` still reported the same 13 blank cells, and
  `tools\visibility_coverage.py` classified them as `blank_despite_visible=13`.
- Interpretation:
  direct visibility bytes were nonzero by dump time, but the dumped surface was
  unchanged. This likely means the write timing was too late for the tile draw,
  or the proof must force the exact `sub_40F0C0` neighbor path before
  `sub_416850`, not just direct cell bits.
- Follow-up attempts:
  moving injection to `PlayGame` then rerunning
  `captures\cdb-surface-dump-20260429-125308` and
  `captures\cdb-surface-dump-20260429-125735` stalled before menu routing under
  the hidden desktop. A default no-force retry
  `captures\cdb-surface-dump-20260429-130246` also stalled, so the active
  blocker is the known hidden-desktop full-startup fragility.

## No-Popup Forced Visible-Edge Proof, 2026-04-29

- Updated `probes/cdb/render/clash95_surface_dump_probe.cdb` with disabled-at-start VEDGE
  breakpoints around the same branch path used by the earlier visibility proof:
  `00416850`, `004169bc`, `004169c1`, `00417a98`, `004169e6`,
  `0041876b`, and `004189fa`.
- Updated `scripts\cdb\run_cdb_surface_dump.ps1 -ForceVisibleEdges` so it enables those
  breakpoints at `PlayGame`, writes the same player-0 visibility bytes as the
  earlier proof, and freezes the proof viewport at `scroll=(10,17)` during
  redraw.
- Reworked `-FastForwardStartAnims` to skip startup/AVI sleep waits while still
  allowing AVI/resource initialization to execute. The previous fast-forward
  route skipped AVI calls and could trigger the `00487cf4` / `0x38` crash.
- Failed intermediate run:
  `captures\cdb-surface-dump-20260429-133504` reached gameplay and produced a
  dump, but the viewport drifted to `map0=(0,41)` before capture; coverage
  correctly failed with `gameplay_frame_likely=False`.
- Successful runtime command:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -ForceVisibleEdges -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-surface-dump -RunSeconds 120`.
- Successful run folder:
  `captures\cdb-surface-dump-20260429-133917`.
- Runtime result:
  `Passed=True`, `LaunchMode=hidden-desktop`, `StoppedAfterDump=True`,
  `DumpMethod=host-readprocessmemory`, `HostDumpedMemory=True`, surface
  `800x600`, raw bytes `480000`, PNG SHA-256
  `0ffa5f2100b2d74e5784865733d11a9a6a710e67ec3ed4fb7e24615dc2bd5b15`.
- CDB evidence:
  `SURFDUMP_FORCE_VISIBLE_EDGES`, `SURFDUMP_FORCE_VIEWPORT`,
  `SURFDUMP_READY map0=(10,17)`, `SCROLL_VISDUMP`, 54
  `SURFDUMP_VEDGE_VISRET` rows, and 54 `SURFDUMP_VEDGE_POST` rows.
- Coverage evidence:
  `gameplay_frame_likely=True`, `active=108`, `measurable=99`,
  `blank=0`, `stale_or_solid=0`, `edge_coverage.overall=86.264%`,
  `right_below_minimap=97.838%`, and `bottom=77.373%`.
- Interpretation:
  the HD 12x9 map path can draw bright right/bottom cells when the save
  visibility permits them. The earlier dark cells are not a map-drawing defect
  in the normal patch; they are fog/unexplored state for the current save.

## Forced Visible-Edge Gate, 2026-04-29

- Added `tools\forced_visible_summary.py`.
- The gate joins `map_tile_coverage.py` JSON with CDB log evidence and requires:
  `gameplay_frame_likely=True`, zero active blank cells, latest
  `SCROLL_VISDUMP map0=(10,17)`, `SURFDUMP_FORCE_VISIBLE_EDGES`,
  `SURFDUMP_FORCE_VIEWPORT`, 54 `SURFDUMP_VEDGE_VISRET` rows, 54
  `SURFDUMP_VEDGE_POST` rows, nonzero visibility for all VEDGE rows, and
  nonblack post samples for all VEDGE rows.
- Wired the gate into `scripts\cdb\run_cdb_surface_dump.ps1 -ForceVisibleEdges`. The harness
  now writes `forced-visible-summary.json` and `forced-visible-summary.txt`, and
  a forced-visible run cannot report success unless this gate passes.
- Direct validation:
  `tools\forced_visible_summary.py` passed on
  `captures\cdb-surface-dump-20260429-133917`.
- Negative validation:
  the same parser failed as expected on
  `captures\cdb-surface-dump-20260429-133504`, reporting
  `gameplay_frame_likely=False`, `latest SCROLL_VISDUMP map0=[0,41]`,
  missing `SURFDUMP_FORCE_VIEWPORT`, wrong VEDGE counts, zero visibility rows,
  and active blank cells.
- Integrated runtime command:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -ForceVisibleEdges -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-surface-dump -RunSeconds 120`.
- Integrated run folder:
  `captures\cdb-surface-dump-20260429-135242`.
- Integrated result:
  `Passed=True`, `ForcedVisibleExitCode=0`, `ForceVisibleStillBlankCells=[]`,
  `ForcedVisibleGate.passed=True`, `latest_visdump.map0=[10,17]`,
  `vedge_visret_count=54`, `vedge_post_count=54`,
  `vedge_visret_nonzero_count=54`, and `vedge_post_nonblack_count=54`.
- Screenshot artifact:
  `captures\cdb-surface-dump-20260429-135242\surface.png`.

## Normal No-Popup Visibility Explanation Gate, 2026-04-29

- Updated `scripts\cdb\run_cdb_surface_dump.ps1` so normal no-popup runs with active blank
  cells invoke `tools\visibility_coverage.py --require-explained`.
- The harness now records `VisibilityExitCode`, `VisibilityRequireExplained`,
  and `VisibilityExplainedGate` in `summary.json`, reports the gate in
  `RUN-SUMMARY.md`, and fails the run if any blank active cell lacks same-run
  visibility/fog/clip evidence.
- Validation pass:
  `captures\cdb-surface-dump-20260429-111340` has 13 active blank cells, all
  classified as `visibility_zero`; `--require-explained` exited `0`.
- Negative validation:
  the same coverage with an empty CDB log exited `2` with 13
  `unexplained_blank` cells.
- Forced-visible negative validation remains handled by
  `tools\forced_visible_summary.py`; `captures\cdb-surface-dump-20260429-133504`
  exits `2` because the viewport drifted to `map0=(0,41)`, the proof markers
  and VEDGE counts are wrong, and blank active cells remain.
- Screenshot artifact for the current no-popup proof:
  `captures\cdb-surface-dump-20260429-135242\surface.png`.

## Fresh Normal No-Popup Gate Run, 2026-04-29

- Command:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-surface-dump -RunSeconds 180`.
- Run folder:
  `captures\cdb-surface-dump-20260429-140916`.
- Result:
  `Passed=True`, `LaunchMode=hidden-desktop`, `HiddenDesktop=True`,
  `StoppedAfterDump=True`, `TimedOut=False`, and
  `DumpMethod=host-readprocessmemory`.
- Candidate:
  `C:\ClashTests\cdb-surface-dump\clash95_hd_surfdump_20260429_140916.exe`,
  SHA-256 `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Surface:
  `800x600`, `480000` bytes, PNG SHA-256
  `c91d6646a7517717053faa1a714f50cebd868c05e10974099c54a4fba64850b8`.
- Coverage:
  `gameplay_frame_likely=True`, `active=108`, `measurable=99`, `blank=13`,
  `stale_or_solid=0`.
- Visibility gate:
  `VisibilityRequireExplained=True`, `VisibilityExplainedGate.Passed=True`,
  `VisibilityExitCode=0`, `VisibilityUnexplainedBlankCells=[]`, and
  `status_counts.visibility_zero=13`.
- Process cleanup:
  no launched `cdb` or `clash95_hd_surfdump_20260429_140916` process remained
  after the run.
- Screenshot artifact:
  `captures\cdb-surface-dump-20260429-140916\surface.png`.

## No-Popup Map Evidence Matrix, 2026-04-29

- Added `tools\no_popup_map_evidence_matrix.py`.
- Purpose:
  print one compact no-popup HD map summary that pairs the freshest normal
  `VisibilityExplainedGate` pass with the freshest forced-visible
  `ForcedVisibleGate` pass.
- Validation command:
  `python tools\no_popup_map_evidence_matrix.py --normal-run captures\cdb-surface-dump-20260429-140916 --forced-run captures\cdb-surface-dump-20260429-135242 --require-pass --write-json captures\cdb-surface-dump-20260429-140916\no-popup-map-evidence-matrix.json`.
- Result:
  `PASS`.
- Normal row:
  `captures\cdb-surface-dump-20260429-140916`, 13 active blank cells, zero
  unexplained blanks, `visibility_zero=13`.
- Forced-visible row:
  `captures\cdb-surface-dump-20260429-135242`, zero active blank cells,
  54 `SURFDUMP_VEDGE_VISRET`, 54 `SURFDUMP_VEDGE_POST`, 54 nonzero visibility
  returns, 54 nonblack post samples, `map0=[10,17]`.
- Auto-select command:
  `python tools\no_popup_map_evidence_matrix.py --require-pass`.
- Auto-select result:
  also `PASS`, selecting the same two runs.
- Markdown report:
  `captures\no-popup-map-evidence-current.md`.
- Markdown validation:
  `Select-String` found `Overall: PASS`, `20260429-140916`,
  `20260429-135242`, and both `surface.png` screenshot references in the saved
  report.

## CDB-Only Right-Bottom UI Policy, 2026-04-30

- User direction: use CDB-only proof for current Clash95 HD work.
- Updated `AGENTS.md` and `CLASH95_ENGINE_VIEWPORT_PATCH_NOTES.md` with the
  same CDB-only policy for right-bottom UI work.
- Added/kept `probes/cdb/ui/clash95_right_bottom_ui_probe.cdb` as the right-bottom UI probe
  target, but it must be run through a CDB-only launcher or hidden-desktop
  harness.
- Added/kept `tools\right_bottom_ui_bounds.py` as the screenshot-side right
  bottom UI analyzer. Baseline JSON:
  `captures\right-bottom-ui-bounds-baseline-20260429.json`.

- Reporting rule:
  after every completed task, show the user a current UI screenshot artifact.
  For CDB-only work, prefer a fresh reconstructed `surface.png`; for docs-only
  work, reuse the latest relevant UI capture and say it is reused.

## Border Frame And Bottom Tooltip Investigation, 2026-04-30

- User selected the next target:
  recover the gameplay border frame and bottom tooltip/status area.
- Spawned three investigation lanes and wrote markdown reports:
  - `reports\border-frame-recovery.md`
  - `reports\bottom-tooltip-recovery.md`
  - `reports\border-tooltip-cdb-validation.md`
- Current shared conclusion:
  the HD 12x9 map drawing path is already proven by no-popup CDB evidence; the
  missing frame/tooltip is now a UI composition, draw-order, anchor, or present
  rectangle problem.
- Highest-value static/runtime candidates:
  - `sub_418700` at VA `00418700`, file offset `0x017B00`, as the full map
    redraw and current HD present-bounds owner.
  - `dword_526990`, called from the `sub_418700` path, as a possible
    post-map UI/frame callback that must be identified at runtime.
  - `UI_DrawUnitInfoPane` at `00419F70`, file offset `0x019370`, as a bottom
    tooltip/status candidate.
  - text helpers `0040BE50`, `0040C150`, and `0040BEE0`.
  - right/action/status UI cluster `004347A0..00435620`.
  - generic panel/notification candidates `004438A0`, `00445360`, `00447330`,
    and `00447610`.
- Added CDB-only probe infrastructure before the target pivot:
  - `scripts\cdb\run_cdb_surface_dump.ps1` now accepts `-ExtraProbeTemplate` and refuses
    extra templates with a standalone `g` command.
  - `probes/cdb/ui/clash95_right_bottom_ui_extra.cdb` is an injectable extra probe for the
    right-bottom/action/status cluster.
  - `scripts\cdb\run_cdb_right_bottom_ui_probe.ps1` wraps the no-popup surface dump route
    and counts `RBUI_*` markers.
- Required next proof:
  add a filtered `probes/cdb/ui/clash95_border_tooltip_extra.cdb` plus
  `tools\border_tooltip_summary.py`, run them through the hidden-desktop
  CDB/no-popup surface-dump path, and include the fresh `surface.png` UI
  screenshot artifact in the report.

## Border/Tooltip CDB Extra Probe, 2026-04-30

- Implemented `probes/cdb/ui/clash95_border_tooltip_extra.cdb` as a CDB-only extra probe for
  the hidden-desktop `scripts\cdb\run_cdb_surface_dump.ps1 -ExtraProbeTemplate` path.
- Implemented `tools\border_tooltip_summary.py` to summarize border/tooltip
  markers and measure fixed UI regions in reconstructed 800x600 surface PNGs.
- Hardened `scripts\cdb\run_cdb_surface_dump.ps1` extra-probe placeholder expansion:
  PowerShell breakpoint-ID arithmetic now emits `29,30,31` correctly, and the
  probe can late-enable only filtered text breakpoints while keeping the very
  hot present breakpoint disabled.
- Extra-probe runtime evidence:
  `captures\cdb-surface-dump-20260430-111545` reached `SURFDUMP_PLAYGAME` and
  `BORDER_FULLREDRAW_ENTER` on the hidden desktop. It reported an 800x600 map
  surface and `d526990=00000000` at redraw entry, then timed out before
  `SURFDUMP_READY`; no game AV was observed.
- Follow-up extra-probe attempts:
  `captures\cdb-surface-dump-20260430-112121` and
  `captures\cdb-surface-dump-20260430-113904` timed out in the startup/AVI
  route before menu forcing, with no `SURFDUMP_MAIN_HIT`. This looks like the
  known hidden-desktop full-startup brittleness rather than a map patch crash.
- Fresh current UI screenshot artifact:
  baseline no-extra hidden CDB dump
  `captures\cdb-surface-dump-20260430-114459` passed in 11 seconds, dumped an
  800x600 `surface.png`, and the visibility gate explained all 13 blank active
  cells as `visibility_zero`.
- Border/tooltip summaries:
  `captures\cdb-surface-dump-20260430-111545\border-tooltip-summary.md` and
  `captures\cdb-surface-dump-20260430-114459\border-tooltip-summary.md`.
- Current inference:
  the missing border frame/bottom tooltip is not a tile-coverage failure.
  `d526990` being null at the full redraw entry is now the strongest next
  runtime lead; the next probe should identify who initializes or calls through
  that pointer/state before patching draw rectangles.

## dword_526990 One-Shot Probe, 2026-04-30

- Implemented `probes/cdb/castle/clash95_d526990_extra.cdb` for the hidden-desktop
  `scripts\cdb\run_cdb_surface_dump.ps1 -ExtraProbeTemplate` path.
- The probe avoids hot present hooks. It logs:
  - hardware writes to `00526990`;
  - `sub_418700` entry at `00418700`;
  - sibling state check at `00418784` for `dword_526994`;
  - fallback-loop branch at `004189AD` and `00418A02`;
  - callback test/call/after points at `004187A0`, `004187A9`, and
    `004187AF`.
- Implemented `tools\d526990_summary.py` to summarize CDB marker counts,
  callback values, write values, and `dword_526994` values.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-d526990 -RunSeconds 240 -ExtraProbeTemplate .\probes/cdb/castle/clash95_d526990_extra.cdb`.
- Result:
  `captures\cdb-surface-dump-20260430-115605` passed on the hidden desktop,
  dumped an 800x600 `surface.png`, and exited after host
  `ReadProcessMemory`.
- dword evidence:
  3 full-redraw entries, 3 callback tests, 0 callback calls, 0 writes to
  `00526990`, `callback=00000000`, and `flag526994=00000000` throughout the
  observed gameplay redraws.
- Branch evidence:
  `sub_418700` always took the fallback loop path controlled by
  `dword_526994=0`, then tested the null callback and skipped the
  `call dword ptr [00526990]`.
- Current inference:
  the callback is not merely clipped or misplaced; in this loaded gameplay
  route it is not installed. Next work should statically find writers/xrefs for
  `00526990` and `00526994`, then probe their owning setup path or game state.

## dword_526990/dword_526994 Static Xrefs And Setup Probe, 2026-04-30

- Ghidra export text did not contain useful `00526990` / `00526994` matches.
- CDB byte-pattern search on the original executable found `00526990` only at
  `004187A2` and `004187AB`, the `sub_418700` optional callback test/call.
- CDB byte-pattern search found `00526994` references at `00418786`,
  `00418AF3`, `00423783`, `004237B5`, `004237F4`, `00423B13`, and
  `00423B55`.
- Disassembly identifies the likely `00526994` setup owners:
  - `00423760`: saves the old flag, sets `00526994=1`, calls `sub_418700`,
    restores the old flag, then calls `sub_418700` again.
  - `00423B00`: sets `00526994=1` and calls `sub_418700`.
  - `00423B40`: clears `00526994=0` and calls `sub_418700`.
- Added CDB-only setup probes:
  `probes/cdb/castle/clash95_d526994_setup_extra.cdb` and
  `probes/cdb/castle/clash95_d526994_setup_min_extra.cdb`.
- Extended `tools\d526990_summary.py` to count the new `D526994_*` markers.
- Runtime attempts:
  - `captures\cdb-surface-dump-20260430-121113`: hardware-watchpoint version,
    timed out before `SURFDUMP_MAIN_HIT`.
  - `captures\cdb-surface-dump-20260430-132217`: software-breakpoint version,
    timed out before `SURFDUMP_MAIN_HIT`.
  - `captures\cdb-surface-dump-20260430-133012`: minimal setup probe, timed out
    before `SURFDUMP_MAIN_HIT`.
- None of the setup attempts observed a game AV or owner marker. Current
  interpretation: the hidden-desktop full-startup/AVI route is stalling before
  menu routing, so the next probe should instrument startup/menu-route progress
  before changing UI patch bytes.
- Current UI screenshot artifact remains:
  `captures\cdb-surface-dump-20260430-115605\surface.png`.

## Startup-Stall Probe And dword_526994 Rerun, 2026-04-30

- Added combined extra probe:
  `probes/cdb/startup/clash95_startup_stall_d526994_extra.cdb`.
- Added parser:
  `tools\startup_stall_summary.py`.
- Full-startup diagnostic command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-startup-d526994 -RunSeconds 180 -ExtraProbeTemplate .\probes/cdb/startup/clash95_startup_stall_d526994_extra.cdb`.
- Full-startup result:
  `captures\cdb-surface-dump-20260430-142129` timed out. It reached
  `STARTUP_UI_AVI_CALL tag=logo`, `STARTUP_VIDEO_IN_ENTRY`, and
  `STARTUP_VIDEO_AFTER_MODE_BEGIN`, then did not return to `UI_StartAnims` or
  reach `SURFDUMP_MAIN_HIT`. No AV was observed. This localizes the no-skip
  hidden-desktop stall to the logo `Video_Avi_playIn` path.
- Sleep-fast-forward rerun command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-startup-d526994 -RunSeconds 120 -ExtraProbeTemplate .\probes/cdb/startup/clash95_startup_stall_d526994_extra.cdb`.
- Sleep-fast-forward result:
  `captures\cdb-surface-dump-20260430-145646` passed, dumped an `800x600`
  `surface.png`, and preserved the normal visibility explanation gate.
- Startup route evidence:
  17 startup rows, `STARTUP_UI_STARTANIMS_RETURN`, 2 `SURFDUMP_MAIN_HIT` rows,
  2 `SURFDUMP_PLAYGAME` rows, 1 `SURFDUMP_READY`, and 0 AV rows.
- `00526994` evidence:
  3 `D526994_MIN_CALLBACK_TEST` rows, 0 owner entries at `00423760`,
  `00423B00`, or `00423B40`, `callback=00000000`, and
  `flag526994=00000000`.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260430-145646\surface.png`.
- Current inference:
  the sleep-fast route is suitable for no-popup setup-owner probing, but the
  current load-slot gameplay route does not invoke the static `00526994` owner
  cluster. Next work should find callers/xrefs for `00423760`, `00423B00`, and
  `00423B40`, then route or force the game state that reaches one of them.

## dword_526994 Owner Route Trigger, 2026-04-30

- Static caller scan on `C:\Clash\clash95.exe` found:
  - `00423760`: one direct call at `004087C8`.
  - `00423B00`: one direct call at `0040A5EE`.
  - `00423B40`: one direct call at `0040A51A`.
  - `00423B00` and `00423B40` are both branches inside `sub_40A500`; the
    initial `PlayGame` setup calls `sub_40A400` at `0040B7AE` and
    `sub_40A500` at `0040B7B3`.
- Added `probes/cdb/castle/clash95_d526994_owner_route_extra.cdb`.
  It logs `sub_40A490`, `sub_40A500`, owner branches, owner entries, and the
  `sub_418700` callback test. In the `PlayGame` setup path it applies a
  debugger-only one-shot state nudge before `0040B7B3`:
  `dword_511B58=-1` and `dword_514194=0`, so the natural `sub_40A500` branch
  reaches `sub_423B40`.
- Added parser `tools\d526994_owner_route_summary.py`.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-d526994-owner-route -RunSeconds 120 -ExtraProbeTemplate .\probes/cdb/castle/clash95_d526994_owner_route_extra.cdb`.
- Result:
  `captures\cdb-surface-dump-20260430-224749` passed on the hidden desktop,
  generated a fresh 800x600 `surface.png`, and produced parser output
  `owner_count=1 route_count=8 ready=True av_count=0`.
- Key CDB rows:
  - `D526994_ROUTE_FORCE_423B40 ... selected_before=-1 prior_before=-1`.
  - `D526994_ROUTE_40A500_ENTRY ... selected=-1 prior=0`.
  - `D526994_ROUTE_423B40_CALL ... selected=-1 prior=0`.
  - `D526994_OWNER_423B40_ENTRY ret=0040a51f callback=00000000 flag526994=00000000 selected=-1 prior=0`.
- Interpretation:
  the owner cluster can be triggered under CDB, but this forced route only
  exercises the clear-highlight owner (`00423B40`) and still leaves
  `dword_526990` null. Border-frame/bottom-tooltip recovery should next trace
  `sub_40A400`, `sub_419D80`, and `dword_511D40` descriptor/bounds setup
  rather than patching `dword_526994` blindly.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260430-224749\surface.png`.

## dword_511D40 Descriptor Trace, 2026-05-06

- Added CDB-only extra probe:
  `probes/cdb/ui/clash95_descriptor_trace_extra.cdb`.
- Added parser:
  `tools\descriptor_trace_summary.py`.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-descriptor-trace -RunSeconds 120 -ExtraProbeTemplate .\probes/cdb/ui/clash95_descriptor_trace_extra.cdb`.
- Result:
  `captures\cdb-surface-dump-20260506-092608` passed on the hidden desktop
  and dumped an 800x600 `surface.png`.
- Candidate:
  `C:\ClashTests\cdb-descriptor-trace\clash95_hd_surfdump_20260506_092608.exe`
  with SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Parser command:
  `python tools\descriptor_trace_summary.py captures\cdb-surface-dump-20260506-092608\cdb-surface-dump.log --write-json captures\cdb-surface-dump-20260506-092608\descriptor-trace-summary.json --write-md captures\cdb-surface-dump-20260506-092608\descriptor-trace-summary.md --require-ready --require-drawn-511d40`.
- Parser result:
  `ready=True av_count=0 scanned_511d40=6 drawn_511d40=6 skipped_511d40=0`.
- Key rows:
  `DESC_40A400_ENTRY` reported `render=0a07edb0`,
  `map_surface=0a07edb0`, and `sz=(800,600)`. The six `dword_511D40`
  descriptors at `(416,400)`, `(480,400)`, `(544,400)`, `(416,432)`,
  `(480,432)`, and `(544,432)` all reached `004191F0` and the first present
  point with those destination coordinates. No `DESC_SKIP_X640` rows fired.
- Image-side checks:
  `tools\right_bottom_ui_bounds.py` passed against the fresh surface.
  `tools\border_tooltip_summary.py --require-ready` showed the screenshot still
  has a partially black right/bottom region, but this run did not include the
  border-tooltip marker set.
- Classification:
  `dword_511D40` is a native 3x2 descriptor cluster that draws successfully.
  The missing HD lower-right border/tooltip is not caused by this list's
  descriptor bounds, render target selection, or `sub_419D80` x clipping. The
  next target is the action/status/bottom-pane path around `004347A0`,
  `00434E20`, `00435280`, `00435500`, and `UI_DrawUnitInfoPane` at `00419F70`.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-092608\surface.png`.

## Hover/Selection UI Probe, 2026-05-06

- Added extra CDB probe:
  `probes/cdb/ui/clash95_hover_selection_ui_extra.cdb`.
- Added parser:
  `tools\hover_selection_ui_summary.py`.
- Static checks:
  `tools\wiki_lint.py` passed, the parser compiled with bundled Python, the
  extra probe contains no standalone `g`, and `C:\Clash\clash95.exe` still
  matches SHA-256
  `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`.
- Runtime command shape:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-hover-selection -RunSeconds 150 -ExtraProbeTemplate .\probes/cdb/ui/clash95_hover_selection_ui_extra.cdb`.
- First run:
  `captures\cdb-surface-dump-20260506-093846` passed and produced a normal
  800x600 `surface.png`, but the hover setter did not fire because a breakpoint
  at `00406FA0` was replaced by the harness redraw breakpoint.
- Fix:
  moved the hover setter to `0040AE11`, the call site immediately before
  `sub_406FA0`, so it no longer collides with the harness.
- Negative forced-hover evidence:
  `captures\cdb-surface-dump-20260506-094226`,
  `captures\cdb-surface-dump-20260506-094449`,
  `captures\cdb-surface-dump-20260506-100556`,
  `captures\cdb-surface-dump-20260506-100727`, and
  `captures\cdb-surface-dump-20260506-100922` all reached `SURFDUMP_READY`
  but failed the map coverage gate after forced hover moved scroll to
  `(35,51)`.
- Final parser result for
  `captures\cdb-surface-dump-20260506-100922`:
  `ready=True av_count=0 force_states=4 entries=0 presents=0 native_clip_rows=0`.
- Forced states in the final run:
  `map_hover (320,300)`, `action_grid_hover (474,114)`,
  `action_box_hover (320,388)`, and `safe_center_hold (320,300)`.
- Runtime state:
  every forced-state row had `d532218=00000000`, `selected=0`, `action=0`, and
  `d532220=0`. No `HOVSEL_PANEL_DRAW`, `HOVSEL_GRID_DRAW`,
  `HOVSEL_STATUS_DRAW`, `HOVSEL_ACTION_BOX`, `HOVSEL_UNITINFO_ENTRY`, text, or
  filtered present rows fired.
- Image-side measurement on the negative artifact:
  `right_bottom_ui_bounds.py` passed as an image parser, but the screenshot is
  mostly black after the forced scroll. It should be used as scroll/route
  evidence, not as a clean map-rendering baseline.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-100922\surface.png`.
- Classification:
  the target bottom/right UI is skipped by state/route in the current
  load-slot path. The probe did not find evidence that those functions draw and
  then get clipped or overwritten. The next proof should avoid mouse forcing
  and trace the owner state that sets `dword_532218` / enters `sub_435BC0`.

## Passive Action Panel Route Probe, 2026-05-06

- Added extra CDB probe:
  `probes/cdb/castle/clash95_action_panel_route_extra.cdb`.
- Added parser:
  `tools\action_panel_route_summary.py`.
- Static checks:
  the extra probe contains no standalone `g`, the parser compiles with bundled
  Python, `tools\wiki_lint.py` passes, and `C:\Clash\clash95.exe` still
  matches SHA-256
  `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`.
- Static correction:
  CDB disassembly of the original showed the owner caller starts at
  `004338E0`, with the actual `sub_435BC0` call at `00433914`. The probe was
  corrected to observe both addresses.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -RequireGameplay -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-action-panel-route -RunSeconds 150 -ExtraProbeTemplate .\probes/cdb/castle/clash95_action_panel_route_extra.cdb`.
- Final corrected run:
  `captures\cdb-surface-dump-20260506-102113` passed on the hidden desktop and
  produced an 800x600 `surface.png`.
- Candidate:
  `C:\ClashTests\cdb-action-panel-route\clash95_hd_surfdump_20260506_102113.exe`
  with SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Parser command:
  `tools\action_panel_route_summary.py captures\cdb-surface-dump-20260506-102113\cdb-surface-dump.log --write-json captures\cdb-surface-dump-20260506-102113\action-panel-route-summary.json --write-md captures\cdb-surface-dump-20260506-102113\action-panel-route-summary.md --require-ready`.
- Parser result:
  `ready=True av_count=0 owner_rows=0 panel_rows=0 draw_rows=0
  nonzero_owner_rows=0`.
- Key rows:
  `PlayGame -> 40A400 -> 40A500` fired with `selected=-1`, `prior=-1`,
  `d532218=00000000`, and `d5322c8=0`; no `004338E0`, `00433914`,
  `sub_435BC0`, hover/poll, grid-hit, draw, or write-watchpoint rows fired.
- Image-side evidence:
  `map_tile_coverage.py` classified the screenshot as likely gameplay and the
  visibility gate explained all 13 blank active cells as `visibility_zero`.
  `right_bottom_ui_bounds.py` still reports the bottom-right panel mostly
  black (`21.43%` nonblack), matching the missing UI symptom.
- Classification:
  the normal CDB load-slot route does not enter the action/status owner path.
  The current missing bottom-right UI is therefore still a route/state problem,
  not yet a proven anchor, clipping, or overwrite bug.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-102113\surface.png`.

## Controlled Action Panel State Route Probe, 2026-05-06

- Added controlled CDB-only extra probe:
  `probes/cdb/castle/clash95_action_panel_state_route_extra.cdb`.
- Extended parser:
  `tools\action_panel_route_summary.py` now recognizes `APSTATE_*` rows,
  owner-global write watches, debugger-only forced-call rows, and the
  one-iteration `sub_435BC0` exit latch.
- Static basis:
  CDB disassembly of `sub_435BC0` showed the loop sets `dword_532210=0`,
  calls `sub_435B90`, and exits when `dword_532210` changes. The probe uses
  that as a debugger-only safety latch if the owner path is reachable.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -RequireGameplay -ExtraProbeTemplate .\probes/cdb/castle/clash95_action_panel_state_route_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-action-panel-state-route -RunSeconds 180`.
- First pass:
  `captures\cdb-surface-dump-20260506-111052` passed and produced an 800x600
  `surface.png`, but skipped the forced owner call because `dword_532150=0`.
- Write-watch rerun:
  `captures\cdb-surface-dump-20260506-111214` passed and produced a fresh
  800x600 `surface.png`.
- Candidate:
  `C:\ClashTests\cdb-action-panel-state-route\clash95_hd_surfdump_20260506_111214.exe`
  with SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Parser command:
  `tools\action_panel_route_summary.py captures\cdb-surface-dump-20260506-111214\cdb-surface-dump.log --write-json captures\cdb-surface-dump-20260506-111214\action-panel-state-route-summary.json --write-md captures\cdb-surface-dump-20260506-111214\action-panel-state-route-summary.md --require-ready`.
- Parser result:
  `ready=True av_count=0 owner_rows=0 panel_rows=0 draw_rows=0
  nonzero_owner_rows=0`.
- Key row:
  `APSTATE_NUDGE_SKIPPED reason=no_owner selected=-1 prior=-1
  d532150=00000000 d532218=00000000 mouse=(320,166) scroll=(10,17)`.
- Negative write evidence:
  no `APSTATE_WRITE_532150`, `APSTATE_WRITE_53214C`, or
  `APSTATE_WRITE_532154` rows fired before `SURFDUMP_READY`.
- Visual evidence:
  the surface dump stayed a clean 800x600 gameplay frame. The visibility gate
  again explained all 13 active blank cells as `visibility_zero`.
- Classification:
  a controlled non-mouse owner/action-panel route is not reachable from the
  current load-slot state because the required owner global is never installed.
  The missing bottom-right action/status UI still looks like a missing
  state/owner route, not a draw clipping bug.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-111214\surface.png`.

## Castle Owner Setup Static/Runtime Probe, 2026-05-06

- Static recovery:
  `00433C20` is the writer for the missing owner globals. It writes
  `dword_532150`, derives and writes `dword_53214C`, allocates resources, then
  writes `dword_532154`. The later right-bottom owner/action path uses
  `004338E0 -> 00433914 -> sub_435BC0`.
- Dispatcher recovery:
  no direct `E8` calls to `00433C20` were found. A pointer reference at
  `0042270A` resolves to the castle screen command-99 descriptor setup:
  `00422709 mov ecx,00433C20`, `cmp esi,63h`, then the shared descriptor
  install path. This says the natural owner setup is castle-screen command
  `0x63`, not normal map loading.
- Added passive extra probe:
  `probes/cdb/castle/clash95_castle_owner_setup_extra.cdb`.
- Added parser:
  `tools\castle_owner_setup_summary.py`.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -NoSkipStartAnims -RequireGameplay -ExtraProbeTemplate .\probes/cdb/castle/clash95_castle_owner_setup_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-castle-owner-setup -RunSeconds 150`.
- Fresh hidden-desktop CDB evidence:
  `captures\cdb-surface-dump-20260506-121909` passed, produced an 800x600
  `surface.png`, and used candidate
  `C:\ClashTests\cdb-castle-owner-setup\clash95_hd_surfdump_20260506_121909.exe`
  with SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Patch-stage gate:
  `tools\patch_stage_report.py --require-current-hd-map` passed with
  118/118 expected bytes patched, 0 original, and 0 unexpected.
- Parser command:
  `tools\castle_owner_setup_summary.py captures\cdb-surface-dump-20260506-121909\cdb-surface-dump.log --require-surface-ready --json-out captures\cdb-surface-dump-20260506-121909\castle-owner-setup-summary.json --markdown-out captures\cdb-surface-dump-20260506-121909\CASTLE-OWNER-SETUP.md --surface-png C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260506-121909\surface.png`.
- Parser result:
  `SURFDUMP_READY` at line 189, `setup_rows=0`, `owner_global_rows=0`,
  `action_rows=0`, and `av_rows=0`.
- Coverage/visibility:
  `map_tile_coverage.py` reports a likely gameplay frame with 13 active blank
  cells; `visibility_coverage.py --require-explained` explains all 13 as
  `visibility_zero`.
- Current inference:
  the current load-slot route reaches gameplay but does not enter the castle
  screen dispatcher, command-99 owner setup, or the right-bottom owner/action
  path. Keep treating the missing bottom-right frame/tooltip as missing
  route/state until a CDB-only castle-screen entry proof says otherwise.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-121909\surface.png`.

## Castle Screen Invoke / Owner Setup Proof, 2026-05-06

- Added controlled CDB-only probe:
  `probes/cdb/castle/clash95_castle_screen_invoke_extra.cdb`.
- Corrected the route naming:
  `00422180` is the full castle screen routine. It installs `00422020` as the
  castle render hook. Command `0x63` is installed at `00422709` with callback
  `00433C20`.
- Added harness support:
  `scripts\cdb\run_cdb_surface_dump.ps1 -SkipMapValidation` skips map tile/visibility
  analysis for non-map UI surfaces while still converting raw surface memory to
  PNG and writing normal run summaries.
- First full-startup attempt:
  `captures\cdb-surface-dump-20260506-140452` reached the castle route and
  proved `00433C20` wrote `dword_532150`, `dword_53214C`, and `dword_532154`,
  but timed out after a write-watch resume (`SetContext failed 0x80070005`).
- Successful hidden-desktop command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\probes/cdb/castle/clash95_castle_screen_invoke_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-castle-screen-invoke -RunSeconds 120`.
- Fresh evidence:
  `captures\cdb-surface-dump-20260506-141239` passed with host-side
  `ReadProcessMemory`, no AV rows, and candidate
  `C:\ClashTests\cdb-castle-screen-invoke\clash95_hd_surfdump_20260506_141239.exe`
  SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Patch-stage gate:
  `tools\patch_stage_report.py --require-current-hd-map` passed with 118/118
  expected bytes patched and 0 unexpected bytes.
- Parser command:
  `tools\castle_owner_setup_summary.py captures\cdb-surface-dump-20260506-141239\cdb-surface-dump.log --require-surface-ready --require-owner-setup --json-out captures\cdb-surface-dump-20260506-141239\castle-screen-invoke-summary.json --markdown-out captures\cdb-surface-dump-20260506-141239\CASTLE-SCREEN-INVOKE.md --surface-png C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260506-141239\surface.png`.
- Parser result:
  `ready_line=222`, `setup_rows=4`, `owner_global_rows=4`, `action_rows=0`,
  and `av_rows=0`. The route observed `CASTLE_DESCRIPTOR_INSTALL_42257E
  callback=00433c20`, `CASTLE_OWNER_SETUP_433C20`, and writes to `00532150`,
  `0053214C`, and `00532154`.
- UI bounds:
  `tools\right_bottom_ui_bounds.py` on the castle screenshot reported
  `bottom-tooltip` nonblack coverage `92.623%` and `right-banner` nonblack
  coverage `96.836%`.
- Current inference:
  authentic bottom/castle UI assets are present on the native 640x480 castle
  screen surface. The current 800x600 gameplay map route still does not
  naturally install the owner/action state. Next proof should safely invoke or
  resume into `004338E0 -> 00433914 -> sub_435BC0` after owner setup and check
  whether that route can draw on the HD gameplay surface.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-141239\surface.png`.

## Post-Owner Action Panel Proof, 2026-05-06

- Added/refined CDB-only probe:
  `probes/cdb/map/clash95_post_owner_action_extra.cdb`.
- Fixes during this run:
  replaced hardware `ba` watchpoints with software breakpoints, short-returned
  from `00433C20` after `dword_532154`, moved the dump trigger to `00433919`
  after `sub_435BC0`, and entered at `0043390F` to avoid the `004338E0`
  timing/presentation prelude while still executing the live owner load and
  `00433914 -> sub_435BC0`.
- Successful hidden-desktop command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\probes/cdb/map/clash95_post_owner_action_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-post-owner-action -RunSeconds 120`.
- Fresh evidence:
  `captures\cdb-surface-dump-20260506-175108` passed, wrote an 800x600
  `surface.png`, used candidate
  `C:\ClashTests\cdb-post-owner-action\clash95_hd_surfdump_20260506_175108.exe`,
  and reported candidate SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Parser command:
  `tools\action_panel_route_summary.py captures\cdb-surface-dump-20260506-175108\cdb-surface-dump.log --write-json captures\cdb-surface-dump-20260506-175108\post-owner-action-summary.json --write-md captures\cdb-surface-dump-20260506-175108\POST-OWNER-ACTION.md --require-ready --require-owner`.
- Parser result:
  `ready=True av_count=0 owner_rows=11 panel_rows=6 draw_rows=5
  nonzero_owner_rows=13`.
- Key rows:
  `APPOST_ACTION_CALL skip_prelude=1`,
  `APPOST_433914_CALL_435BC0`, `APPOST_OWNER_435BC0_ENTRY`,
  `APPOST_WRITE_532218`, `APPOST_PANEL_DRAW_4347A0`,
  `APPOST_GRID_DRAW_434E20`, `APPOST_STATUS_DRAW_435280`,
  `APPOST_ACTION_BOX_435500`, and `APPOST_SURFDUMP_READY`.
- Patch-stage gate:
  `tools\patch_stage_report.py --require-current-hd-map` passed with 118/118
  expected bytes patched and zero original/unexpected selected bytes.
- Visual result:
  `tools\right_bottom_ui_bounds.py` measured `bottom-tooltip` at `83.256%`
  nonblack and `right-bottom-panel` at `21.43%` nonblack. The action-box row
  reports `render=0051d4c0` while `map_surface=0a57edb0`, making the next
  target render-target/copyback recovery for the right-bottom panel.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-175108\surface.png`.

## Action-Box Redirect/Copyback Negative Proof, 2026-05-06

- Extended `probes/cdb/map/clash95_post_owner_action_extra.cdb` with CDB-only
  `APREDIR_*` breakpoints around `00435500`, `00435532`, `0043553F`,
  `00435569`, `00435D93`, `00435D9E`, and `00435DA5`.
- Extended `tools\action_panel_route_summary.py` so redirect/copyback rows are
  counted and reported in generated summaries.
- First hidden-desktop command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\probes/cdb/map/clash95_post_owner_action_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-post-owner-action -RunSeconds 120`.
- Redirect-only evidence:
  `captures\cdb-surface-dump-20260506-180501` passed with no AV rows,
  candidate SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`,
  and `surface.png` SHA-256
  `DA9F920C95CC6C38B027CC2CC5ADF341579714B28EA345F99A770D76108EFE58`.
- Redirect rows:
  `APREDIR_SET_MAP_TARGET`, `APREDIR_AFTER_BACKUP_COPY`,
  `APREDIR_BEFORE_RESTORE`, and `APREDIR_AFTER_ACTION_BOX` fired. Samples at
  `(586,528)`, `(672,528)`, and `(736,528)` stayed
  `map=(c1,01,01)` while scratch-like samples were `(00,66,93)`.
- Copyback evidence:
  `captures\cdb-surface-dump-20260506-180755` added
  `APREDIR_COPYBACK_SET_MAP_TARGET` before the `00435D93 -> 00405020`
  post-action call and `APREDIR_COPYBACK_AFTER_CALL` after it. The run passed
  with no AV rows and produced the same raw and PNG hashes as the redirect-only
  run.
- Visual result:
  `tools\right_bottom_ui_bounds.py` still measured `right-bottom-panel` at
  `21.43%` nonblack, `bottom-tooltip` at `83.256%` nonblack, and fully black
  `r8c10` / `r8c11`. `tools\map_tile_coverage.py` still reported
  `blank=7`: `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, `r8c11`.
- Patch-stage gate:
  `tools\patch_stage_report.py --require-current-hd-map` passed on
  `C:\ClashTests\cdb-post-owner-action\clash95_hd_surfdump_20260506_180755.exe`
  with 118/118 selected bytes patched and zero unexpected selected bytes.
- Interpretation:
  simple `00435500` render-target redirection and `00435D93 -> 00405020`
  copyback redirection do not recover the right-bottom cells. The remaining
  blank region should be investigated as a per-tile visibility/terrain draw
  question in the same post-owner action route, not promoted as a render-target
  production patch.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-180755\surface.png`.

## Post-Owner Tile Visibility Proof, 2026-05-06

- Added `probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb`, a CDB-only post-owner
  action route probe that emits focused `APVIS_CELL` rows for the seven
  currently blank active cells:
  `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, and `r8c11`.
- Extended `tools\visibility_coverage.py` to parse focused `APVIS_CELL` rows
  and the base `SURFDUMP_VEDGE_*` draw-time visibility rows.
- Successful clean command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -ExtraProbeTemplate .\probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-post-owner-visibility -RunSeconds 120`.
- Fresh clean evidence:
  `captures\cdb-surface-dump-20260506-190037` passed hidden-desktop CDB,
  dumped an 800x600 post-owner action surface, and used candidate SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Route parser:
  `tools\action_panel_route_summary.py --require-ready --require-owner`
  reports `ready=True`, `av_count=0`, `owner_rows=11`, `panel_rows=6`,
  `draw_rows=5`, and `nonzero_owner_rows=13`.
- Visual/bounds result:
  `tools\right_bottom_ui_bounds.py` still measures `bottom-tooltip` at
  `83.256%` nonblack and `right-bottom-panel` at `21.43%` nonblack. The map
  coverage remains a gameplay-like 800x600 frame with blank active cells
  `r6c10`, `r6c11`, `r7c10`, `r7c11`, `r8c0`, `r8c10`, and `r8c11`.
- Visibility result:
  `tools\visibility_coverage.py --require-explained` passed. All seven blank
  cells are classified as `visibility_zero`, with zero unexplained blanks.
  Focused rows show `byte=00`, `hit=00`, and surface samples
  `sample=01 center_sample=01` for each target cell.
- Draw-time attempt:
  `captures\cdb-surface-dump-20260506-185450` armed base `SURFDUMP_VEDGE_*`
  rows and proved the target cells take the `SURFDUMP_VEDGE_CLEAR
  reason=vis_zero` path with post samples `01`, but the run dumped before the
  post-owner route and is a timing-intrusive draw-time diagnostic, not the
  preferred visual baseline.
- Failed combined attempt:
  `captures\cdb-surface-dump-20260506-185733` suppressed the base dump while
  hot draw breakpoints were armed, but timed out before a post-owner dump.
  Do not use that suppression pattern as the default route.
- Interpretation:
  the right/bottom dark cells in the post-owner action capture are explained by
  save visibility/fog state, not by missing 12x9 loops, present bounds, or the
  `00435500` action-box copyback path. Next proof should be debugger-only
  forced visibility for exactly these cells to show they fill when visibility
  permits, without turning visibility forcing into a gameplay patch.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-190037\surface.png`.

## Post-Owner Seven-Cell Forced-Visible Proof, 2026-05-06

- Added `-PostOwnerForceVisibleSeven` to `scripts\cdb\run_cdb_surface_dump.ps1`. The switch
  injects only the seven target visibility bits through the base PlayGame CDB
  breakpoint before HD redraw, then leaves the post-owner route in
  `probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb` to dump the same 800x600 map
  surface.
- Added `tools\post_owner_forced_visible_summary.py`, a focused gate for the
  debugger-only proof. It requires `APPOST_FORCE_VISIBLE_SEVEN`,
  `APPOST_ACTION_CALL`, `APPOST_SURFDUMP_READY`, APVIS rows for all seven
  target cells, nonzero hits for those rows, and zero blank active cells in map
  coverage.
- Failed first attempt:
  `captures\cdb-surface-dump-20260506-191042` set a CDB gate but did not write
  visibility because a same-address breakpoint was redefined by the base
  PlayGame breakpoint.
- Failed second attempt:
  `captures\cdb-surface-dump-20260506-191408` wrote the visibility bytes but
  reused `@$t18`, which blocked the post-owner route state and allowed the base
  dump to win early. The capture is useful only as a harness failure.
- Successful hidden-desktop command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -PostOwnerForceVisibleSeven -ExtraProbeTemplate .\probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-post-owner-forced-visible -RunSeconds 120 -RequireGameplay`.
- Fresh proof:
  `captures\cdb-surface-dump-20260506-200426` passed with candidate SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Coverage result:
  `map_tile_coverage.py` reports `gameplay_frame_likely=True` and
  `blank_active_cells: none`.
- Focused gate:
  `tools\post_owner_forced_visible_summary.py --require-post-owner-forced-visible`
  passed. Log rows show exact forced bytes
  `new_x20b2=80`, `new_x21b2=80`, `new_x20b3=03`, `new_x21b3=03`,
  `new_x10b3=02`, and all seven `APVIS_CELL` hits are nonzero.
- Key APVIS samples:
  `r6c10 hit=80 sample=c1 center_sample=c0`,
  `r7c10 hit=01 sample=c1 center_sample=29`,
  `r8c0 hit=02 sample=a7 center_sample=7f`, and
  `r8c11 hit=02 sample=c1 center_sample=c0`.
- Interpretation:
  the current HD 12x9 map path fills the right/bottom cells when the save
  visibility permits them. The normal dark cells are therefore fog/unexplored
  state for this save, not a reason to patch map loops, present bounds, or
  action-box copyback.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-200426\surface.png`.

## Post-Owner Forced-Visible Harness Gate, 2026-05-06

- Wired `tools\post_owner_forced_visible_summary.py` into
  `scripts\cdb\run_cdb_surface_dump.ps1`. When `-PostOwnerForceVisibleSeven` is used, the
  harness now writes `post-owner-forced-visible-summary.json` /
  `post-owner-forced-visible-summary.txt`, includes the result in
  `summary.json` and `RUN-SUMMARY.md`, and fails the run if the focused gate
  reports missing rows, zero visibility hits, or remaining blank cells.
- Added a guard so `-PostOwnerForceVisibleSeven` cannot be combined with
  `-SkipMapValidation`.
- Fresh hidden-desktop command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -PostOwnerForceVisibleSeven -ExtraProbeTemplate .\probes/cdb/map/clash95_post_owner_tile_visibility_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-post-owner-forced-visible -RunSeconds 120 -RequireGameplay`.
- Fresh gated evidence:
  `captures\cdb-surface-dump-20260506-201114` passed with
  `Post-owner forced-visible gate: passed` in `RUN-SUMMARY.md`.
- Focused summary:
  `post-owner-forced-visible-summary.txt` reports `passed: True`,
  `gameplay_frame_likely: True`, `blank_active_cells: -`,
  `markers: force=1 done=1 action=1 ready=1`, and no missing or zero-hit
  cells.
- Current screenshot artifact:
  `captures\cdb-surface-dump-20260506-201114\surface.png`.

## Post-Owner Evidence Matrix, 2026-05-08

- Added `tools\post_owner_evidence_matrix.py`, a repo-only gate that pairs:
  - latest normal post-owner visibility-zero proof;
  - latest seven-cell post-owner forced-visible proof.
- Validation command:
  `python tools\post_owner_evidence_matrix.py --require-pass --write-json captures\post-owner-evidence-current.json --write-markdown captures\post-owner-evidence-current.md`.
- Result:
  overall `PASS`.
- Normal proof selected:
  `captures\cdb-surface-dump-20260506-190037`, with seven target blank cells
  and `visibility_status_counts={'visibility_zero': 7}`.
- Forced-visible proof selected:
  `captures\cdb-surface-dump-20260506-201114`, with zero blank active cells and
  gate counts `force=1 done=1 action=1 ready=1`.
- Current report:
  `captures\post-owner-evidence-current.md`.

## HD Map Smoke Matrix, 2026-05-08

- Added `tools\hd_map_smoke_matrix.py`, a repo-only smoke gate that combines:
  - current HD map patch-stage verification via `tools\patch_stage_report.py`;
  - post-owner normal/forced-visible evidence via
    `tools\post_owner_evidence_matrix.py`.
- Validation command:
  `python tools\hd_map_smoke_matrix.py --require-pass --write-json captures\hd-map-smoke-current.json --write-markdown captures\hd-map-smoke-current.md`.
- Result:
  overall `PASS`.
- Patch-stage proof:
  selected
  `C:\ClashTests\cdb-post-owner-forced-visible\clash95_hd_surfdump_20260506_201114.exe`,
  SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`,
  with `118/118` selected current HD map patch bytes patched.
- Evidence proof:
  reused normal run `captures\cdb-surface-dump-20260506-190037` and
  forced-visible run `captures\cdb-surface-dump-20260506-201114`.
- Current report:
  `captures\hd-map-smoke-current.md`.

## Fresh-Base HD Map Smoke Reproduction, 2026-05-08

- Added a `README.md` section named `Clash95 HD Map Smoke Reproduction`.
- The documented sequence starts from the verified user-owned
  `C:\Clash\clash95.exe`, writes a unique candidate to
  `C:\ClashTests\hd-map-smoke`, generates an old/new byte manifest with
  `tools\patch_stage_report.py --require-current-hd-map --write-json
  captures\patch-stage-current-hd-map.json`, and then runs
  `tools\hd_map_smoke_matrix.py --patch-exe <candidate>` against the archived
  normal/forced post-owner evidence pair.
- This is a documentation-only reproduction path for the current sandboxed run:
  no game, CDB, or external candidate build was launched here.
- Expected matrix result remains `patch_stage.status=pass`, `118/118` selected
  bytes patched, zero original/unexpected selected bytes, and
  `post_owner_evidence.status=pass`.

## HD Map Smoke Dry-Run Helper, 2026-05-08

- Added `scripts\smoke\prepare_hd_map_smoke_candidate.ps1`.
- Default mode is dry-run only. It prints the exact patch, manifest, and matrix
  commands; selects a unique candidate path under
  `C:\ClashTests\hd-map-smoke`; verifies the base SHA when
  `C:\Clash\clash95.exe` is accessible; and refuses candidate output under the
  repository unless `-AllowRepoCandidateDir` is explicitly passed.
- Validation:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\prepare_hd_map_smoke_candidate.ps1 -Json`
  passed, found `C:\Clash\clash95.exe`, and verified SHA-256
  `500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
- Guard validation:
  `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke\prepare_hd_map_smoke_candidate.ps1 -CandidateDir . -Json`
  failed as intended with a repository-output refusal.

## Patch Manifest Compare Helper, 2026-05-08

- Added `tools\patch_manifest_compare.py`.
- Added `tools\test_patch_manifest_compare.py`.
- The helper compares two `tools\patch_stage_report.py --write-json` outputs
  without reading executables, then reports metadata diffs, group diffs, added
  offsets, removed offsets, changed offsets, and any `original` / `unexpected`
  records.
- Validation:
  `python -m py_compile tools\patch_manifest_compare.py tools\test_patch_manifest_compare.py`
  passed.
- Regression test:
  `python tools\test_patch_manifest_compare.py` passed.
- Real archived comparison:
  `python tools\patch_manifest_compare.py captures\patch-stage-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-20260424.json captures\patch-stage-mapdraw-partial12-20260424.json --write-json captures\patch-manifest-compare-current-vs-partial12.json --write-markdown captures\patch-manifest-compare-current-vs-partial12.md --limit 8`
  passed and found three changed records: `0x017DFF`, `0x017EDB`, and
  `0x0E8DC0`.

## Current HD Map Evidence Index, 2026-05-08

- Added `captures\hd-map-evidence-current.md`.
- It links the current smoke matrix, post-owner evidence matrix,
  patch-manifest comparison report, normal/forced run summaries, and the two
  current surface PNG artifacts.
- Current interpretation recorded in the index:
  the current HD map path fills the right/bottom cells when visibility permits
  it; the normal black cells in this save are explained by fog/unexplored
  visibility, not by a remaining map-loop or present defect.

## Evidence Index Consistency Checker, 2026-05-08

- Added `tools\evidence_index_check.py`.
- Added `tools\test_evidence_index_check.py`.
- The checker parses a Markdown evidence index, verifies local Markdown links,
  verifies referenced image artifacts, and writes an optional JSON report.
- Validation:
  `python -m py_compile tools\evidence_index_check.py tools\test_evidence_index_check.py`
  passed.
- Regression test:
  `python tools\test_evidence_index_check.py` passed.
- Current index check:
  `python tools\evidence_index_check.py captures\hd-map-evidence-current.md --require-pass --write-json captures\hd-map-evidence-current-check.json`
  passed with `links=5`, `images=2`, `missing=0`, and
  `image_wrong_extension=0`.

## Castle Barracks UI Probe, 2026-05-11

- Added `probes/cdb/castle/clash95_castle_barracks_ui_extra.cdb` to trace the CDB-only
  post-owner castle action-panel path with barracks/addon-list diagnostics.
- Added `tools\castle_barracks_ui_summary.py` to parse `APBARRACKS_*` rows,
  count panel/grid/action-box markers, report selected addon ids, and fail when
  ready/panel markers or AV rows are missing.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\probes/cdb/castle/clash95_castle_barracks_ui_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-castle-barracks-ui -RunSeconds 120`.
- Fresh evidence:
  `captures\cdb-surface-dump-20260511-084202` passed on the hidden desktop,
  dumped an 800x600 surface, and used candidate
  `C:\ClashTests\cdb-castle-barracks-ui\clash95_hd_surfdump_20260511_084202.exe`
  with SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Parser result:
  `tools\castle_barracks_ui_summary.py --require-ready --require-panel`
  passed with `ready=True`, `panel=True`, `action_box=True`, `av_count=0`, and
  `last_selected_addon=0`.
- Key runtime rows:
  the route installed owner globals, entered `00433914 -> 00435BC0`, drew
  `004347A0`, `00434E20`, `00435280`, and `00435500`, and logged the available
  addon list as `(0,1,3,16,17,-1,-1,-1,-1,-1,-1,-1)`.
- Visual result:
  `captures\cdb-surface-dump-20260511-084202\surface.png` plus crops
  `castle-barracks-right-panel.png`, `castle-barracks-action-box.png`, and
  `castle-barracks-grid-area.png` show the route is live, but the right/bottom
  UI is still partly black on the HD surface.
- Current inference:
  the barracks/action UI problem is not a missing route. The strongest
  remaining lead is render-target/copyback recovery around `00435500`, where
  the action-box row reports `render=0051d4c0` while
  `map_surface=0a07ed90`.

## Castle Barracks Selected-Addon Copyback Trace, 2026-05-11

- Added `probes/cdb/castle/clash95_castle_barracks_select_extra.cdb`, a sibling of the baseline
  barracks probe that forces the selected addon index to `1` in memory and
  traces the action-box/copyback addresses `00435500`, `00435532`,
  `0043553F`, `00435569`, `00435D93`, `00435D9E`, and `00435DA5`.
- Extended `tools\castle_barracks_ui_summary.py` to count
  `APBARRACKS_SELECT_FORCED` and the action-box/copyback trace markers.
- First runtime attempt:
  `captures\cdb-surface-dump-20260511-134458` timed out because the probe used
  invalid CDB pseudo-register `$t20`. The timeout stack stopped at
  `004347A1`, proving this was a debugger-script issue, not a game crash.
- Corrected runtime attempts:
  `captures\cdb-surface-dump-20260511-134746` passed with copyback trace
  markers but did not force the selection because the guard register had
  already been used by the base probe. The final corrected run,
  `captures\cdb-surface-dump-20260511-134947`, passed with hidden desktop CDB,
  no AV rows, a host-read `800x600` surface dump, and selected addon `1`.
- Runtime command:
  `scripts\cdb\run_cdb_surface_dump.ps1 -UseDdrawProxy -FastForwardStartAnims -SkipMapValidation -ExtraProbeTemplate .\probes/cdb/castle/clash95_castle_barracks_select_extra.cdb -Stage gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch -CandidateDir C:\ClashTests\cdb-castle-barracks-ui -RunSeconds 120`.
- Fresh evidence:
  `captures\cdb-surface-dump-20260511-134947\RUN-SUMMARY.md` passed with
  candidate
  `C:\ClashTests\cdb-castle-barracks-ui\clash95_hd_surfdump_20260511_134947.exe`
  and candidate SHA-256
  `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`.
- Parser result:
  `tools\castle_barracks_ui_summary.py --require-ready --require-panel`
  passed with `ready=True`, `panel=True`, `action_box=True`, `av_count=0`,
  `APBARRACKS_SELECT_FORCED=1`, and `last_selected_addon=1`.
- Key runtime rows:
  `APBARRACKS_SELECT_FORCED` changed `dword_532220` to index `1`, after which
  `004347A0`, `00434E20`, `00435280`, and `00435500` all reported
  `selected_index=1 selected_addon=1`. Copyback trace rows show
  `00435D93` loads `eax=0051d4c0`, `00435D98` loads
  `edx=dword_53221c`, `00435DA0` calls `00405020`, and samples in the map
  surface remained `(c1,01,01)` while scratch-side samples were `(00,66,93)`.
- Static check:
  CDB disassembly of `C:\Clash\clash95.exe` confirmed `00435500` temporarily
  sets `dword_511230` to `0051D4C0`, draws the action-box rectangle, restores
  the prior render target at `00435569`, then the owner loop later calls
  `00405020` from `00435DA0` with `eax=0051D4C0` and
  `edx=dword_53221c`.
- Screenshot artifacts:
  `captures\cdb-surface-dump-20260511-134947\surface.png`,
  `captures\cdb-surface-dump-20260511-134947\castle-barracks-top-panel.png`,
  `captures\cdb-surface-dump-20260511-134947\castle-barracks-selected-card.png`,
  and
  `captures\cdb-surface-dump-20260511-134947\castle-barracks-bottom-actions.png`.
- Current inference:
  the barracks UI route is live and selectable under CDB. The remaining proof
  is whether a debugger-only manual row copy from the `0051D4C0` scratch/render
  area into the 800x600 `dword_5202E0` surface at `00435DA5` recovers any
  missing action-box pixels; if it does, the production patch should target
  copyback routing rather than panel draw logic.

## Castle Barracks UI Centering Proof, 2026-05-11

- User correction:
  castle/barracks UI should be centered in the 800x600 HD canvas, matching the
  already-centered 640x480 menu treatment.
- CDB-only proof:
  `captures\cdb-surface-dump-20260511-141143` passed after a debugger-side
  experiment copied the native 640x480 barracks surface into `0051D4C0`,
  cleared `dword_5202E0`, and copied the native layer back at `(80,60)`.
  Screenshot: `captures\cdb-surface-dump-20260511-141143\surface.png`.
- Patcher implementation:
  added `castle-ui-center-present` and stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter`.
  The hook overwrites only the first five bytes at VA `00435DA5`, jumps to
  DGROUP cave VA `0051316F`, performs the same 640x480 scratch/clear/center
  copy, restores `eax=00544CD8`, then resumes the original
  `mov ebx,00435B90; call Render_Present` sequence at `00435DAA`.
- Failed patch attempts:
  `captures\cdb-surface-dump-20260511-141708` corrupted `.idata` by using an
  import-section cave and failed with `c0000139`. The patch was moved out of
  `.idata`.
  `captures\cdb-surface-dump-20260511-142147` jumped to the wrong DGROUP VA
  (`0051216F`) due an RVA calculation error and AVed on zeros. The corrected
  VA is `0051316F`.
- Passing patch-stage run:
  `captures\cdb-surface-dump-20260511-142304` passed on the hidden desktop
  with no debugger-side centering markers, no AV rows, and candidate SHA-256
  `8BC179944C2859FB5C0A8B1E36A695D8A9371E0C975B80FA1092513AC53C89B8`.
- Parser result:
  `tools\castle_barracks_ui_summary.py --require-ready --require-panel`
  passed with `ready=True`, `panel=True`, `action_box=True`, `av_count=0`, and
  `last_selected_addon=1`.
- Screenshot artifact:
  `captures\cdb-surface-dump-20260511-142304\surface.png` shows the native
  castle/barracks UI layer centered at `(80,60)` inside the 800x600 dump.
- Remaining risk:
  this is a visual/presentation centering patch. Castle/barracks hitboxes and
  mouse coordinates still need an explicit `(80,60)` alignment proof before
  this can be considered interactive-complete.

## Castle Barracks Centered Hitbox Transform, 2026-05-11

- Implemented a new patch group:
  `castle-ui-centered-input`.
- New validation stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`.
- Patch intent:
  keep the centered `(80,60)` presentation from `castle-ui-center-present`, but
  temporarily subtract the same `(80,60)` offset from the logical mouse globals
  while the castle/barracks owner poll and descriptor hit-test code runs.
- Hook details:
  `00435B90` owner-poll entry jumps to DGROUP cave `00513220` and subtracts
  `80 << dword_54512C` / `60 << dword_54512C` from `dword_544CFC` and
  `dword_544D00`.
  `00435BB3` owner-poll exit jumps to cave `00513260` and restores the mouse
  globals before the original `pop edx; ret`.
  `00435DF5` descriptor hit-test call jumps to cave `005131C5`, applies the
  same temporary transform around `00419DC0`, restores `eax`, then returns to
  `00435DFA`.
- Runtime evidence:
  `captures\cdb-surface-dump-20260511-143741` passed on the hidden desktop
  with stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`.
  Candidate SHA-256:
  `BEC4674A98060928337F05CB967AEDBD2A800905389DBBE4990CF771C6DF19C8`.
- Parser result:
  `tools\castle_barracks_ui_summary.py --require-ready --require-panel`
  passed with `ready=True`, `panel=True`, `action_box=True`, `av_count=0`, and
  `last_selected_addon=1`.
- Patch-stage report:
  `tools\patch_stage_report.py` reports `126 patched, 0 original,
  0 unexpected`; `castle-ui-center-present` is `2/2` patched and
  `castle-ui-centered-input` is `6/6` patched.
- Screenshot artifact:
  `captures\cdb-surface-dump-20260511-143741\surface.png`.
- Remaining risk:
  this validates the patched bytes, centered screenshot, and no-crash route.
  The next proof should force centered screen coordinates over a real
  barracks/grid target and log the resulting hover/selection row, so the
  transform is proven as hitbox behavior rather than only as a safe wrapper.

## Castle Barracks Grid Hitbox Proof, 2026-05-11

- Added the missing grid hit-test wrapper to `castle-ui-centered-input`.
  Static trace showed the barracks grid helper `00435580` is reached from
  `00435A17`, after the descriptor hit-test wrapper restores the mouse. The
  production patch now wraps that call site too.
- New byte patches:
  `00435A17` file offset `0x034E17`, old `E8 64 FB FF FF`, new
  `E8 6E D8 0D 00`; DGROUP cave file offset `0x11148A`, VA `0051328A`,
  old `00 * 80`.
- Added `probes/cdb/castle/clash95_castle_barracks_hitbox_extra.cdb` and
  `tools\castle_barracks_hitbox_summary.py`.
- Focused proof run:
  `captures\cdb-surface-dump-20260511-145141` passed with hidden-desktop CDB,
  candidate SHA-256
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`, no AV
  rows, and screenshot
  `captures\cdb-surface-dump-20260511-145141\surface.png`.
- Hitbox evidence:
  the probe forced displayed/centered grid coordinate `(530,133)`, the
  owner-poll wrapper logged native `(450,73)`, the new `00435A17` grid wrapper
  called `00435580` with native `(450,73)`, and
  `APBARRACKS_HITBOX_GRID_RESULT result=0 expected=0` proved cell `0`.
- Parser result:
  `tools\castle_barracks_hitbox_summary.py --require-ready --require-grid-hit`
  passed with `grid_hit_ok=True`, `last_grid_entry=[450, 73]`,
  `last_grid_result=0`, and `av_count=0`.
- Patch-stage report:
  `tools\patch_stage_report.py` reports `128 patched, 0 original,
  0 unexpected`; `castle-ui-centered-input` is now `8/8` patched.
- Note:
  no selection-update marker was expected in this exact proof because selected
  index `0` was already active; the route ended with hover slot `0`, which is
  enough to prove the centered grid hitbox mapping.

## Castle Barracks Raw Click-Gate Hitbox Proof, 2026-05-11

- Added `probes/cdb/castle/clash95_castle_barracks_click_extra.cdb`.
- Extended `tools\castle_barracks_hitbox_summary.py` with
  `--require-raw-gate` and `--forbid-forced-gate`.
- Fresh hidden-desktop CDB run:
  `captures\cdb-surface-dump-20260511-150643`.
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`.
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-150643\surface.png`.
- The new probe still forces the displayed centered mouse coordinate
  `(530,133)` and the click-state flag, but it no longer rewrites `eax` at
  `00435A0E`. Instead, the raw `DD_IsFlipping(dword_544CD8)` result must pass.
- Parser result:
  `ready=True grid_hit_ok=True last_grid_entry=[450, 73] last_grid_result=0 raw_gate_ok=True forced_gate_count=0 selection_updates=0 av_count=0`.
- Key rows:
  `APBARRACKS_HITBOX_GRID_GATE raw_result=1 forced_result=none` and
  `APBARRACKS_HITBOX_GRID_RESULT result=0 expected=0 mouse=(450,73)`.
- Patch-stage report:
  `tools\patch_stage_report.py` reports `128 patched, 0 original,
  0 unexpected`; `castle-ui-centered-input` remains `8/8` patched.
- Interpretation:
  the centered barracks grid path now has CDB proof for the full chain:
  displayed coordinate `(530,133)`, raw click gate open without gate-forcing,
  temporary native transform to `(450,73)`, grid helper result `0`, and clean
  loop exit. The remaining interactive proof is a less synthetic input source
  or a populated nonzero slot/action button that causes an observable selection
  or action-state update.

## Castle Barracks Action Descriptor Proof, 2026-05-11

- Added `probes/cdb/castle/clash95_castle_barracks_action_click_extra.cdb`.
- Added `tools\castle_barracks_action_click_summary.py`.
- Fresh hidden-desktop CDB run:
  `captures\cdb-surface-dump-20260511-160221`.
- Stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-hitbox`.
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-160221\surface.png`.
- Parser result:
  `ready=True descriptor_click_ok=True action_exit_ok=True failure_exits=0 av_count=0`.
- Patch-stage report:
  `tools\patch_stage_report.py` reports `128 patched, 0 original,
  0 unexpected`; `castle-ui-center-present` is `2/2` patched and
  `castle-ui-centered-input` is `8/8` patched.
- Key rows:
  the centered displayed target `(161,501)` maps to native `(81,441)`, hits
  descriptor `0051519a` at native `(41,425)`, opens the click gate
  (`click_gate=1`), dispatches callback `00435620`, enters
  `00435620`, and sets `dword_532210` to exit the barracks loop.
- Important limitation:
  the first action-click attempts proved that the hidden-desktop/proxy route
  clears `dword_544D04` before descriptor `0051519a` is evaluated. The passing
  proof rearms only that click byte at `00419C47`, before the stock
  `004608F0` gate reads it. This proves centered descriptor identity and stock
  callback behavior, but it is still debugger-assisted input-state evidence.

## Castle Barracks Action Descriptor Pre-Gate Refinement, 2026-05-11

- Refined `probes/cdb/castle/clash95_castle_barracks_action_click_extra.cdb` so the click-state
  rearm happens at `00419C28`, after the action descriptor `0051519a` is
  identified but before the stock `00460900` and `004608F0` input gates run.
- Failed exploratory attempt:
  `captures\cdb-surface-dump-20260511-160850` tried a global `00419B80`
  descriptor-entry breakpoint. It timed out before `SURFDUMP_READY`, showing
  that hot descriptor breakpoints must be late-armed or avoided in normal
  hidden-desktop runs.
- Passing run:
  `captures\cdb-surface-dump-20260511-161212`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-161212\surface.png`.
- Parser result:
  `ready=True descriptor_click_ok=True action_exit_ok=True failure_exits=0 av_count=0`.
- Patch-stage report:
  `tools\patch_stage_report.py` reports `128 patched, 0 original,
  0 unexpected`; `castle-ui-center-present` is `2/2` patched and
  `castle-ui-centered-input` is `8/8` patched.
- Key rows:
  `APBARRACKS_ACTION_WIDGET_REARM_PRE_GATES desc=0051519a ... click_flag=00000001`;
  `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1`;
  `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620`;
  and `APBARRACKS_ACTION_CLICK_EXIT_SET ... action_state=1`.
- Current interpretation:
  the smallest stable CDB-only workaround is descriptor-local and pre-gate.
  The root cause is not the centered hitbox patch; it is the synthetic/proxy
  hidden-desktop input path losing `dword_544D04` before later descriptors in
  the list are evaluated.

## Castle Barracks CDB Harness Click Preservation, 2026-05-11

- Added `probes/cdb/castle/clash95_castle_barracks_click_consume_trace_extra.cdb` to run the
  action-descriptor click route without the descriptor-local rearm.
- Extended `tools\castle_barracks_action_click_summary.py` to recognize
  pre-gate rows and click-flag trace markers.
- Diagnostic run:
  `captures\cdb-surface-dump-20260511-162607` passed the surface dump but
  showed `0051519a` seeing `click_flag=00000000` and `button0=0x00`.
- Root cause:
  the shared surface-dump template breakpoint at `00419B80` was clearing
  `005451C0` and `00544D04` during post-gameplay descriptor walks, so the CDB
  harness consumed its own synthetic click before the barracks action
  descriptor.
- Changed `probes/cdb/render/clash95_surface_dump_probe.cdb` so that generic post-gameplay
  cleanup still runs for normal map dumps, but does not clear mouse button
  state once an extra UI probe has entered its active `$t18` phase.
- Passing run:
  `captures\cdb-surface-dump-20260511-162846`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-162846\surface.png`.
- Parser result:
  `ready=True descriptor_click_ok=True action_exit_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.
- Key rows:
  `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=0051519a ... click_flag=00000001 button0=0x80`;
  `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=0051519a click_gate=1`;
  `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=0051519a callback=00435620`;
  and `APBARRACKS_ACTION_CLICK_EXIT_SET ... action_state=1`.
- Patch-stage report:
  `captures\cdb-surface-dump-20260511-162846\patch-stage-report.json` reports
  `128 patched, 0 original, 0 unexpected`; `castle-ui-center-present` is
  `2/2` and `castle-ui-centered-input` is `8/8`.
- Current interpretation:
  the centered barracks action descriptor is proven under the CDB no-popup
  harness without a descriptor-local rearm. The remaining limitation is that
  the click state is still debugger-injected rather than manual DirectInput.

## Castle Barracks Second Action Descriptor, 2026-05-11

- Added `probes/cdb/castle/clash95_castle_barracks_second_action_extra.cdb`.
- Extended `tools\castle_barracks_action_click_summary.py` with
  `--expect-desc` and `--expect-callback`, plus `004356c0` callback markers.
- Fresh hidden-desktop CDB run:
  `captures\cdb-surface-dump-20260511-163846`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-163846\surface.png`.
- Target:
  displayed centered coordinate `(276,501)`, expected native `(196,441)`.
- Descriptor:
  `005151cf`, native origin `(156,425)`, callback `004356c0`.
- Parser result:
  `ready=True descriptor_click_ok=True action_exit_ok=False failure_exits=0 clickflag_writes=0 av_count=0`.
- Key rows:
  `APBARRACKS_ACTION_WIDGET_PRE_GATES desc=005151cf ... click_flag=00000001 button0=0x80`;
  `APBARRACKS_ACTION_WIDGET_CLICK_GATE_RET desc=005151cf click_gate=1 click_cb=004356c0`;
  `APBARRACKS_ACTION_DESCRIPTOR_CALLBACK desc=005151cf callback=004356c0`;
  `APBARRACKS_ACTION_CLICK_4356C0_ENTRY desc=005151cf`; and
  `APBARRACKS_ACTION_CLICK_4356C0_CHECK_RET check_result=0`.
- Patch-stage report:
  `captures\cdb-surface-dump-20260511-163846\patch-stage-report.json` reports
  `128 patched, 0 original, 0 unexpected`; `castle-ui-center-present` is
  `2/2` and `castle-ui-centered-input` is `8/8`.
- Interpretation:
  the second bottom action button proves the same centered input and stock
  gate/callback chain as the first action button. The stock callback rejects
  the current selected addon (`selected_addon=0`), so a future proof should
  select a compatible addon before clicking this descriptor if the goal is a
  visible callback-success branch.

## Castlecenter-All Interior Catalog, 2026-05-11

- Added patch stage
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`.
  It currently uses the same patch byte set as `castlecenter-hitbox` and keeps
  that older stage as the regression reference.
- Added `probes/cdb/castle/clash95_castle_interior_catalog_extra.cdb` plus parser
  `tools\castle_interior_catalog_summary.py`.
- Hidden-desktop CDB run:
  `captures\cdb-surface-dump-20260511-170708`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-170708\surface.png`.
- Parser:
  `ready=True surface_size=[640, 480] descriptors=7 commands=0x63,0x86,0x87,0x99,0x9C,0x9F,0xA6 av_count=0`.
- 800x600 requirement check:
  intentionally fails for this full castle overview route with
  `required 800x600 surface was not observed`.
- Current interpretation:
  the descriptor catalog is working, but full castle overview/interior routing
  still uses a native 640x480 surface. The next patch target is the separate
  `00422180` castle-screen surface/present path, not the already centered
  barracks `00435DA5` route.

## Castlecenter-All Barracks Success-Branch Proof, 2026-05-11

- Hidden-desktop CDB run:
  `captures\cdb-surface-dump-20260511-170759`.
- Probe:
  `probes/cdb/castle/clash95_castle_barracks_second_action_select1_extra.cdb`.
- Screenshot:
  `captures\cdb-surface-dump-20260511-170759\surface.png`.
- Candidate:
  `C:\ClashTests\cdb-castle-center-all\clash95_hd_surfdump_20260511_170759.exe`.
- Candidate SHA-256:
  `F7E3FE2D4411D586870A05549CBC35B331446D35E567A5347096150B16934434`.
- Patch-stage report:
  `128 patched, 0 original, 0 unexpected`; current HD map gate passed.
- Geometry:
  `centered_gate=PASS image=800x600 centered_nonblack=74.464% max_margin_nonblack=24.979%`.
- Action parser:
  `ready=True descriptor_click_ok=True action_exit_ok=False success_4356c0_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.
- Key proof:
  selected addon `1`, displayed action coordinate `(276,501)` mapped to native
  `(196,441)`, descriptor `005151cf` reached stock callback `004356c0`, and
  the success-branch marker was observed before the controlled dump exit.

## Castle Overview Gate And Barracks Probe Cleanup, 2026-05-12

- Kept the stable HD map stage at
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
- Kept castle/interior validation on
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all`;
  castle patches are still not part of the default HD map stage.
- Added `tools\castle_overview_gate.py`, a repo-only gate for full castle
  overview runs. It requires a ready castle catalog, no AV rows, all expected
  descriptor commands (`0x63`, `0x86`, `0x87`, `0x99`, `0x9C`, `0x9F`,
  `0xA6`), an 800x600 CDB-reported surface, and centered 800x600 PNG geometry.
- Current expected result for the catalog run
  `captures\cdb-surface-dump-20260511-170708` is failure: it catalogs the
  expected descriptors but still reports a 640x480 surface. This keeps the
  next patch target narrowed to the full castle overview allocation/present
  path around `00422180`, `00422020`, and likely `00422305`.
- Updated `probes/cdb/castle/clash95_castle_barracks_second_action_select1_extra.cdb` so the
  selected-index-1 second-action proof can emit
  `APBARRACKS_ACTION_CLICK_4356C0_CONTROLLED_STOP`,
  `APBARRACKS_SURFDUMP_READY`, and `SURFDUMP_HOST_READY` at the `004356C0`
  callback entry. This avoids the May 12 timeout path where the callback later
  halted on `c0000096` at `004024E6` before the host could dump the surface.
- Extended `tools\castle_barracks_action_click_summary.py` with
  `controlled_4356c0_ok` and `--require-4356c0-controlled-stop` so the CDB
  harness-control proof is explicit instead of being treated as a generic
  timeout.
- Fresh hidden-desktop CDB validation:
  `captures\cdb-surface-dump-20260512-082120`.
- Candidate:
  `C:\ClashTests\cdb-castle-center-all\clash95_hd_surfdump_20260512_082120.exe`.
- Candidate SHA-256:
  `AF53C76D4E4C6184E1038B228F23F8D77FA2E0FDB31B6CD6BFC9CB497590619E`.
- Parser result:
  `ready=True descriptor_click_ok=True action_exit_ok=False success_4356c0_ok=False controlled_4356c0_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.
- Key row:
  `APBARRACKS_ACTION_CLICK_4356C0_CONTROLLED_STOP reason=entry_before_privileged_probe selected_index=1 selected_addon=1 action_state=1 surface=... size=(800,600)`.
- Interpretation:
  the selected-index-1 descriptor/callback route is now CDB-stable under the
  controlled-stop harness. This run is not a replacement for the earlier
  post-action centered-frame proof at
  `captures\cdb-surface-dump-20260511-170759`, because it intentionally stops
  before the final post-callback redraw.

## Castle Barracks Duplicate/Echo Fix, 2026-05-12

- Fixed the `castlecenter-all` visual centering path so the stock barracks
  redraw runs first and the freshly rendered native 640x480 layer is centered
  exactly once.
- Patch change:
  `castle-ui-center-present-wrapper` now patches both `00435DAA`
  (`Render_Present` callback pointer `00435B90 -> 0051316F`) and `00435DDE`
  (per-frame loop redraw call `00435B90 -> 0051316F`). The wrapper calls the
  stock `00435B90`, copies top-left 640x480 to scratch, clears the 800x600
  target, and copies back at `(80,60)`.
- Important failed attempts:
  `captures\cdb-surface-dump-20260512-080906` and `20260512-081214` exposed
  the register/relative-call hazards in the first wrapper, and
  `captures\cdb-surface-dump-20260512-082001` proved that wrapping only the
  initial present callback is not enough because the loop redraw still draws
  native-origin content.
- Passing hidden-desktop CDB run:
  `captures\cdb-surface-dump-20260512-082418`.
- Candidate:
  `C:\ClashTests\cdb-castle-center-all\clash95_hd_surfdump_20260512_082418.exe`.
- Candidate SHA-256:
  `4E42D4A3EA61E1DB31007600A8B6515B4803E14CCC07FD2CBF1C2BA838492498`.
- Screenshot:
  `captures\cdb-surface-dump-20260512-082418\surface.png`.
- Geometry gate:
  `centered_gate=PASS image=800x600 centered_nonblack=71.228% max_margin_nonblack=0.0%`.
- Patch-stage gate:
  `129 patched, 0 original, 0 unexpected`; current HD map gate passed and
  `castle-ui-center-present-wrapper` is `3/3`.
- Action parser:
  `ready=True descriptor_click_ok=True action_exit_ok=False success_4356c0_ok=False controlled_4356c0_ok=True failure_exits=0 clickflag_writes=0 av_count=0`.
- Follow-up check:
  `captures\cdb-surface-dump-20260512-082606` used the non-controlled second
  action probe and confirmed the default selected addon still takes the
  availability-failed path. Use the controlled selected-index-1 run for the
  current no-echo screenshot and keep the older success-branch evidence as a
  separate action-state proof.

## Battle UI Probe Lane, 2026-05-15

- Added a probe-only battle validation stage:
  `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-castlecenter-all-battlecenter`.
- The stage deliberately selects the same patch groups as `castlecenter-all`;
  no battle-specific patch bytes were added.
- Added CDB templates under `probes/cdb/battle/` for catalog, present/copyback,
  and descriptor/input discovery.
- Added `tools/battle_ui_summary.py` and `tools/battle_ui_gate.py` plus
  fixture tests. The gate fails closed until battle reachability, surface,
  centered visual mode, command hit, tactical-grid hit, modal classification,
  clean patch-stage bytes, and stable HD-map regression evidence are all
  present.
- Current status:
  battle runtime proof is still pending; the new work only makes the next
  hidden/no-popup battle probe measurable and patch-safe.
