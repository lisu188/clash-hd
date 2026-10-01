# Engine viewport patch notes

Public patch documentation is intentionally limited to information necessary to
understand and maintain the independently authored patcher.

The detailed historical reverse-engineering notebook previously stored here has
been removed from the public repository. The executable itself, decompiler or
disassembler exports, debugger dumps, and raw runtime evidence are not public
project artifacts.

For maintained behavior, use the implementation under `src/patcher/`, the
launcher resolution registry, and source-only tests. Patch definitions must
continue to verify the expected executable identity and old bytes before
writing replacement bytes.
