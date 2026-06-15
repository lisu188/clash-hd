# Probe Layout

CDB probes are grouped by runtime domain under `probes/cdb/`:

- `startup/`: startup, crash, stall, and boot-route probes.
- `menu/`: menu, load-slot, and route-transition probes.
- `mouse/`: Win32 mouse and DirectInput probes.
- `map/`: map, minimap, post-owner, and visibility probes.
- `castle/`: castle, barracks, owner/action, and overview probes.
- `battle/`: battle UI, command, and input probes.
- `ui/`: descriptor, right-bottom panel, tooltip, and selection probes.
- `render/`: DirectDraw, surface, viewport, and geometry probes.
- `key-scroll/`: keyboard scroll and boundary probes.

Probe contents are evidence artifacts. Move them mechanically when reorganizing,
but do not change breakpoints or command semantics unless the task is explicitly
about probe behavior.
