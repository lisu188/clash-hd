# Complete-HD integration handoff — 2026-09-08

The active candidate is the protected stable stage plus
`-completehd-validation`, recipe `complete_hd_v1`. The protected stable stage
and Classic launcher default at 800x600 remain unchanged. Complete HD is
experimental at every resolution. Native 640x480 menus, castles and battles
remain centered; the widened-battle experiment is excluded.

## Implemented and checked

The reviewed combined/framed/minimap/native-modal/army dependency chain is in
main, with exact source provenance in `reports/hd-foundation-import-manifest.json`.
The shared builder emits deterministic external candidate/manifest/probe
bundles. All six fixture resolutions, including 802x602, passed in-memory
construction; repeated 800x600/1024x768/1920x1080 results matched. The nine
modal/army suites passed 78 tests. See `COMPLETE_HD_CANDIDATE.md` and
`HD_FOUNDATION_IMPORT.md` for scope and historical compatibility.

The launcher consumes that builder through an experimental Complete HD profile.
Its original Classic/800x600 default and explicit Play/double-flag confirmation
remain. The visible diagnostic harness uses measured geometry and pulse input;
its separate human observation path never labels injected input as manual proof.

Whole-release evaluation reconstructs candidate bytes and requires trusted
lane verifiers. A report's own passing flags cannot establish eligibility.
Missing verifier implementations and actual evidence remain incomplete.

## First integrated runtime result

`captures/current/completehd-initial-800x600-20260908.json` binds the first hidden
run and its unchanged raw artifacts. Candidate
`e785d202140942959b973f462a9eded27531fd12c5668fac40af61248e875a84`
reached the map and yielded a 480,000-byte paused surface with observed minimap
state. It **failed** initial trace validation: line 520 repeats full convergence
before matching presentation. Event-output integrity passed, but that does not
prove native call completion. Do not remove repeated records or turn this run
into a rendering pass.

The run had no access violation or timeout; exact task-owned process cleanup
passed. Original executable, live saves and isolated saves were unchanged.
The diagnostic PNG is a single hidden software capture, not a stable pair or
final visible-color proof. All four borders and six action cells were visually
inspected, but blank terrain and full rendering acceptance remain unproven.

Prepared bundles for 800x600, 1024x768 and 1920x1080 are under
`C:/ClashTests/completehd-validation-20260908/prepared-<resolution>/`.
The 1080p candidate is
`95ba0c965d019d0b1c5fb45726e938bf0b1b22ce6fc8353375409477e94a90d0`.
The initial run plan records producer hashes; later producer edits require a
new immutable run plan. Its unexecuted 1024/1080 entries are not evidence.

## Remaining work

Diagnose repeated native observations with additional progress/call-identity
probes. Preserve all original failures. Validate scrolling, minimap erasure,
partial/full painting, clamps and out-of-world clearing separately.

Barracks evidence demonstrates twelve late 32x64 rectangles missing from the
physical mirror after native slot draws. A narrow additive copy hook is being
prepared; native primary destination misplacement remains a static inference
until primary-surface evidence is captured. Court, recruitment, peasants,
ownership/exit restoration and destruction still require complete routes.

Ordinary army selection/movement, all portraits, map redraw/scroll/reselection,
centered battle entry/command/outcome/return and healthy map transitions remain
incomplete on the final candidate. Earlier controlled 1024x768 and historical
battle callback evidence does not establish these claims.

Fresh approved visible/manual evidence, the five human input targets, complete
continuity, the final candidate's short ladder and both separate two-hour soaks
remain outstanding. There is no release eligibility report or promotion
decision. Preserve the dirty `C:/Users/andrz/git/clash-hd` checkout; it was read
only throughout these imports.
