# HD Soak Short-Tier Report

- Overall: FAIL
- Generated: 2026-07-18T10:28:08.4381655+02:00
- Runtime policy: opt-in visible runtime soak; raw frames stay outside the repository by default
- Tier / route: short2 / map-idle
- Duration seconds: 120
- Stage: gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
- Candidate SHA-256: 5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33
- Output directory: C:\ClashCaptures\hd-soak\hd-soak-20260718-102547-short2-map-idle
- Frame samples: 8
- Unique frame hashes: 2
- Frame stability class: progressing
- Frame progress expected: False
- Nonblack min/max: 0.017 / 60.487
- Unique sampled colors min/max: 6 / 157
- Input max move drift px: 0
- Input max sampled drift px: 80
- Input drift limit px: 1
- Window mode: required=True display=application presentation=windowed config=C:\Clash\dxcfg.ini
- Window hang observed: False
- Window missing while process alive: False
- First window-health failure:  / 
- Intro skip mode/repeat/pulses: postmessage / 8 / 4
- Intro skip proof class: intro_skip_harness_prep_not_manual_directinput_release_proof
- Intro menu verified: True (nonblack 60.487, rounds 1)
- Map route reached:  (final nonblack )
- Working-set growth bytes: 876544
- Private-memory growth bytes: 704512
- Handle growth: 6
- Artifact bytes: 1657609
- Artifact limit bytes: 262144000
- Unexpected exit: False
- Clean stop: True
- Route marker: intro-skip
- Input proof class: automated_visible_runtime_diagnostic_not_manual_directinput_release_proof
- Right-bottom promotion remains blocked: True

## Failures

- nonblack percent dropped below 10
- unique sampled colors dropped below 8
- no launch attempt produced an interactive menu (engine cursor never responded to pulse input)
- route did not reach the gameplay map

## Frame Samples

- frame-0000: hash=601A4A90C2256EC7790551264695CF89A58AEC51FC944C8E3D1BA8B196B0A449 nonblack=60.487 luma=49.409 colors=157 mode=windowdc-contaminated-fallback
- frame-0001: hash=601A4A90C2256EC7790551264695CF89A58AEC51FC944C8E3D1BA8B196B0A449 nonblack=60.487 luma=49.409 colors=157 mode=windowdc-contaminated-fallback
- frame-0002: hash=601A4A90C2256EC7790551264695CF89A58AEC51FC944C8E3D1BA8B196B0A449 nonblack=60.487 luma=49.409 colors=157 mode=windowdc-contaminated-fallback
- frame-0003: hash=601A4A90C2256EC7790551264695CF89A58AEC51FC944C8E3D1BA8B196B0A449 nonblack=60.487 luma=49.409 colors=157 mode=windowdc-contaminated-fallback
- frame-0004: hash=601A4A90C2256EC7790551264695CF89A58AEC51FC944C8E3D1BA8B196B0A449 nonblack=60.487 luma=49.409 colors=157 mode=windowdc-contaminated-fallback
- frame-0005: hash=601A4A90C2256EC7790551264695CF89A58AEC51FC944C8E3D1BA8B196B0A449 nonblack=60.487 luma=49.409 colors=157 mode=windowdc-contaminated-fallback
- frame-0006: hash=601A4A90C2256EC7790551264695CF89A58AEC51FC944C8E3D1BA8B196B0A449 nonblack=60.487 luma=49.409 colors=157 mode=windowdc-contaminated-fallback
- frame-0007: hash=585C2E7D16B88EC9C69FFCD2E46CAA4B82C1B79824F9625AC537A15D4C131875 nonblack=0.017 luma=0.035 colors=6 mode=screen

## Window Health Samples

- after-launch: class=responsive hwnd=0x1EBC07C4 size=800x600
- after-intro-wait: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0000: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0001: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0002: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0003: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0004: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0005: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0006: class=responsive hwnd=0x1EBC07C4 size=800x600
- before-frame-0007: class=responsive hwnd=0x1EBC07C4 size=800x600
