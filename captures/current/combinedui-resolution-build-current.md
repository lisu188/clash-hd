# Combined UI resolution candidate builds

Generated: `2026-09-05T08:49:01.916075+00:00`.

All six candidates were built from the known original with SHA and old-byte verification. The original was rehashed afterward and is unchanged. Each exact-resolution byte gate passes 166 patched records, with no original or unexpected bytes. No candidate in this report was executed or promoted.

| Resolution | Candidate SHA-256 | Byte report |
| --- | --- | --- |
| 800x600 | `0A75CF35F42EFE1E44FBA1AC4031EAAE5323CDFF51AA19D261C36C5BB84691C2` | [166 patched](combinedui-validation-800x600-patch-stage-current.json) |
| 1024x768 | `4F8FE0899593B2E2F7477518EE1EA05E1D0F21B0CEEA9091507361D4A3504120` | [166 patched](combinedui-validation-1024x768-patch-stage-current.json) |
| 1280x720 | `F1475EE51D64FE5CEFAB29339992A2FBBDF382806446BF570F8105198112F3FA` | [166 patched](combinedui-validation-1280x720-patch-stage-current.json) |
| 1280x960 | `019BA3A7C932606AC35E9A703E86FA0A0672066E4CDDA6407A732EFA460584B6` | [166 patched](combinedui-validation-1280x960-patch-stage-current.json) |
| 1920x1080 | `B4AF9A609F2E90A48941C2404AA71CC794AA9E680D0CD78940662817071A2CEF` | [166 patched](combinedui-validation-1920x1080-patch-stage-current.json) |
| 802x602 | `9C45ED3F679DD802EE0D11F8B31DEA6CD8D302556A84E31835A9407DA9CBA4B5` | [166 patched](combinedui-validation-802x602-patch-stage-current.json) |

The 800x600 output remains byte-identical to the first combined candidate. Larger and custom recipes repeat the native left/top border artwork in bounded chunks, clipping partial final tiles. New code fits the existing 256-byte cave; semantic fixtures cover 287 profile shapes and three present-flag values. These checks establish byte integrity and generated rectangle behavior, not final-wrapper rendering or input correctness.

Candidate paths, full source identity, and per-run fields are in the [JSON record](combinedui-resolution-build-current.json). Binaries stay under `C:\ClashTests\combinedui-validation\resolution-build-20260905-104900-264961`; launcher statuses remain unchanged.
