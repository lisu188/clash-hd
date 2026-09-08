# Framed modal capture checkpoint — 2026-09-06

Two failed overview attempts are preserved. The subsequent 1024×768 castle overview and constructed hospital captures pass their bounded runtime/trace gates, but both have **visual composition failures**. No modal screen is accepted as complete.

All four attempts use validation-only candidate `69899e07f70dde2094264be694300e00c7a778f1391ac7797b74c59c56ee1ce0` with the optional minimap viewport fix; stable selection is unchanged.

| Attempt | Availability | Original runtime | Snapshot / visual result | Recorded CDB / game cleanup |
| --- | --- | --- | --- | --- |
| `035304` castle_overview | `existing_flags` | FAIL | No snapshot | 12608 / 10068: signaled and handles closed |
| `040604` castle_overview | `existing_flags` | FAIL | No snapshot | 30484 / 3396: signaled and handles closed |
| `040923` castle_overview | `existing_flags` | PASS | Visual FAIL | 41268 / 33000: signaled and handles closed |
| `041248` hospital | `construct_all` | PASS | Visual FAIL | 17736 / 12832: signaled and handles closed |

The first overview [failed before modal readiness](framed-modal-overview-entry-failure-20260906.json): assigning the native entry as current EIP skipped its first breakpoint. The separately reviewed post-PUSH observer fixes that capture-protocol issue. The second overview [failed before its header read](framed-modal-overview-host-read-failure-20260906.json) because PowerShell could not cast the Int32 read count to UIntPtr; a separately reviewed explicit constructor fixes the host call. These later revisions do not turn either original failure into a pass.

The [overview pixel audit](framed-modal-overview-1024x768-pixels-20260906.json) binds the complete source/probe/trace and image chain. Root and an independent reviewer viewed its existing PNG: displaced horizontal rows and a corrupt red lower region occur **inside** the centered native rectangle `(192,144)..(831,623)`. The back control is visible near its lower-left; its behavior is untested.

The [hospital pixel audit](framed-modal-hospital-1024x768-pixels-20260906.json) also authenticates the complete chain. Its `construct_all` availability mutation is explicit. The PNG shows horizontal corruption, hospital title/body near native 640 coordinates and retained centered castle content below. A hospital back arrow near `(40,430)` and an old castle arrow near `(225,580)` are observations, not input proof.

| Full-window ordinary-map comparison | Overview | Hospital |
| --- | --- | --- |
| Top source pixels | 0 / 16,384 | 177 / 16,384 |
| Bottom structural source pixels | 0 / 11,524 | 0 / 11,524 |
| Left source pixels | 0 / 23,552 | 18 / 23,552 |
| Right source pixels | 0 / 23,552 | 51 / 23,552 |
| Tooltip footer source pixels | 0 / 4,860 | 0 / 4,860 |
| Ordinary-map action cells | 0 / 6; N/A for modal controls | 0 / 6; N/A for modal controls |

**Interpretation:** native modal screens have a centered 640×480 composition and expected outer margins. The full-window ordinary-map frame/footer profile is a diagnostic comparison here; its absence is not automatically a castle defect. The actionable failures are the corrupted internal pixels and mixed hospital composition described above. Map-bar absence neither fails nor passes modal controls.

The [JSON checkpoint](framed-modal-runtime-current.json) binds 136 checked artifact-hash references and the exact retained-handle cleanup records. No independent live process query or new runtime occurred during this checkpoint.

Court, school, workshop, smith, barracks, peasants, recruitment, battle, other resolutions and applicable artwork variants remain pending. Existing older battle/right-bottom evidence retains its original scope. Visible composition, natural/manual input, gameplay acceptance, modal controls and promotion remain unproven by these captures.
