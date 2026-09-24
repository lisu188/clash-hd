# Actual Clash executable startup — 2026-09-20

## Observed result

The original game and the existing Complete HD 1024x768 candidate were actually
executed on an isolated Windows 2022 runner with the complete runtime from
`lisu188/clash-assets`, commit `84a1e4bcf131e6bb75b39fc5e10941dd0b801767`.
These are not synthetic PE targets or simulated menu images.

| Executable and wrapper | Actual observation | Harness outcome |
| --- | --- | --- |
| Original EXE, shipped GOG wrapper | Intro and then the main menu in a 1024x768 wrapper window; cached native surface is 640x480 | Incomplete: final debugger register command fails |
| Original EXE, source-built diagnostic DirectDraw | Main menu at 640x480; 60.532 seconds host duration | Complete bounded observation; exit 0 |
| Complete HD candidate, diagnostic DirectDraw | Main menu centered at (192,144) in a real 1024x768 primary surface; 60.484 seconds host duration | Complete bounded observation; exit 0 |

Both proxy runs retained seven byte-identical paused primary buffers and six
identical window captures. The last window PNG and last palette-rendered primary
PNG have zero differing RGB pixels within each run. All six menu controls and
all four image edges were inspected. The HD outer area is black except for the
cursor at the physical top-left. These are menu observations; the ordinary map
frame and six action-bar cells are not on this screen.

The center comparison against the original has 261 differing indexed pixels,
confined to [1,1,30,28), where the original cursor appears. This diagnostic
comparison is not independent source-artwork or input acceptance.

## Exact identities

Original EXE: 1,232,384 bytes, SHA-256
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.

Complete HD candidate: SHA-256
`9bc99ba5a33248066b90b95119dd4301692d5af429d93167c4b35d2e508c53b5`,
recipe `complete_hd_v1`, stage
`gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch-completehd-validation`.
This is the existing combined recipe, not an installation or promotion of the
newer modal/widget experiments.

All 60 reference files (517,940,933 bytes) matched their manifest before and
after the attempts. The executable sections loaded at image base `00400000`
matched the authenticated disk image before execution. The original entry
`004731B6` was observed. Every copied original and candidate EXE remained
unchanged; all three retained owned process handles confirmed process absence
after task cleanup. Cleanup exit `80004005` is debugger termination, not a
reported natural game crash.

## Retained attempts

### Initial attempt

Run `35493716788`, source commit
`dbdf5463f673ae306abbcbc0acbd1ac9f2d710c4`, artifact `10600042003`,
ZIP SHA-256 `5b584a74ab40f15f83564d5db087045155453d11e844b4b9d47e606126be71f5`.

Both real original processes reached the entry and drew windows. GOG showed
the intro; the proxy showed the menu. Both harnesses then returned 2 because
`SetInterrupt` was followed by a timed-out pause event (`S_FALSE`). The initial
Python exit calculation considered entry and cleanup but omitted the harness
return code, so a green workflow was not a completed diagnostic run. Its raw
summary and logs are preserved unchanged. The follow-up fixes this reporting
error and includes a regression reproducing the retained failure.

### Follow-up with actual HD execution

Run `35494221434`, source commit
`c5130f25aa3dc03d9d6328c0ad876623460b34f5`, artifact `10599813055`,
ZIP SHA-256 `76e881323900800cdb87342c8bfc2caf7e5d9889a85d2d301138e9601669000b`.

`DebugBreakProcess` on the retained task-owned handle produced actual paused
reads. The two proxy observations completed. The GOG attempt retained intro
and menu screenshots but later lost the debugger's current process/thread
context; `r` returned `80040205`. Its harness return is 2 and
`observation_complete=false`. The combined workflow therefore fails honestly.
The cause of the lost context is unresolved; this is not proof of a game crash.
Audio-device and debugger-extension warnings are retained as well.

Source LF SHA-256:
`0b5ad7d87cc1277214c9fbc60c840a26056dbd9b0f68059a9eb26782d90d31c6`.
The actual Windows CRLF checkout SHA-256 recorded by this run is
`0a674a5134264a9e641b520330d3e1dbead9606d1db527117db37cb124137710`.
The LF-to-CRLF transformation reproduces that exact hash, and the archived C++
source matches the embedded harness after the same newline normalization.

Representative actual images inside the artifact:

- `real-exe/gog/window-04-00.png`: GOG main menu.
- `real-exe/proxy/primary-06.png`: native 640x480 menu, SHA-256
  `7beab7aba6bc5a4a283a924adc9052b002117c8bc9b3a235bb6c004c1cdd338f`.
- `real-exe/completehd-proxy/primary-06.png`: HD menu, SHA-256
  `697e72f5c7fe904114fd5e669807067d2ff5700f2115c13497d17bd03fb1325c`.

## Reproduction and limits

`tools/real_exe_smoke.py` is dry-run-only without `--execute`. The final workflow
runs only source fixtures on pull requests; real execution requires a manual
workflow dispatch with `execute=true`. The disposable run uses copies outside
the checkout, a retained process handle and kill-on-close job, and never uploads
the game EXE, wrapper DLL or complete assets. Eight focused fixtures cover the
opt-in, input checks, diagnostic rendering and failure reporting.

A malformed one-line YAML dependency command in intermediate commit `9bc81bd`
was rejected before a runner started (run `35494347791`). Its colon parsing was
reproduced and repaired with a block scalar; this was separate from both actual
runtime attempts.

No clicks or keyboard input were injected. Campaign entry, map rendering,
movement, combat, save/load, audio output, ordinary/manual input and endurance
remain untested by this startup experiment. No stable/default patch bytes or
launcher settings changed. The GOG debugger-context failure and later gameplay
validation remain open; successful idle menu captures do not establish release
eligibility.
