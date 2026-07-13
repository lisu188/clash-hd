# Working With This Repo (Read This First)

Concise operating guide for any agent — especially smaller/lower-tier models —
touching the Clash95 HD mod. `AGENTS.md` is the full spec; this is the short,
prescriptive version. When the two conflict, `AGENTS.md` wins.

## What this project is

A reverse-engineering + binary-patching project that makes the 32-bit Windows
game `clash95.exe` render at HD (800x600, 12x9-tile map) instead of native
640x480. The repo ships **only** source, docs, and small evidence manifests —
never the game binary, patched `.exe`, wrapper DLLs, saves, or large dumps.

## The five rules you must not break

1. **Never modify `C:\Clash\clash95.exe`** (the user's original) and never
   commit any `.exe`/`.dll`/`.dat`/`.raw`/dump. `.gitignore` blocks them; do not
   force-add. Build candidates under `C:\ClashTests\...` or run a
   distinctly-named copy from `C:\Clash`.
2. **Honesty over green gates.** The evidence gates exist to tell the truth
   about the mod. Never make a check pass by weakening it to ignore a real
   failure, by pointing it at unrelated evidence, or by fabricating data. If a
   gate is red for a real reason, leave it red and say why. A dishonest pass is
   worse than an honest fail.
3. **Never fabricate approval/consent.** Manifest fields like `approved: true`,
   `approval_record`, and any visible/manual-runtime run require a real, fresh
   user approval in chat. Do not write them yourself.
4. **The stable stage is sacred.** The default stable stage is
   `gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch`.
   New patch work goes in a **validation stage** (a `-suffix` stage), never
   silently into stable. Promotion needs hidden-CDB **and** approved
   visible-runtime evidence.
5. **Every byte patch verifies old bytes before writing new bytes.** Record
   SHA, file offset, VA/RVA, old bytes, new bytes, stage, rationale.

## Do this to check the current state (repo-only, no game launch)

```
python tools/current_evidence_refresh.py        # regenerates all evidence gates
python -c "import json;d=json.load(open('captures/current/current-evidence-refresh-current.json',encoding='utf-8'));print(sum(1 for v in d['checks'].values() if not v.get('passed')),'/',len(d['checks']),'failing')"
```
Per-tool fixtures: `python tools/test_<name>.py`. Wiki: `python tools/wiki_lint.py`.

## Environment gotchas (this machine)

- Shell is **hardened**: `NoDefaultCurrentDirectoryInExePath=1`. cmd.exe won't
  resolve bare batch/exe names from the current dir — invoke by full path.
- Sandbox blocks child-process chains — run PowerShell game/CDB harnesses with
  the sandbox disabled.
- The game window creation leaves `Process.MainWindowHandle` **null** under the
  GOG/dgVoodoo ddraw wrapper. Detect the window with **EnumWindows** (visible +
  titled window for the pid), not `.MainWindowHandle`.
- PowerShell: `$pid` is **reserved** — never name a variable `$pid` (use
  `$procId`). This bug silently no-ops every downstream call.
- Two ddraw wrappers, opposite trade-offs: the **surfdump proxy**
  (`src/ddraw_surfdump_proxy/`) is memory-only (no visible window) and lets CDB
  run — use it for hidden dumps. The **GOG/dgVoodoo wrapper** (`C:\Clash\ddraw.dll`)
  makes a real visible window but **breaks CDB** (empty log) — use it for
  visible runs *without* CDB.

## Two capture paths, and their traps

- **Hidden CDB surfdump** (`scripts/cdb/run_cdb_surface_dump.ps1`, no popup):
  dumps `dword_5202E0` as an **8-bit paletted** surface. It **cannot** capture
  the minimap interior, bottom tooltip, or right/bottom HUD, and recolors the
  palette (green->orange). Its "black patches" are **capture artifacts, not
  render defects** — confirmed by real-runtime measurement
  (`reports/real_runtime_screen_audit_20260712.md`). Do not treat proxy black
  as an HD bug without a real-runtime check.
- **Visible runtime** (approved only): real colors + minimap + tooltips, but the
  live GDI grab **tears on animated screens** (e.g. the castle courtyard). Static
  screens capture clean.

## The current frontier (2026-07-13)

Refresh ~143/154. Remaining reds are honest, not oversights:
- **UI layout defects** (user-confirmed): terrain tooltip should be
  bottom-centered; selected-unit action panel should dock right-bottom. Real
  anchor-relocation patch work (validation stage first).
- **Right-bottom compose gates**: a gate-design contradiction — one gate wants
  natural owner/action rows drawn, another wants them absent; only the
  addon_flags fixture draws them. Needs a gate-owner design decision, not a
  force.
- **Battle click-to-callback**: blocked by the CDB-vs-visible-window ddraw
  tension (R&D).
- **Continuity / long soaks**: need fresh approval / multi-hour runtime.

## If you are a smaller model, prefer these safe actions

- Read-only evidence checks, `tools/test_*.py`, `wiki_lint.py`.
- Documentation and evidence-report writing.
- Repoint a tool's default run path after regenerating evidence.
Avoid, unless explicitly asked and you understand the risk: byte-patch changes,
touching the stable stage, editing gate pass/fail logic, or any visible/manual
runtime. When unsure, stop and ask.
