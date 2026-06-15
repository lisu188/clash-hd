# Castle Owner Setup Probe

- Log: `captures\cdb-surface-dump-20260506-141239\cdb-surface-dump.log`
- Lines: 229
- Surface ready line: 222
- PlayGame line: 209
- Setup rows: 4
- Owner global rows: 4
- Action rows: 0
- AV rows: 0

## Classification

- surface dump reached ready state
- controlled castle-screen invocation was attempted
- full castle screen body was observed
- castle screen render/dispatcher entry was observed
- command-99 owner setup route was observed
- owner globals dword_532150/dword_53214C/dword_532154 were touched
- right-bottom castle action owner path was not observed

## Marker Counts

- CASTLE_INVOKE_PLAYGAME: 1
- CASTLE_SCREEN_OWNER_SET_422207: 1
- CASTLE_RENDERHOOK_DRAW_422020: 1
- CASTLE_FORCE_HITTEST_254: 1
- CASTLE_CMD99_SETUP_422709: 2
- CASTLE_DESCRIPTOR_INSTALL_42257E: 1
- CASTLE_FORCE_COMMAND99_CLICK: 1
- CASTLE_CALLBACK_CALL_42262C: 1
- CASTLE_OWNER_SETUP_433C20: 1
- CASTLE_WRITE_532150: 1
- CASTLE_WRITE_53214C: 1
- CASTLE_WRITE_532154: 1
- CASTLE_SURFDUMP_READY: 1
- SURFDUMP_PLAYGAME: 1
- SURFDUMP_READY: 1
- SURFDUMP_HOST_READY: 1

## Screenshot Artifact

![surface dump](C:\Users\andrz\OneDrive\Pulpit\git\clash-hd\captures\cdb-surface-dump-20260506-141239\surface.png)
