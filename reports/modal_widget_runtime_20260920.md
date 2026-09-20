# Actual modal-widget candidate startup — 2026-09-20

The `owned_modal_widget_bounds_v1` candidates were actually built and executed
on isolated Windows 2022 runners with all 60 original runtime files from
`clash-assets` commit `84a1e4bcf131e6bb75b39fc5e10941dd0b801767`.
These are the widget candidates, not the earlier original-game or Complete HD
baselines. No input or forced map/modal route was injected.

## Fresh follow-up

Run `35499187074`, runtime source commit
`d6ebe6e6cd852d67eacc3b279e33d35aabe5c197`.
Both exact candidate observations completed with harness exit 0, observed entry,
matching loaded executable sections, correct primary dimensions, retained owned
cleanup, and unchanged original/reference/candidate/source identities.

| Resolution | Candidate SHA-256 | Observed game interval | Identical primary samples |
| --- | --- | --- | --- |
| 1024x768 | `ebea660f885da43896ad5e4303e6e7d7fe112def6c897b4c26312df8505376e5` | 60.250 seconds | 7 |
| 1920x1080 | `baea13ce80c89d0f9369947881c187adcf9065ddaee5295978fdfea4f72ca5a9` | 60.781 seconds | 6 |

Host elapsed times, including final collection, were 62.343 and 62.546 seconds.
The same candidate bytes were used in the earlier attempt; the follow-up changes
only debugger selection/observation, not a rendering patch.

Both paused primary images show all six menu controls within a centered native
640x480 area: `[192,144,832,624)` and `[640,300,1280,780)` respectively. All four
outer bands are black except 265 cursor pixels in `[1,1,30,28)`. Both final
primary pairs pass the advisory tear check as `clean_stable_pair` (ratio 1.246).
There is no ordinary-map action bar on this menu, and no map/control acceptance
is inferred.

At 1024x768, all six window PNGs are identical and the final window and primary
images differ by zero RGB pixels. At 1920x1080, the five window PNGs are stable
but incomplete: their visible 1024x768 region matches the primary, while pixels
outside it are black. This yields 122,614 mismatched pixels against the complete
primary. The clipped window is not full-window rendering proof, despite stable
captures and a complete memory buffer. The actual source of the clipping was
not separately measured; the observation is retained without relabeling it as
full visible-composition acceptance.

## Identity and artifact verification

The downloaded archives passed SHA-256 checks against GitHub's artifact metadata:

- 1024x768 artifact `10600799149`, archive SHA-256
  `6eeb6a88a75e142b94412326389a3986b8e72396155a3f14bf34a273d8a092d1`.
  Raw summary SHA-256 `28ad985d313778d824e9fa7071fd5152019bd9c22c372452b14b826099af6a63`;
  debugger log SHA-256 `24a621d297d19660a6e7fd145d0f971b519ca8c417d2d9c5d26557edb15314ea`.
- 1920x1080 artifact `10602125022`, archive SHA-256
  `af563f16673d43cc6db9c74314d06b0004e4752b8e808f2e09995c2b7eb743cb`.
  Raw summary SHA-256 `13467aaee1887e4032432c0a6cbc4a69f3de811bdd04a5e711d8d46c59e43d3c`;
  debugger log SHA-256 `b833398a7ca1d85b537129487f2a65f339388e4e38aced2f9b9135f53682c87c`.

The runtime source SHA-256 is
`3b1ec5a8642cf7e371ddccd299d7e35d10c77a1041019a42bb5809e2d8144f62`.
Both archived source copies match it. All 36 recorded recipe-source identities
match the reviewed source tree. Every retained primary PNG and raw buffer hash
was checked, not just the summary verdicts. Final primary PNG hashes are:
1024x768 `697e72f5c7fe904114fd5e669807067d2ff5700f2115c13497d17bd03fb1325c`;
1920x1080 `17d1d56ae895d7f859a680e34c10349aecd2a159f4dee8ea12065a5cdd5b734d`.
The original EXE remains
`500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae`.
All 517,940,933 original asset bytes were reverified by the runtime host.

## Retained failures

Initial run `35498498709` failed its Windows source fixture before game launch:
the mocked temporary directory used a short path that differed from the runtime's
resolved path. The narrow test repair canonicalized the fixture root; production
path guards were unchanged. The failed run remains retained.

Run `35498617219`, source `32dc9aeaf7d8fc3f9ff9df40b01874cf501d2938`,
actually executed both candidates. The 1024x768 run captured five identical menu
buffers but its final `r` command failed with `80040205` after losing debugger
context. It remains exit 2 and `observation_complete=false`; no crash diagnosis
is inferred. Its artifact `10601254232` has archive SHA-256
`bf1384192b1f9e0d305817e09d8390e9e6db5ef5745965c61c88ed3fca4ed435`.

The earlier 1920x1080 run completed with seven matching primary captures, but the
same clipped GDI-window limitation. Its artifact `10601183106` has archive SHA-256
`03acb0cee3dbab6a2c479066dd812cb6dfbd345b954df324d7aec0a90f50ce3a`.
Both archives and their original summaries remain unchanged. Their older source
SHA-256 is `aec067b9b02e9343a8db9b09fbfc3e9765f5d37b9df38de6ea5549fe8e7b93a9`.

The fresh debugger correction resolves and selects only the retained live primary
thread while stopped, then reads back the selected system identities and IP.
Seven / six actual `REAL_CONTEXT` records are present in the new runs. This
bounded success does not establish that every possible debugger-context loss
has been eliminated. Native exceptions and historical failures remain visible.

## Scope

These observations prove actual widget-candidate EXE startup and requested-size
menu primary buffers, not full visible composition, input responsiveness,
expanded gameplay, native modal ownership execution, corrected barracks pixels,
text placement, save/load, transitions or endurance. The generated full-stage
CDB probe was authenticated as a file, not executed by this startup harness.
All release, gameplay and manual-input verdicts remain false. The protected
stable stage and launcher defaults are unchanged. Future runtime is explicit
manual dispatch; normal PR checks launch no game.
