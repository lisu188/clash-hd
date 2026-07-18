# HD Soak Short-Tier Report

- Overall: FAIL
- Generated: 2026-07-18T21:10:32.6935237+02:00
- Runtime policy: opt-in visible runtime soak; raw frames stay outside the repository by default
- Tier / route: short2 / map-idle
- Duration seconds: 120
- Stage: gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
- Candidate SHA-256: 5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33
- Output directory: C:\ClashCaptures\hd-soak\hd-soak-20260718-210958-short2-map-idle
- Frame samples: 0
- Unique frame hashes: 0
- Frame stability class: no_frames
- Frame progress expected: False
- Nonblack min/max: 0 / 0
- Unique sampled colors min/max: 0 / 0
- Input max move drift px: 0
- Input max sampled drift px: 0
- Input drift limit px: 1
- Window mode: required=True display=application presentation=windowed config=C:\Clash\dxcfg.ini
- Window hang observed: False
- Window missing while process alive: True
- First window-health failure: after-pulse-route-wait / window_missing_while_process_alive
- Intro skip mode/repeat/pulses: postmessage / 8 / 4
- Intro skip proof class: intro_skip_harness_prep_not_manual_directinput_release_proof
- Intro menu verified: True (nonblack 60.487, rounds 1)
- Map route reached: False (final nonblack 97.09)
- Working-set growth bytes: 0
- Private-memory growth bytes: 0
- Handle growth: 0
- Artifact bytes: 499449
- Artifact limit bytes: 262144000
- Unexpected exit: False
- Clean stop: True
- Route marker: confirm-load
- Input proof class: automated_visible_runtime_diagnostic_not_manual_directinput_release_proof
- Right-bottom promotion remains blocked: True

## Failures

- visible application window disappeared while the process remained alive
- capture errors: 1
- expected at least 2 frame samples
- expected at least 2 render-evidence frame samples
- nonblack percent dropped below 10
- unique sampled colors dropped below 8
- route/input probe failures: 2
- input drift exceeded 1px or metric missing: 3
- route did not reach the gameplay map

## Frame Samples


## Window Health Samples

- after-launch: class=responsive hwnd=0x470096 size=800x600
- after-intro-wait: class=responsive hwnd=0x470096 size=800x600
- before-pulse-route: class=responsive hwnd=0x470096 size=800x600
- after-pulse-route-wait: class=window_missing_while_process_alive hwnd= size=x
- before-frame-0000: class=window_missing_while_process_alive hwnd= size=x
