"""Launch-runner contracts using source inspection and mock processes only.

PowerShell tests AST-extract helper definitions; they never evaluate the runner
body or start a game/debugger. Packet tests use synthetic private fixture bytes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/cdb/run_battle_hd_visible_session.ps1"
PS = shutil.which("pwsh") or shutil.which("powershell")
if not PS and os.name == "nt":
    candidate = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    PS = str(candidate) if candidate.is_file() else None


class RunnerTests(unittest.TestCase):
    def run_helpers(self, body: str) -> None:
        if os.name != "nt" or not PS:
            self.skipTest("Windows PowerShell mock helpers unavailable; no runtime execution")
        path = str(RUNNER).replace("'", "''")
        script = rf"""
$ErrorActionPreference='Stop'
$tokens=$null; $errors=$null
$ast=[System.Management.Automation.Language.Parser]::ParseFile('{path}',[ref]$tokens,[ref]$errors)
if ($errors.Count) {{ throw ($errors | Out-String) }}
$names=@('Assert-NoReparse','Assert-Approval','Assert-ChildIdentity','Stop-OwnedProcesses')
foreach ($node in $ast.FindAll({{param($n) $n -is [System.Management.Automation.Language.FunctionDefinitionAst]}},$false)) {{
    if ($node.Name -in $names) {{ Invoke-Expression $node.Extent.Text }}
}}
function Require($Condition,[string]$Message) {{ if (-not $Condition) {{ throw $Message }} }}
function Reject([scriptblock]$Action) {{
    $rejected=$false
    try {{ & $Action }} catch {{ $rejected=$true }}
    Require $rejected 'expected rejection'
}}
{body}
"""
        encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
        result = subprocess.run([PS, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                                capture_output=True, text=True, timeout=30,
                                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_powershell_syntax(self):
        self.run_helpers("Require ($names.Count -eq 4) 'helper contract'")

    def test_launch_only_boundary(self):
        text = RUNNER.read_text()
        self.assertNotRegex(text, r"(?i)SendInput|PostMessage|SetCursorPos|SetForegroundWindow|CopyFromScreen|GetWindowRect|raw_sendinput|Stop-Process|Get-Process\s+-Name")
        self.assertEqual(text.count("$debugger = [Diagnostics.Process]::Start($startInfo)"), 1)
        self.assertLess(text.index("if (-not $ExecuteApproved)"), text.index("New-Item -ItemType Directory"))
        self.assertLess(text.index("if (-not $ExecuteApproved)"), text.index("$debugger = [Diagnostics.Process]::Start($startInfo)"))
        for setting in ("FileName = $Cdb", "Arguments = $arguments", "WorkingDirectory = Split-Path $Exe",
                        "UseShellExecute = $false", "CreateNoWindow = $true",
                        "WindowStyle = [Diagnostics.ProcessWindowStyle]::Normal"):
            self.assertIn("$startInfo." + setting, text)
        self.assertNotIn("Start-Process", text)
        self.assertNotRegex(text, r"(?i)WindowStyle\s*(?:=\s*)?(?:\[[^]]+\]::)?Hidden")
        self.assertIn("acceptance_passed=$false; manual_input_proven=$false", text)
        for reason in ("deadline", "stop_request", "debugger_exit", "error"):
            self.assertIn("'" + reason + "'", text)
        self.assertLess(text.index("Assert-ChildIdentity $discoveredProcess"), text.index("$candidate = $discoveredProcess"))

    def test_approval_identity_and_freshness(self):
        self.run_helpers(r"""
$now=[DateTimeOffset]::Parse('2026-09-19T12:00:00Z')
$good=@{user_response='Yes';candidate_sha256='candidate';wrapper_sha256='wrapper';wrapper_mode='proxy-present';stage='stage';resolution='1280x720';scope='visible launch, foreground/cursor control, automated input and screenshots';approval_question='Synthetic fixture only';thread_id='fixture';recorded_at_utc='2026-09-19T11:00:00Z'}
Assert-Approval $good 'candidate' 'wrapper' 'stage' $now
$explicit=$good.Clone();$explicit.user_response='Approve visible rerun'
Assert-Approval $explicit 'candidate' 'wrapper' 'stage' $now
foreach ($answer in @('yes','approve visible rerun','Approve','Continue','Maybe','Yes, perhaps')) {
    $ambiguous=$good.Clone();$ambiguous.user_response=$answer
    Reject { Assert-Approval $ambiguous 'candidate' 'wrapper' 'stage' $now }
}
foreach ($key in @('user_response','candidate_sha256','wrapper_sha256','wrapper_mode','stage','resolution','scope','approval_question','thread_id')) {
    $bad=$good.Clone();$bad[$key]=''
    Reject { Assert-Approval $bad 'candidate' 'wrapper' 'stage' $now }
}
foreach ($time in @('2026-09-18T23:59:59Z','2026-09-19T12:00:01Z','invalid')) {
    $bad=$good.Clone();$bad.recorded_at_utc=$time
    Reject { Assert-Approval $bad 'candidate' 'wrapper' 'stage' $now }
}
""")

    def test_child_identity_rejects_pid_path_parent_and_time_changes(self):
        self.run_helpers(r"""
