from pathlib import Path
import hashlib, json, os, subprocess, sys
p=Path('src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp')
raw=p.read_bytes()
if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!='fdb6b06ed8d6ea5d547894d5ad59d61fc71a35f9':
    raise SystemExit('Unreviewed proxy input')
s=raw.decode().replace('\r\n','\n')
helper='''const BYTE* indexed_dib_rows(const std::vector<BYTE>& pixels, DWORD width, DWORD height,
                             DWORD pitch, std::vector<BYTE>& storage) {
    if (!width || !height || pitch < width || width > size_t(-1) - 3u ||
        static_cast<size_t>(height) > pixels.size() / pitch) {
        return nullptr;
    }
    const size_t dib_pitch = (static_cast<size_t>(width) + 3u) & ~size_t(3u);
    if (static_cast<size_t>(height) > size_t(-1) / dib_pitch) {
        return nullptr;
    }
    if (pitch == dib_pitch) {
        return pixels.data();
    }
    storage.assign(dib_pitch * height, 0);
    for (DWORD row = 0; row < height; ++row) {
        memcpy(storage.data() + static_cast<size_t>(row) * dib_pitch,
               pixels.data() + static_cast<size_t>(row) * pitch, width);
    }
    return storage.data();
}

'''
s=s.replace('namespace {\n','namespace {\n\n'+helper,1)
s=s.replace('''        // Assumes pitch_ == width_ and width_ is a multiple of 4 (640/800 both
        // are), so the surface rows already satisfy the DIB 4-byte row stride.
''','''        // GDI rows use DWORD alignment even when the native surface is tight.
''')
s=s.replace('''        HDC dc = ::GetDC(g_present_hwnd);''','''        std::vector<BYTE> aligned_pixels;
        const BYTE* dib_pixels = indexed_dib_rows(pixels_, width_, height_, pitch_, aligned_pixels);
        if (!dib_pixels) {
            return;
        }
        HDC dc = ::GetDC(g_present_hwnd);''')
s=s.replace('''                        pixels_.data(), reinterpret_cast<BITMAPINFO*>(&bmi),''','''                        dib_pixels, reinterpret_cast<BITMAPINFO*>(&bmi),''')
new=s.replace('\n','\r\n').encode()
expected='2b2e482e324a4bea302d9457cfeac6566cb7b536a23d636212c06107faef2ffc'
if hashlib.sha256(new).hexdigest()!=expected:raise SystemExit('Unreviewed proxy output')
p.write_bytes(new)
out=Path(os.environ['RUNNER_TEMP'])/'dib-stride-review';out.mkdir()
sys.path[:0]=[str(Path.cwd()),str(Path.cwd()/'tools')]
from run_framed_offline_tests import source_preflight
preflight=source_preflight(Path.cwd())
result=subprocess.run([sys.executable,'tools/test_ddraw_dib_stride.py'],capture_output=True,text=True,timeout=150)
(out/'native-tests.log').write_text(result.stdout+result.stderr)
rows=[json.loads(line.removeprefix('DIB_STRIDE ')) for line in result.stdout.splitlines() if line.startswith('DIB_STRIDE ')]
report=dict(source_preflight=preflight,source_sha256=expected,native_rows=rows,test_exit=result.returncode,
            game_executed=False,promotion_ready=False)
(out/'receipt.json').write_text(json.dumps(report,indent=2)+'\n')
if result.returncode or len(rows)!=1 or not rows[0]['native_gdi_executed'] or not preflight['passed']:
    raise SystemExit('Native GDI fixture or source preflight failed')
subprocess.run(['pwsh','-NoProfile','-ExecutionPolicy','Bypass','-File','scripts/build/build_ddraw_surfdump_proxy.ps1',
                '-OutputDll',str(out/'build/ddraw.dll'),'-LogDir',str(out/'build')],check=True)
(out/'proxy-source.cpp').write_bytes(new)
subprocess.run(['git','diff','--check'],check=True)
subprocess.run(['git','config','user.name','github-actions[bot]'],check=True)
subprocess.run(['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],check=True)
subprocess.run(['git','add','--',str(p)],check=True)
subprocess.run(['git','commit','-m','Fix DWORD-aligned GDI presentation without changing native surface pitch'],check=True)
(out/'commit.txt').write_text(subprocess.check_output(['git','rev-parse','HEAD'],text=True))
subprocess.run(['git','push','origin','HEAD:codex/dib-stride'],check=True)
