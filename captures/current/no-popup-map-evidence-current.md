# No-Popup Map Evidence

- Overall: PASS
- Captures root: `captures`

## Normal Visibility-Explained Run

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260429-140916`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Blank active cells: 13
- Unexplained blank cells: 0
- Visibility status counts: `{'visibility_zero': 13}`
- Screenshot: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260429-140916\surface.png`

![normal no-popup surface](C:/Users/andrz/git/clash-hd/captures/archive/cdb-surface-dump-20260429-140916/surface.png)

## Forced-Visible Edge Run

- Status: PASS
- Run: `captures\archive\cdb-surface-dump-20260429-135242`
- Candidate SHA-256: `5E162FA81DF59533E0B99A0DCBC9EA24280DBEC46411AE871E968D6536C08B33`
- Blank active cells: 0
- VEDGE visibility returns: 54
- VEDGE post samples: 54
- Nonzero visibility returns: 54
- Nonblack post samples: 54
- Latest visibility dump map0: `[10, 17]`
- Screenshot: `C:\Users\andrz\git\clash-hd\captures\archive\cdb-surface-dump-20260429-135242\surface.png`

![forced-visible no-popup surface](C:/Users/andrz/git/clash-hd/captures/archive/cdb-surface-dump-20260429-135242/surface.png)

## Interpretation

Normal no-popup dark cells are accepted only because the same run explains them as visibility/fog state. The forced-visible proof shows the HD right/bottom cells draw when visibility permits them.
