"""Opt-in DbgEng grammar checks on the existing marked synthetic PE fixture.

Exact disabled breakpoint definitions are parsed by the system x86 debugger.
Stored command bodies are then evaluated with only `gc` replaced by a labeled
echo. Synthetic input writes are fixture setup, never part of the observer.
The target stays paused at its initial loader breakpoint; no fixture instructions run.
This is not evidence of native text execution or game/candidate correctness.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

import test_framed_loaded_probe_engine as engine
import test_modal_primary_text_observer as fixtures
import modal_primary_text_observer as observer


BODY_CHECK = r'''
        // The parsed breakpoint definitions are exact. Only continuation is
        // suppressed when evaluating their stored bodies in this synthetic PE.
        for (int sample = 0; sample < 5; ++sample) {
            ULONG id = sample < 3 ? 150 + sample : sample == 3 ? 150 : 151;
            const char *stack = sample == 0 ? "ed @esp 00432c6b 221 265 35 3 004efc3a ffffffff" :
                                sample == 1 ? "ed @esp 00432c6b 271 2b5 71 3 004efc3a ffffffff" :
                                sample == 2 ? "ed @esp 271 2b5 71 3 004efc3a ffffffff" :
                                              "ed @esp 00432c6c 221 265 35 3 004efc3a ffffffff";
            check(session.control->Execute(DEBUG_OUTCTL_THIS_CLIENT, stack, DEBUG_EXECUTE_NO_REPEAT), "Synthetic stack input");
            if (sample >= 3)
                check(session.control->Execute(DEBUG_OUTCTL_THIS_CLIENT, "ed 00405008 0", DEBUG_EXECUTE_NO_REPEAT), "Synthetic null owner input");
            IDebugBreakpoint *breakpoint = nullptr;
            check(session.control->GetBreakpointById(id, &breakpoint), "GetBreakpointById");
            char buffer[4096]; ULONG length = 0;
            HRESULT captured = breakpoint->GetCommand(buffer, sizeof(buffer), &length);
            breakpoint->Release();
            check(captured, "GetCommand");
            if (!length || length > sizeof(buffer)) throw std::runtime_error("Stored body length is invalid");
            std::string body(buffer);
            size_t position = 0; int substitutions = 0;
            const std::string replacement = ".echo MPTEXT_FIXTURE_CONTINUATION_SUPPRESSED";
            while ((position = body.find("gc", position)) != std::string::npos) {
                bool before = position == 0 || body[position-1] == ' ' || body[position-1] == ';';
                bool after = position+2 == body.size() || body[position+2] == ' ' || body[position+2] == ';' || body[position+2] == '}';
                if (!before || !after) throw std::runtime_error("Unexpected gc substring in stored body");
                body.replace(position, 2, replacement); position += replacement.size(); ++substitutions;
            }
            if (substitutions != (id == 151 ? 2 : 1)) throw std::runtime_error("Unexpected continuation inventory");
            printf("HARNESS_OBSERVER_BODY sample=%d id=%lu substitutions=%d\n", sample, id, substitutions); fflush(stdout);
            check(session.control->Execute(DEBUG_OUTCTL_THIS_CLIENT, body.c_str(), DEBUG_EXECUTE_NO_REPEAT), "Stored observer body");
        }
'''

# Reuse the existing source-bound marked-PE, x86-only, no-window lifecycle and
# cleanup harness. No AttachProcess, SetExecutionStatus, or candidate path exists.
HARNESS = engine.HARNESS.replace('        session.client->FlushCallbacks();', BODY_CHECK + '\n        session.client->FlushCallbacks();')


def grammar_packet():
    binding = fixtures.sites()
    binding['state_va'] = 0x405000  # Mapped BSS in the marked synthetic PE only.
    return observer._compose(fixtures.context('800x600'), binding,
                             breakpoint_ids=observer.DEFAULT_IDS, occupied_breakpoints={})


def fixture_script(prepared):
    state, native, physical, backend = 0x405000, 0x406000, 0x407000, 0x408000
    values = {
        state: 1, state + 4: physical, state + 8: native, state + 36: 0,
        state + 60: 0x1800000, state + 64: 0x1000000,
        observer.canvas.MAP: native, observer.canvas.RENDER: observer.canvas.PRIMARY,
        native: 640 | (480 << 16), native + 4: 0x1800000, native + 0xAC: 0,
        native + 0xB8: observer.canvas.MEMORY_VTABLE,
        physical: 800 | (600 << 16), physical + 4: 0x1000000, physical + 0xAC: 0,
        physical + 0xB8: observer.canvas.MEMORY_VTABLE,
        observer.canvas.PRIMARY: 800 | (600 << 16), observer.canvas.PRIMARY + 0xB8: observer.canvas.PRIMARY_VTABLE,
        observer.canvas.PRIMARY + 0xBC: backend, observer.canvas.PRIMARY + 0xD4: 8,
        backend + 0xA4: 0x409000,
    }
    lines = ['$$ SYNTHETIC FIXTURE INPUTS ONLY. These writes are not observer commands.']
    lines += [f'ed {address:08x} {value:08x}' for address, value in values.items()]
    lines += [f'ed {state + 16:08x} @esp+100', f'ed {state + 20:08x} @$tid']
    return '\r\n'.join(lines) + '\r\n' + prepared['fragment']


@unittest.skipUnless(os.name == 'nt' and os.environ.get('CLASH_TEXT_OBSERVER_DEBUGGER_INTEGRATION') == '1',
                     'separate opt-in isolated system x86 debugger-engine lane required')
class TextObserverDebuggerTests(unittest.TestCase):
    def test_exact_definitions_and_stored_bodies_under_native_dbgeng(self):
        compiler = shutil.which('cl.exe')
        self.assertIsNotNone(compiler, 'MSVC x86 environment is required')
        with tempfile.TemporaryDirectory(prefix='clash-text-observer-engine-') as temporary:
            directory = Path(temporary)
            source = directory / 'engine.cpp'; source.write_text(HARNESS, encoding='utf-8')
            runner = directory / 'engine.exe'
            compiled = subprocess.run([compiler, '/nologo', '/EHsc', '/W4', '/O2', '/MT', str(source),
                                       '/Fe:' + str(runner), '/Fo:' + str(directory / 'engine.obj'), '/link', '/MACHINE:X86'],
                                      cwd=directory, capture_output=True, text=True, timeout=60,
                                      creationflags=subprocess.CREATE_NO_WINDOW)
            self.assertEqual(compiled.returncode, 0, compiled.stdout + compiled.stderr)
            image, _, _ = engine.executable_fixture('800x600')
            self.assertEqual(image[64:64 + len(engine.MAGIC)], engine.MAGIC)
            (directory / 'probe-fixture.exe').write_bytes(image)
            prepared = grammar_packet(); script = fixture_script(prepared)
            command = directory / 'observer.cdb'; command.write_bytes(script.encode('ascii'))
            result = subprocess.run([str(runner), str(command), 'file'], cwd=directory,
                                    capture_output=True, text=True, errors='replace', timeout=35,
                                    env={**os.environ, '_NT_SYMBOL_PATH': '.', '_NT_ALT_SYMBOL_PATH': ''},
                                    creationflags=subprocess.CREATE_NO_WINDOW)
            log = result.stdout + result.stderr
            report = dict(schema=1, proof_class='synthetic_dbgeng_observer_grammar_only',
                          engine='system x86 DbgEng', exact_disabled_breakpoint_definitions=True,
                          continuation_suppression='Only standalone gc tokens in stored command bodies become a labeled echo.',
                          target_fixture_sha256=observer.sha(image), observer_fragment_sha256=prepared['fragment_sha256'],
                          fixture_command_sha256=observer.sha(script.encode('ascii')), runner_sha256=observer.sha(runner.read_bytes()),
                          source_hashes={str(Path(module.__file__).relative_to(observer.context_reader.ROOT)).replace('\\', '/'):
                                         observer.sha(Path(module.__file__).read_bytes()) for module in (observer, fixtures, engine)},
                          engine_fixture_source_sha256=observer.sha(Path(__file__).read_bytes()),
                          compile_stdout=compiled.stdout, compile_stderr=compiled.stderr, returncode=result.returncode,
                          stdout=result.stdout, stderr=result.stderr, fixture_directory=str(directory),
                          fixture_directory_cleanup='TemporaryDirectory cleanup after this test, including failed assertions.',
                          game_runtime_executed=False, native_text_execution_proven=False, manual_input_proof=False, promotion_ready=False)
            destination = os.environ.get('CLASH_TEXT_OBSERVER_DEBUGGER_REPORT')
            if destination:
                # Preserve an existing report instead of replacing prior failures.
                with Path(destination).open('x', encoding='utf-8') as stream:
                    json.dump(report, stream, indent=2); stream.write('\n')
            self.assertEqual(result.returncode, 0, log)
            self.assertIn('HARNESS_END hr=00000000 paused=1 same_ip=1 unchanged=1', log)
            self.assertIn('HARNESS_CONTEXT before=014c after=014c', log)
            self.assertEqual(len(re.findall(r'^HARNESS_OBSERVER_BODY ', log, re.M)), 5, log)
            self.assertEqual(log.count('MPTEXT_FIXTURE_CONTINUATION_SUPPRESSED'), 5, log)
            self.assertNotRegex(log, r'(?i)syntax error|memory access error|couldn.t resolve|unable to insert|HARNESS_ERROR')
            observations = [observer.EVENT_RE.fullmatch(line) for line in log.splitlines() if line.startswith('MPTEXT_EVENT ')]
            self.assertEqual(len(observations), 3, log)
            self.assertTrue(all(observations), log)
            self.assertEqual([match[1] for match in observations], list(observer.EVENTS))
            self.assertEqual([match['arg5'] for match in observations], ['ffffffff'] * 3)
            self.assertEqual(sum(line.startswith('MPTEXT_OBSERVER_REJECT ') for line in log.splitlines()), 1, log)


if __name__ == '__main__':
    unittest.main(verbosity=2)
