# Clash95.exe HD Mod Analysis

Analyzed file: `clash95.exe`

- Size: 1,232,384 bytes
- SHA-256: `500055D77D03D514E8D3168506BD10F67CD8569BCC450604FF8192F46CDAF3AE`
- PE type: 32-bit Windows GUI executable
- Build timestamp in PE header: 1998-04-08 13:46:45 UTC
- Likely compiler/toolchain: Watcom-era C/C++ based on section names (`AUTO`, `DGROUP`) and exported symbol mangling.

## Main Finding

The safest HD mod path is not a direct "make the engine 1920x1080" patch. The executable is a DirectDraw-era 8-bit/paletted game with many hard-coded 640x480 assumptions. A presentation-layer HD mod should come first: keep the game rendering at its native logical 640x480, intercept DirectDraw output, scale it to a modern window/fullscreen resolution, and remap mouse coordinates.

True widescreen or larger visible map area is possible, but it is a much larger reverse-engineering project because UI layout, clip rectangles, sprite buffers, map rendering, mouse coordinates, and asset dimensions all appear tied to 640x480.

## Rendering/API Evidence

Imported graphics/media APIs:

- `DDRAW.dll!DirectDrawCreate`
- `DINPUT.dll!DirectInputCreateA`
- `DSOUND.dll!DirectSoundCreate`
- `GDI32.dll!StretchBlt`
- `GDI32.dll!StretchDIBits`
- `AVIFIL32.dll` and `MSVFW32.dll` AVI/decompression functions

Relevant internal strings:

- `DLXMemScreen`
- `DLXSurfScreen`
- `DLXRealScreen`
- `DLXVScreen`
- `DLXSpriteSet`
- `DirectDraw Error %s`
- `Cant flip`
- `page lock error`
- `palette create`
- `set palette`
- `map.pal`
- `mouse.s32`
- `pal_grey.pcx`

This points to an engine using DirectDraw surfaces, palette management, software/memory surfaces, sprite sets, PCX images, and custom `.s32` sprite assets.

## Resolution Evidence

The game creates a 640x480 window directly:

- `CreateWindowExA` call at file offset `0x60ec8`, RVA `0x61ac8`
- Nearby pushes include:
  - `push 480`
  - `push 640`
  - window/class strings both resolve to `Clash`

The DirectDraw display-mode call is also identifiable:

- Likely `IDirectDraw2::SetDisplayMode` vtable call at file offset `0x7454b`, RVA `0x7514b`
- The call sequence pushes five arguments:
  - flags: `1`
  - refresh: `0`
  - bits-per-pixel from object field `+0x20`
  - height from object field `+0x1c`
  - width from object field `+0x18`

There are many nearby 640/480 constant pairs in code. This means changing only the window size or only the display mode is not enough. Several systems likely calculate positions or clipping against native resolution.

## Asset/Data Evidence

The executable itself contains only icon resources. Game assets are external.

Referenced data/archive paths include:

- `data\minimum.res`
- `data\normal.res`
- `data\maximum.res`
- `data\maps.res`
- `data\gfx3.res`
- `data\infopol.res`
- `data\infoang.res`
- `data\infoger.res`
- `data\misinfop.res`
- `data\misinfoa.res`
- `data\miswava.res`
- `data\misinfog.res`
- `data\music.res`
- `maps\`
- `sfx\music\`

Referenced asset formats include:

- `.pcx`
- `.pal`
- `.s32`
- `.map`
- `.wav`
- `.dat`
- `.fac`

The next asset-related step requires the original `data` and `maps` directories or CD contents. Without those, the executable can be analyzed but the actual HD asset pipeline cannot be validated.

## Recommended Build Strategy

### Phase 1: DirectDraw HD Wrapper

Build a 32-bit `ddraw.dll` proxy placed next to `clash95.exe`.

The proxy should:

- Export `DirectDrawCreate`.
- Load the real system `ddraw.dll`.
- Wrap `IDirectDraw`, `IDirectDraw2`, `IDirectDrawSurface`, and `IDirectDrawSurface2` enough to intercept:
  - `SetCooperativeLevel`
  - `SetDisplayMode`
  - `CreateSurface`
  - `SetPalette`
  - `Flip`
  - `Blt`
  - `Lock`
  - `Unlock`
  - `GetDC`
  - `ReleaseDC`
- Preserve the game's logical 640x480 8-bit render target.
- Convert the paletted frame to 32-bit RGBA.
- Present it scaled to the actual window/fullscreen size with integer scaling first.
- Remap mouse coordinates from scaled output back to 640x480 logical coordinates.

This gives a real HD presentation mod without destabilizing game logic.

### Phase 2: Asset Extraction/Repacking

Once original data files are present:

- Reverse the `.res` archive format.
- Extract `.pcx`, `.pal`, `.s32`, `.map`, and `.wav` contents.
- Confirm whether `.s32` stores dimensions, palette indices, compression, and frame tables.
- Replace assets at original dimensions first to verify the pipeline.
- Only attempt larger assets after the wrapper is stable.

### Phase 3: True Larger-Canvas Patch

This is the hard version. Required work likely includes:

- Patch `CreateWindowExA` 640x480 dimensions.
- Patch DirectDraw mode fields feeding `SetDisplayMode`.
- Find global screen-width/screen-height storage.
- Patch surface allocations and pitch assumptions.
- Patch all clipping, dirty-rect, and mouse-coordinate conversions.
- Patch UI layout and map viewport math.
- Replace or upscale UI/background assets.

This should be treated as a separate reverse-engineering project after Phase 1 works.

## Practical Recommendation

Start with a wrapper-based HD mod:

1. Native game logic stays at 640x480.
2. Output scales to 1280x960, 1600x1200, 1920x1440, or letterboxed 1920x1080.
3. Add optional filters later: nearest, linear, xBR-like, CRT, scanlines.
4. Avoid distributing a modified executable; distribute a loader/proxy DLL or binary patcher instead.

The evidence suggests this will produce the fastest stable result. Direct binary patching for true HD is possible, but the number of hard-coded 640x480 paths makes it high-risk as a first step.
