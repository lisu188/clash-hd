# HD Soak Short-Tier Report

- Overall: FAIL
- Generated: 2026-07-17T15:25:41.3412314+02:00
- Runtime policy: opt-in visible runtime soak; raw frames stay outside the repository by default
- Tier / route: short2 / map-idle
- Duration seconds: 120
- Stage: gameplay-menu640-centered-map12-dynorigin-mapsurface-scrollclamp-presentbounds-minimapright-dynvswitch
- Candidate SHA-256: 5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33
- Output directory: C:\ClashCaptures\hd-soak\hd-soak-20260717-152525-short2-map-idle
- Frame samples: 0
- Unique frame hashes: 0
- Frame stability class: no_frames
- Frame progress expected: False
- Nonblack min/max: 0 / 0
- Unique sampled colors min/max: 0 / 0
- Input max move drift px: 
- Input max sampled drift px: 
- Input drift limit px: 1
- Window mode: required=True display=application presentation=windowed config=C:\Clash\dxcfg.ini
- Window hang observed: False
- Window missing while process alive: False
- First window-health failure:  / 
- Intro skip mode/repeat/pulses: postmessage / 8 / 4
- Intro skip proof class: intro_skip_harness_prep_not_manual_directinput_release_proof
- Intro menu verified: False (nonblack , rounds 1)
- Map route reached:  (final nonblack )
- Working-set growth bytes: n/a
- Private-memory growth bytes: n/a
- Handle growth: n/a
- Artifact bytes: 56508
- Artifact limit bytes: 262144000
- Unexpected exit: True
- Clean stop: False
- Route marker: intro-skip
- Input proof class: automated_visible_runtime_diagnostic_not_manual_directinput_release_proof
- Right-bottom promotion remains blocked: True

## Failures

- process exited unexpectedly with code 1
- expected at least 2 frame samples
- nonblack percent dropped below 10
- unique sampled colors dropped below 8
- route/input probe failures: 1
- input drift exceeded 1px or metric missing: 1
- intro skip rounds never verified the main menu on screen
- no launch attempt produced an interactive menu (engine cursor never responded to pulse input)
- route did not reach the gameplay map
- working-set growth metric unavailable
- private-memory growth metric unavailable
- handle growth metric unavailable

## Frame Samples


## Window Health Samples

- after-launch: class=responsive hwnd=0x1E120E size=800x600
- after-intro-wait: class=process_exited hwnd= size=x
