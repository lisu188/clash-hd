# Combined UI hidden validation

Generated: `2026-09-05T09:59:36.849476+00:00`

These are bounded startup and full-tile surface diagnostics, not full combined-rendering or promotion proof.

| Run | Resolution | Surface gate | Observed outcome |
| --- | --- | --- | --- |
| `native_startup_timeout` | 800x600 | FAIL | CDB surface dump timed out after 240 seconds |
| `whole_startup_bypass_av` | 800x600 | FAIL | access violation observed during surface capture |
| `800x600_fast_forward` | 800x600 | PASS | Matching geometry, explained full-tile visibility, five-second post-dump observation |
| `1024x768_fast_forward` | 1024x768 | PASS | Matching geometry, explained full-tile visibility, five-second post-dump observation |

Exact candidate, wrapper, raw-log and generated-probe identities are in [the manifest](combinedui-hidden-validation-current.json). All raw artifacts remain outside the repository.

## Remaining claims

- Full-tile geometry and visibility gates do not cover partial tile strips. Native draw counts omit those strips; safe edge clipping and world-boundary handling remain under source review.
- Hidden palette/surface composition cannot prove final visible wrapper output or manual input.
- Native startup timeout and whole-routine-bypass AV are preserved as distinct failures. Fast-forward success does not establish native startup correctness.