$time=[datetime]::Parse('2026-09-19T12:00:00Z').ToUniversalTime()
$process=@{Id=7;Path='C:\ClashTests\fixture.exe';StartTime=$time.AddTicks(9)}
$seen=@{ProcessId=7;ParentProcessId=9;ExecutablePath=$process.Path;CreationDate=$time}
$bound=$seen.Clone()
Assert-ChildIdentity $process $seen $bound 9 $process.Path
foreach ($key in @('ProcessId','ParentProcessId','ExecutablePath','CreationDate')) {
    $bad=$bound.Clone()
    if ($key -eq 'CreationDate') { $bad[$key]=$time.AddTicks(10) } else { $bad[$key]='99' }
    Reject { Assert-ChildIdentity $process $seen $bad 9 $process.Path }
}
$bad=$process.Clone();$bad.StartTime=$time.AddTicks(10)
Reject { Assert-ChildIdentity $bad $seen $bound 9 $process.Path }
$bad=$process.Clone();$bad.Id=8
Reject { Assert-ChildIdentity $bad $seen $bound 9 $process.Path }
""")

    def test_cleanup_signals_both_and_contains_individual_errors(self):
        self.run_helpers(r"""
function Fake([string]$Name,[bool]$KillFails,[bool]$WaitFails) {
    $p=[pscustomobject]@{Name=$Name;HasExited=$false;KillFails=$KillFails;WaitFails=$WaitFails}
    $p | Add-Member ScriptMethod Kill {
        $script:events.Add($this.Name+' kill')
        if ($this.KillFails) { throw 'synthetic kill failure' }
        if ($this.Name -eq 'debugger') { $script:released=$true }
    }
    $p | Add-Member ScriptMethod WaitForExit {
        param($Milliseconds)
        $script:events.Add($this.Name+' wait')
        if ($this.WaitFails) { throw 'synthetic wait failure' }
        return $script:released
    }
    return $p
}
foreach ($failure in @('none','kill','wait')) {
    $script:events=[System.Collections.Generic.List[string]]::new();$script:released=$false
    $result=Stop-OwnedProcesses (Fake 'candidate' ($failure -eq 'kill') ($failure -eq 'wait')) (Fake 'debugger' $false $false)
    Require (($script:events -join ',') -eq 'candidate kill,debugger kill,candidate wait,debugger wait') 'cleanup ordering or exception escaped'
    Require $result.debugger_stopped 'debugger cleanup omitted'
    Require (($result.errors.Count -gt 0) -eq ($failure -ne 'none')) 'cleanup error missing'
    Require ($result.candidate_stopped -eq ($failure -ne 'wait')) 'candidate wait result wrong'
}
""")

    def test_reparse_ancestor_rejected_without_creating_links(self):
        self.run_helpers(r"""
function Test-Path { param($LiteralPath) return $true }
function Get-Item { param($LiteralPath,[switch]$Force)
    $flags=[IO.FileAttributes]::Directory
    if ($LiteralPath -eq 'C:\ClashTests\alias') { $flags=$flags -bor [IO.FileAttributes]::ReparsePoint }
    return [pscustomobject]@{Attributes=$flags}
}
Assert-NoReparse 'C:\ClashTests\normal\future\session'
Reject { Assert-NoReparse 'C:\ClashTests\alias\future\session' }
""")

    def test_exact_packet_reconstruction_rejects_tampering(self):
        code = re.search(r"\$verifyPacket = @'\n(.*?)\n'@", RUNNER.read_text(), re.S).group(1)
        with tempfile.TemporaryDirectory(prefix="battle-visible-packet-fixture-") as tmp:
            base = Path(tmp); (base / "save").mkdir()
            producer = base / "producer.py"
            producer.write_text("""import hashlib
from pathlib import Path
def sha(data): return hashlib.sha256(data).hexdigest()
def snapshot_script(): return 'snapshot\\n'
def snapshot_commands(): return 'snapshot'
def build_probe(original,candidate,save,**kw):
 return 'probe\\n',dict(schema='clash95_battle_hd_visible_probe_v1',stage=kw['stage'],resolution=kw['resolution'],producer_sha256=sha(Path(__file__).read_bytes()),byte_spans=[{'old_hex':'01','candidate_hex':'02'}])
""")
            candidate = base / "candidate.exe"; candidate.write_bytes(b"synthetic, not executable")
            original = base / "original.bin"; original.write_bytes(b"original fixture")
            save = base / "save/0.dat"; save.write_bytes(b"save fixture")
            probe = base / "probe.cdb"; probe.write_bytes(b"probe\n")
            snapshot = base / "snapshot.cdb"; snapshot.write_bytes(b"snapshot\n")
            packet = dict(schema="clash95_battle_hd_visible_probe_v1", stage="fixture", resolution="1280x720",
                          producer_sha256=hashlib.sha256(producer.read_bytes()).hexdigest(),
                          byte_spans=[{"old_hex":"01","candidate_hex":"02"}],
                          candidate_path=str(candidate), probe_path=str(probe), original_path=str(original),
                          save_path=str(save), snapshot_path=str(snapshot), snapshot_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest())
            path = base / "packet.json"
            def run(value):
                path.write_text(json.dumps(value))
                return subprocess.run([sys.executable, "-B", "-c", code, str(producer), str(path), str(candidate), str(probe)], capture_output=True, text=True, timeout=15)
            good = run(packet)
            self.assertEqual(good.returncode, 0, good.stderr)
            for key, value in (("schema","unknown"),("producer_sha256","0"*64),("byte_spans",[]),
                               ("candidate_path",str(original)),("probe_path",str(snapshot)),
                               ("save_path",str(original)),("snapshot_sha256","0"*64)):
                self.assertNotEqual(run(packet | {key:value}).returncode, 0, key)
            probe.write_bytes(b"modified commands\n")
            self.assertNotEqual(run(packet).returncode, 0)


if __name__ == "__main__":
    unittest.main()
