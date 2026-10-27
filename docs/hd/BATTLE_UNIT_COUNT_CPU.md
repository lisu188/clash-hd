# Native Unit to Count CPU slice

`tools/test_battle_profile_native_unit_count_original.py` supplies a separate,
explicitly opted-in CPU comparison of one bounded native route. The default
command runs five stdlib authoring checks. It opens no game file and constructs
neither a parent candidate nor a CPU machine. Public CI uses this default.

The private command requires the exact user-owned original:

```powershell
python -B tools/test_battle_profile_native_unit_count_original.py --original-backed C:/Clash/clash95.exe
```

The fixture reconstructs the Classic and Modal Widgets 800x600 parent recipes
in RAM. It independently authenticates the selected executing caller, Unit
prefix including its JE, argument preparation, Count CALL, complete Count body,
stop instruction, neighbor table and selected HIGHLOW operands. It compares the
unchanged instructions with four RAM-only Atomic V2 overrides: the first Unit
Type read, Count entry and both Count body reads. Helper allocations, outer
Field/Tile/Adjacent ancestry and Thread callbacks remain synthetic or modeled.

The authentic final caller and Unit prologue establish the local and saved
register history. A valid unit index with type `-1` takes the actual JE at
`0x42F854`, reaches native argument preparation and calls Count. Count executes
its original prologue, neighbor loop and RET. Execution stops immediately before
`0x42F95B`; that instruction, later Unit bodies, Unit RET and final caller
continuation are outside this proof. Identity `-1` is excluded and remains
distinct from a valid index whose record has type `-1`.

Healthy comparisons cover two load bases, both modeled draw modes, identities
0/7/21, motion values -63/-64/-65 and separately allocated Modal Widgets. The
motion values create genuine saved ECX values 1/0/-1. Empty, occupied, edge and
sparse neighbor layouts exercise both Count body adapters. Assertions compare
all GPRs, EFLAGS, ESP, the exact return PC, native saved slots and local writes,
semantic payload reads, unchanged Unit locals and stack canaries. Count's final
flags are checked against its actual `ADD ESP,4`, rather than entry flags.

Guarded motion, active identity, native ancestry and Count-local mutations must
reach an actual UD2 before another cached descriptor or payload read. Parent,
instruction and return-word tampering remains a separate rejection check.

## Retained saved-ECX counterexample

The initial new fixture incorrectly demanded a UD2 for callback-time corruption
of CountS-8, Count's saved ECX slot. The pinned Atomic producer already states
`native_ecx_pop_slot_authority_verified=False`. The observed mutation reached a
protected physical-descriptor read instead of UD2. That failed run, exact prior
fixture and diagnostic remain outside the repository; the source report retains
their identities and failed verdict.

The terminal test now targets the producer's guarded saved-EBP ancestry slot.
Healthy saved-ECX push/pop comparisons remain. This scope correction supplies
no saved-ECX corruption protection or historical callee-preservation proof.

## Evidence limits

The local result is recorded in
`reports/battle-unit-count-native-cpu-20261027.json`. A passing bounded CPU
comparison does not establish a legal live-game record, production allocation,
all eight prospective overrides, a full native callback ABI, sprite/provider
lifetime, Windows/game runtime, input, endurance, installation or stable
promotion. All production hooks remain uninstalled and the protected stable
stage is unchanged. The frozen prefix and Count fixtures remain unchanged.

Raw IDA databases, REA assembly exports, original bytes and local diagnostics
stay outside public source control. Public CI obtains no retail runtime.
