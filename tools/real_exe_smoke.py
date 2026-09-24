"""Explicitly opt-in launch of a verified original Clash EXE on a disposable Windows runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time

ORIGINAL_SHA256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
ASSET_COMMIT = '84a1e4bcf131e6bb75b39fc5e10941dd0b801767'
HARNESS = r'''
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <dbgeng.h>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <iterator>
#include <stdexcept>
#include <string>
#include <vector>

static void check(HRESULT hr, const char *op) {
    if (hr != S_OK) { char b[200]; sprintf_s(b,"%s hr=%08lx",op,hr); throw std::runtime_error(b); }
}
static void save(const std::string &path, const void *data, size_t size) {
    std::ofstream f(path,std::ios::binary); f.write(static_cast<const char *>(data),size);
    if (!f) throw std::runtime_error("capture write failed");
}
struct LogOutput : IDebugOutputCallbacks {
    LONG refs=1;
    STDMETHOD(QueryInterface)(REFIID id,PVOID *p) {
        if (!p) return E_POINTER; *p=nullptr;
        if (id!=__uuidof(IUnknown) && id!=__uuidof(IDebugOutputCallbacks)) return E_NOINTERFACE;
        *p=static_cast<IDebugOutputCallbacks *>(this); AddRef(); return S_OK;
    }
    STDMETHOD_(ULONG,AddRef)() { return InterlockedIncrement(&refs); }
    STDMETHOD_(ULONG,Release)() { return InterlockedDecrement(&refs); }
    STDMETHOD(Output)(ULONG,PCSTR s) { fputs(s,stdout); fflush(stdout); return S_OK; }
};
struct Session {
    HMODULE engine=nullptr;
    IDebugClient *client=nullptr;
    IDebugControl *control=nullptr;
    IDebugDataSpaces *memory=nullptr;
    IDebugSystemObjects *system=nullptr;
    IDebugRegisters *registers=nullptr;
    IDebugSymbols *symbols=nullptr;
    HANDLE process=nullptr, job=nullptr, primary_thread=nullptr;
    ULONG owned_pid=0, primary_tid=0;
    ~Session() {
        if (client) client->EndSession(DEBUG_END_ACTIVE_TERMINATE);
        if (job) CloseHandle(job);
        if (process) {
            DWORD waited=WaitForSingleObject(process,5000);
            if (waited!=WAIT_OBJECT_0) { TerminateProcess(process,0x534d4f4b); waited=WaitForSingleObject(process,5000); }
            DWORD code=0; GetExitCodeProcess(process,&code);
            printf("REAL_CLEANUP absent=%d exit=%08lx\n",waited==WAIT_OBJECT_0,code); fflush(stdout);
            CloseHandle(process);
        }
        if (primary_thread) CloseHandle(primary_thread);
        if (symbols) symbols->Release(); if (registers) registers->Release();
        if (system) system->Release(); if (memory) memory->Release();
        if (control) control->Release(); if (client) client->Release();
        if (engine) FreeLibrary(engine);
    }
    std::vector<unsigned char> read(ULONG address,ULONG size) {
        if (address<0x10000 || size>16000000 || address>0x7fffffff-size) throw std::runtime_error("bounded read rejected");
        std::vector<unsigned char> bytes(size); ULONG actual=0;
        check(memory->ReadVirtual(address,bytes.data(),size,&actual),"ReadVirtual");
        if (actual!=size) throw std::runtime_error("short memory read"); return bytes;
    }
    ULONG word(ULONG address) { auto b=read(address,4); ULONG v; memcpy(&v,b.data(),4); return v; }
    void command(const char *s) { check(control->Execute(DEBUG_OUTCTL_THIS_CLIENT,s,DEBUG_EXECUTE_NO_REPEAT),s); }
};
struct Windows { DWORD pid; std::string out; int sample; int count=0; };
static BOOL CALLBACK window(HWND hwnd,LPARAM arg) {
    auto &w=*reinterpret_cast<Windows *>(arg); DWORD pid=0; GetWindowThreadProcessId(hwnd,&pid);
    if (pid!=w.pid) return TRUE;
    char title[1024]={},cls[256]={}; GetWindowTextA(hwnd,title,sizeof(title)); GetClassNameA(hwnd,cls,sizeof(cls));
    RECT r={}; GetWindowRect(hwnd,&r); int width=r.right-r.left,height=r.bottom-r.top;
    printf("REAL_WINDOW sample=%d hwnd=%p visible=%d class=%s title=%s rect=%ld,%ld,%ld,%ld\n",w.sample,hwnd,IsWindowVisible(hwnd),cls,title,r.left,r.top,r.right,r.bottom);
    if (!IsWindowVisible(hwnd) || width<1 || height<1 || width>4096 || height>2160) return TRUE;
    HDC src=GetWindowDC(hwnd); if (!src) return TRUE;
    HDC dst=CreateCompatibleDC(src); void *bits=nullptr; BITMAPINFO info={};
    info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER); info.bmiHeader.biWidth=width;
    info.bmiHeader.biHeight=-height; info.bmiHeader.biPlanes=1; info.bmiHeader.biBitCount=32;
    HBITMAP bitmap=CreateDIBSection(src,&info,DIB_RGB_COLORS,&bits,nullptr,0);
    if (bitmap && dst) {
        HGDIOBJ old=SelectObject(dst,bitmap);
        if (BitBlt(dst,0,0,width,height,src,0,0,SRCCOPY|CAPTUREBLT)) {
            BITMAPFILEHEADER header={}; header.bfType=0x4d42; header.bfOffBits=sizeof(header)+sizeof(BITMAPINFOHEADER);
            header.bfSize=header.bfOffBits+width*height*4;
            char suffix[80]; sprintf_s(suffix,"/window-%02d-%02d.bmp",w.sample,w.count++);
            std::ofstream f(w.out+suffix,std::ios::binary);
            f.write(reinterpret_cast<char *>(&header),sizeof(header));
            f.write(reinterpret_cast<char *>(&info.bmiHeader),sizeof(info.bmiHeader));
            f.write(static_cast<char *>(bits),width*height*4);
        }
        SelectObject(dst,old);
    }
    if (bitmap) DeleteObject(bitmap); if (dst) DeleteDC(dst); ReleaseDC(hwnd,src); return TRUE;
}
static void select_owned_primary(Session &s) {
    if (!s.process || !s.primary_thread || WaitForSingleObject(s.process,0)!=WAIT_TIMEOUT ||
        WaitForSingleObject(s.primary_thread,0)!=WAIT_TIMEOUT)
        throw std::runtime_error("owned process or primary thread is no longer alive");
    ULONG status=0,process=0,thread=0,pid=0,tid=0;
    check(s.control->GetExecutionStatus(&status),"owned selection status");
    if (status!=DEBUG_STATUS_BREAK) throw std::runtime_error("owned selection requires a stopped debuggee");
    check(s.system->GetProcessIdBySystemId(s.owned_pid,&process),"resolve owned debugger process");
    check(s.system->SetCurrentProcessId(process),"select owned debugger process");
    check(s.system->GetThreadIdBySystemId(s.primary_tid,&thread),"resolve retained primary thread");
    check(s.system->SetCurrentThreadId(thread),"select retained primary thread");
    check(s.system->GetCurrentProcessSystemId(&pid),"verify selected process");
    check(s.system->GetCurrentThreadSystemId(&tid),"verify selected thread");
    if (pid!=s.owned_pid || tid!=s.primary_tid) throw std::runtime_error("selected debugger identity differs");
    ULONG64 ip=0; check(s.registers->GetInstructionOffset(&ip),"selected primary instruction offset");
    printf("REAL_CONTEXT pid=%lu tid=%lu engine_process=%lu engine_thread=%lu ip=%08llx retained_handles_alive=1\n",pid,tid,process,thread,ip);
    fflush(stdout);
}
static void pause_owned(Session &s) {
    if (!DebugBreakProcess(s.process)) throw std::runtime_error("owned DebugBreakProcess failed");
    check(s.control->WaitForEvent(0,10000),"owned native break event");
    ULONG status=0; check(s.control->GetExecutionStatus(&status),"paused status");
    if (status!=DEBUG_STATUS_BREAK) throw std::runtime_error("owned native break did not pause the target");
    select_owned_primary(s);
    printf("REAL_PAUSE method=DebugBreakProcess paused=1\n"); fflush(stdout);
}
static void snapshot(Session &s,const std::string &out,int sample,bool proxy) {
    char prefix[80]; sprintf_s(prefix,"/primary-%02d",sample); std::string path=out+prefix;
    try {
        auto p=s.read(0x51d4c0,220); USHORT width,height; memcpy(&width,p.data(),2); memcpy(&height,p.data()+2,2);
        ULONG backend; memcpy(&backend,p.data()+0xbc,4); auto b=s.read(backend,176);
        auto u=[&](size_t at) { ULONG v; memcpy(&v,b.data()+at,4); return v; };
        ULONG pitch=u(0x48),pixels=u(0x5c),surface=u(0xa4);
        if (width<640 || width>4096 || height<480 || height>2160 || pitch<width || pitch>8192 || u(0x38)!=108 || u(0x40)!=height || u(0x44)!=width)
            throw std::runtime_error("cached primary Lock descriptor is unavailable");
        auto raw=s.read(pixels,pitch*height); auto after=s.read(backend,176);
        if (b!=after) throw std::runtime_error("paused cached header changed");
        save(path+".raw",raw.data(),raw.size()); save(path+"-header.bin",p.data(),p.size()); save(path+"-backend.bin",b.data(),b.size());
        bool palette=false;
        if (proxy) {
            try { ULONG pal=s.word(surface+28); auto entries=s.read(pal+12,1024); save(path+"-palette.bin",entries.data(),entries.size()); palette=true; }
            catch (const std::exception &e) { printf("REAL_PALETTE_UNAVAILABLE %s\n",e.what()); }
        }
        std::ofstream meta(path+".json");
        meta<<"{\"width\":"<<width<<",\"height\":"<<height<<",\"pitch\":"<<pitch<<",\"pixels\":"<<pixels<<",\"backend\":"<<backend<<",\"surface\":"<<surface<<",\"paused\":true,\"proxy_private_palette\":"<<(palette?"true":"false")<<"}\n";
        printf("REAL_PRIMARY sample=%d width=%u height=%u pitch=%lu bytes=%zu palette=%d\n",sample,width,height,pitch,raw.size(),palette);
    } catch(const std::exception &e) { printf("REAL_PRIMARY_UNAVAILABLE sample=%d reason=%s\n",sample,e.what()); }
}
int main(int argc,char **argv) {
    if (argc!=5) return 2;
    const int seconds=atoi(argv[3]); if (seconds<10 || seconds>90) return 2;
    LogOutput output; Session s;
    try {
        SetErrorMode(SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX|SEM_NOOPENFILEERRORBOX);
        char sysdir[MAX_PATH]={},enginepath[MAX_PATH]={}; GetSystemDirectoryA(sysdir,MAX_PATH);
        sprintf_s(enginepath,"%s\\dbgeng.dll",sysdir); s.engine=LoadLibraryExA(enginepath,nullptr,LOAD_LIBRARY_SEARCH_SYSTEM32);
        if (!s.engine) throw std::runtime_error("system x86 DbgEng unavailable");
        auto create=reinterpret_cast<HRESULT(WINAPI *)(REFIID,PVOID *)>(GetProcAddress(s.engine,"DebugCreate"));
        if (!create) throw std::runtime_error("DebugCreate missing");
        check(create(__uuidof(IDebugClient),reinterpret_cast<void **>(&s.client)),"DebugCreate");
        check(s.client->QueryInterface(__uuidof(IDebugControl),reinterpret_cast<void **>(&s.control)),"control");
        check(s.client->QueryInterface(__uuidof(IDebugDataSpaces),reinterpret_cast<void **>(&s.memory)),"memory");
        check(s.client->QueryInterface(__uuidof(IDebugSystemObjects),reinterpret_cast<void **>(&s.system)),"system");
        check(s.client->QueryInterface(__uuidof(IDebugRegisters),reinterpret_cast<void **>(&s.registers)),"registers");
        check(s.client->QueryInterface(__uuidof(IDebugSymbols),reinterpret_cast<void **>(&s.symbols)),"symbols");
        check(s.client->SetOutputCallbacks(&output),"output"); check(s.symbols->SetSymbolPath("."),"symbol path");
        check(s.control->AddEngineOptions(DEBUG_ENGOPT_INITIAL_BREAK|DEBUG_ENGOPT_DISALLOW_SHELL_COMMANDS),"options");
        std::ifstream f(argv[1],std::ios::binary); std::vector<unsigned char> disk((std::istreambuf_iterator<char>(f)),std::istreambuf_iterator<char>());
        if (disk.size()<4096 || memcmp(disk.data(),"MZ",2)) throw std::runtime_error("not a PE image");
        ULONG off; memcpy(&off,disk.data()+60,4);
        if (off>disk.size()-sizeof(IMAGE_NT_HEADERS32)) throw std::runtime_error("PE offset out of bounds");
        const auto *nt=reinterpret_cast<const IMAGE_NT_HEADERS32 *>(disk.data()+off);
        if (nt->Signature!=IMAGE_NT_SIGNATURE || nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_I386) throw std::runtime_error("not x86 PE");
        std::string cmd=std::string("\"")+argv[1]+"\""; std::vector<char> command(cmd.begin(),cmd.end()); command.push_back(0);
        check(s.client->CreateProcess(0,command.data(),DEBUG_ONLY_THIS_PROCESS),"CreateProcess real EXE");
        check(s.control->WaitForEvent(0,15000),"initial loader event");
        ULONG pid=0; check(s.system->GetCurrentProcessSystemId(&pid),"Get process id");
        s.owned_pid=pid;
        check(s.system->GetCurrentThreadSystemId(&s.primary_tid),"retain primary system thread id");
        s.primary_thread=OpenThread(SYNCHRONIZE|THREAD_QUERY_LIMITED_INFORMATION,FALSE,s.primary_tid);
        if (!s.primary_thread) throw std::runtime_error("retain primary thread handle failed");
        s.process=OpenProcess(PROCESS_ALL_ACCESS,FALSE,pid);
        if (!s.process) throw std::runtime_error("retain process handle failed");
        s.job=CreateJobObjectA(nullptr,nullptr); JOBOBJECT_EXTENDED_LIMIT_INFORMATION limit={};
        limit.BasicLimitInformation.LimitFlags=JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
        if (!s.job || !SetInformationJobObject(s.job,JobObjectExtendedLimitInformation,&limit,sizeof(limit)) || !AssignProcessToJobObject(s.job,s.process)) throw std::runtime_error("owned job assignment failed");
        ULONG64 peb=0; check(s.system->GetCurrentProcessPeb(&peb),"PEB"); ULONG base=s.word(static_cast<ULONG>(peb)+8);
        if (base!=nt->OptionalHeader.ImageBase || s.control->IsPointer64Bit()!=S_FALSE) throw std::runtime_error("unexpected image base or architecture");
        const auto *sections=IMAGE_FIRST_SECTION(nt);
        for (int n=0;n<nt->FileHeader.NumberOfSections;++n) {
            const auto &sec=sections[n]; if (!(sec.Characteristics&IMAGE_SCN_MEM_EXECUTE) || !sec.SizeOfRawData) continue;
            if (sec.PointerToRawData>disk.size() || sec.SizeOfRawData>disk.size()-sec.PointerToRawData) throw std::runtime_error("invalid executable section");
            auto bytes=s.read(base+sec.VirtualAddress,sec.SizeOfRawData);
            if (memcmp(bytes.data(),disk.data()+sec.PointerToRawData,bytes.size())) throw std::runtime_error("loaded executable code differs from verified disk image");
        }
        ULONG entry=base+nt->OptionalHeader.AddressOfEntryPoint;
        IDebugBreakpoint *bp=nullptr; check(s.control->AddBreakpoint(DEBUG_BREAKPOINT_CODE,DEBUG_ANY_ID,&bp),"entry breakpoint");
        check(bp->SetOffset(entry),"entry offset"); check(bp->AddFlags(DEBUG_BREAKPOINT_ENABLED|DEBUG_BREAKPOINT_ONE_SHOT),"entry flags"); bp->Release();
        printf("REAL_LOADED pid=%lu base=%08lx entry=%08lx executable_sections_match=1\n",pid,base,entry); fflush(stdout);
        s.command("sxe av"); s.command("sxe eh");
        bool entered=false,exited=false,crashed=false; int sample=0; ULONGLONG start=GetTickCount64(),next=start+10000;
        check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"run actual code");
        while (GetTickCount64()-start<static_cast<ULONGLONG>(seconds)*1000) {
            HRESULT hr=s.control->WaitForEvent(0,1000);
            ULONG status=0; if (s.control->GetExecutionStatus(&status)!=S_OK || status==DEBUG_STATUS_NO_DEBUGGEE) { exited=true; break; }
            if (hr==S_OK && status==DEBUG_STATUS_BREAK) {
                ULONG64 ip=0; s.registers->GetInstructionOffset(&ip); ULONG type=0,proc=0,thread=0,used=0,descrUsed=0;
                unsigned char extra[1024]={}; char descr[1024]={};
                s.control->GetLastEventInformation(&type,&proc,&thread,extra,sizeof(extra),&used,descr,sizeof(descr),&descrUsed);
                printf("REAL_EVENT type=%lu ip=%08llx description=%s\n",type,ip,descr); fflush(stdout);
                if (ip==entry && !entered) { entered=true; printf("REAL_EXE_ENTRY observed=1\n"); }
                else if (type==DEBUG_EVENT_EXCEPTION) {
                    auto *e=reinterpret_cast<DEBUG_LAST_EVENT_INFO_EXCEPTION *>(extra);
                    printf("REAL_EXCEPTION code=%08lx first_chance=%lu\n",e->ExceptionRecord.ExceptionCode,e->FirstChance);
                    if (e->ExceptionRecord.ExceptionCode==EXCEPTION_ACCESS_VIOLATION || !e->FirstChance) { crashed=true; break; }
                    check(s.control->SetExecutionStatus(DEBUG_STATUS_GO_NOT_HANDLED),"forward native exception"); continue;
                } else if (type==DEBUG_EVENT_EXIT_PROCESS) { exited=true; break; }
                check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"continue actual code");
            } else if (FAILED(hr)) { printf("REAL_WAIT_ERROR hr=%08lx\n",hr); break; }
            if (GetTickCount64()>=next) {
                Windows windows{pid,argv[2],sample}; EnumWindows(window,reinterpret_cast<LPARAM>(&windows));
                pause_owned(s);
                snapshot(s,argv[2],sample++,strcmp(argv[4],"proxy")==0);
                s.command(".lastevent"); s.command("~*kb 12");
                check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"resume after read"); next=GetTickCount64()+10000;
            }
        }
        ULONG status=0; s.control->GetExecutionStatus(&status);
        if (!exited && status!=DEBUG_STATUS_NO_DEBUGGEE) {
            if (status!=DEBUG_STATUS_BREAK) pause_owned(s);
            else if (!crashed) select_owned_primary(s);
            snapshot(s,argv[2],sample,strcmp(argv[4],"proxy")==0);
            s.command(".lastevent"); s.command("r"); s.command("~*kb 20"); s.command("lm");
        }
        printf("REAL_END entered=%d exited=%d exception_stop=%d elapsed_ms=%llu\n",entered,exited,crashed,GetTickCount64()-start); fflush(stdout);
        return crashed?4:(entered?0:3);
    } catch(const std::exception &e) { fprintf(stderr,"REAL_HARNESS_ERROR %s winerror=%lu\n",e.what(),GetLastError()); return 2; }
}
'''


def sha(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def verify(runtime: Path, manifest: dict) -> dict:
    rows = manifest['runtime']['files']
    receipts = {}
    for row in rows:
        path = runtime / row['path']
        if not path.resolve().is_relative_to(runtime.resolve()) or path.is_symlink():
            raise ValueError('runtime path escapes reference root')
        if path.stat().st_size != row['size'] or sha(path) != row['sha256']:
            raise ValueError('original input size/hash mismatch: ' + row['path'])
        receipts[row['path']] = {'bytes': row['size'], 'sha256': row['sha256']}
    if len(rows) != 60 or sum(row['size'] for row in rows) != 517940933:
        raise ValueError('unexpected runtime inventory')
    actual = {path.relative_to(runtime).as_posix() for path in runtime.rglob('*') if path.is_file()}
    if actual != set(receipts) or len(receipts) != len(rows):
        raise ValueError('reference runtime contains missing, extra, or duplicate paths')
    if sha(runtime / 'clash95.exe') != ORIGINAL_SHA256:
        raise ValueError('unsupported original executable')
    return receipts


def compile_harness(out: Path) -> Path:
    source = out / 'real-exe-engine.cpp'
    source.write_text(HARNESS, encoding='utf-8')
    vswhere = Path(os.environ['ProgramFiles(x86)']) / 'Microsoft Visual Studio/Installer/vswhere.exe'
    install = subprocess.check_output([str(vswhere), '-latest', '-products', '*', '-requires',
        'Microsoft.VisualStudio.Component.VC.Tools.x86.x64', '-property', 'installationPath'], text=True).strip()
    vcvars = Path(install) / 'VC/Auxiliary/Build/vcvars32.bat'
    exe = out / 'real-exe-engine.exe'
    command = out / 'compile.cmd'
    command.write_text(f'@echo off\ncall "{vcvars}" >nul\ncl /nologo /EHsc /W4 /O2 /MT "{source}" /Fo"{out / "engine.obj"}" /Fe"{exe}" /link /MACHINE:X86 user32.lib gdi32.lib\nexit /b %ERRORLEVEL%\n', encoding='ascii')
    result = subprocess.run(['cmd.exe', '/d', '/c', str(command)], cwd=out, capture_output=True, text=True, timeout=120)
    (out / 'compile.log').write_text(result.stdout + result.stderr, encoding='utf-8')
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return exe


def render(out: Path) -> list[dict]:
    from PIL import Image
    results = []
    for meta in sorted(out.glob('primary-*.json')):
        data = json.loads(meta.read_text())
        raw = meta.with_suffix('.raw').read_bytes()
        image = Image.frombytes('P', (data['width'], data['height']), raw, 'raw', 'P', data['pitch'], 1)
        palette = meta.with_name(meta.stem + '-palette.bin')
        if palette.exists() and any(palette.read_bytes()[i:i+3] != b'\0\0\0' for i in range(0,1024,4)):
            p = palette.read_bytes()
            image.putpalette(bytes(v for i in range(0,1024,4) for v in p[i:i+3]))
            data['palette_mode'] = 'paused_diagnostic_proxy_private_palette'
        else:
            image.putpalette(bytes(v for i in range(256) for v in (i,i,i)))
            data['palette_mode'] = 'grayscale_index_preview'
        png = meta.with_suffix('.png')
        image.convert('RGB').save(png)
        data.update(png=png.name, png_sha256=sha(png), raw_sha256=sha(meta.with_suffix('.raw')),
                    nonzero_indices=sum(pixel != 0 for pixel in image.tobytes()), visual_acceptance=False)
        meta.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')
        results.append(data)
    for bmp in out.glob('window-*.bmp'):
        with Image.open(bmp) as image:
            image.convert('RGB').save(bmp.with_suffix('.png'))
    return results


def outcome(log: str, returncode: int) -> dict:
    lines = log.splitlines()
    endings = [re.fullmatch(r'REAL_END entered=([01]) exited=([01]) exception_stop=([01]) elapsed_ms=([0-9]+)', line)
               for line in lines if line.startswith('REAL_END ')]
    complete = returncode == 0 and len(endings) == 1 and endings[0] is not None
    if complete:
        complete = endings[0][1] == '1' and endings[0][3] == '0'
    failures = [line for line in lines if line.startswith(('REAL_HARNESS_ERROR ', 'REAL_WAIT_ERROR '))]
    entry = lines.count('REAL_EXE_ENTRY observed=1') == 1
    loaded = sum(bool(re.fullmatch(r'REAL_LOADED pid=[0-9]+ base=[0-9a-f]+ entry=[0-9a-f]+ executable_sections_match=1', line)) for line in lines) == 1
    cleanup = sum(bool(re.fullmatch(r'REAL_CLEANUP absent=1 exit=[0-9a-f]{8}', line)) for line in lines) == 1
    return dict(entry_observed=entry, loaded_code_matches=loaded, owned_process_absent=cleanup,
                observation_complete=bool(complete and entry and loaded and cleanup and not failures),
                harness_errors=failures)



HD_RESOLUTIONS = ('800x600', '1024x768', '1280x720', '1280x960', '1920x1080', '802x602')
HD_RECIPES = {
    'completehd': ('src.patcher.complete_hd_candidate', '-completehd-validation', 'complete_hd_v1'),
    'modalwidgets': ('tools.build_framed_modal_widgets_candidate', '-completehd-modalwidgets-validation',
                     'owned_modal_widget_bounds_v1'),
}


def prepare_hd_bundle(original: Path, out: Path, recipe: str, resolution: str) -> tuple[Path, dict]:
    import importlib
    if recipe not in HD_RECIPES or resolution not in HD_RESOLUTIONS:
        raise ValueError('explicit supported HD recipe and resolution required')
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    from src.patcher.patch_clash95_hd import DEFAULT_STAGE
    module_name, suffix, revision = HD_RECIPES[recipe]
    builder = importlib.import_module(module_name)
    if builder.STAGE != DEFAULT_STAGE + suffix or builder.REVISION != revision:
        raise ValueError('HD builder stage/revision differs from the selected recipe')
    name = 'clash95_hd_1024.exe' if (recipe, resolution) == ('completehd', '1024x768') else f'clash95_hd_{recipe}_{resolution}.exe'
    candidate = out / 'bundle' / name
    metadata = builder.write_candidate(original, candidate, resolution)
    if (metadata['stage'] != builder.STAGE or metadata['recipe_revision'] != revision
            or metadata['resolution'] != resolution or metadata['candidate_sha256'] != sha(candidate)
            or sha(candidate.with_suffix('.cdb')) != metadata['probe_sha256']
            or candidate.with_suffix('.candidate.json').read_bytes() !=
                (json.dumps(metadata, indent=2) + '\n').encode('utf-8')):
        raise ValueError('HD bundle bytes or identity differ from the selected recipe')
    verify_hd_sources(metadata, root)
    return candidate, metadata


def verify_hd_sources(metadata: dict, root: Path) -> None:
    sources = metadata.get('source_hashes')
    if not isinstance(sources, dict) or not sources:
        raise ValueError('complete HD source identities required')
    for name, digest in sources.items():
        if (not isinstance(name, str) or '\\' in name or ':' in name
                or PurePosixPath(name).is_absolute() or '..' in PurePosixPath(name).parts
                or PurePosixPath(name).as_posix() != name
                or not isinstance(digest, str) or re.fullmatch(r'[0-9a-f]{64}', digest) is None):
            raise ValueError('noncanonical HD source path or SHA256')
        path = root / name
        if not path.resolve().is_relative_to(root.resolve()) or sha(path) != digest:
            raise ValueError('HD source changed: ' + name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--proxy', type=Path)
    parser.add_argument('--complete-hd', action='store_true')
    parser.add_argument('--hd-recipe', choices=tuple(HD_RECIPES), default='completehd')
    parser.add_argument('--hd-resolution', choices=HD_RESOLUTIONS, default='1024x768')
    parser.add_argument('--hd-only', action='store_true')
    parser.add_argument('--seconds', type=int, choices=range(10,91), default=40)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    if not args.complete_hd and (args.hd_only or args.hd_recipe != 'completehd' or args.hd_resolution != '1024x768'):
        parser.error('HD recipe, resolution and HD-only selection require --complete-hd')
    if not args.execute:
        print(json.dumps({'executed': False, 'original_sha256': ORIGINAL_SHA256,
                          'hd_recipe': args.hd_recipe if args.complete_hd else None,
                          'hd_resolution': args.hd_resolution if args.complete_hd else None,
                          'hd_only': args.hd_only,
                          'operation': 'launch verified original copies with shipped wrapper and optional diagnostic proxy'}))
        return 0
    if args.complete_hd and args.proxy is None:
        parser.error('complete-HD comparison requires the diagnostic proxy')
    if os.name != 'nt':
        parser.error('actual Windows runner required')
    runtime, out = args.runtime.resolve(), args.out.resolve()
    root = Path(__file__).resolve().parents[1]
    if out.is_relative_to(root) or out.is_relative_to(runtime) or runtime.is_relative_to(out):
        parser.error('output must be separate from repository and original assets')
    out.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(args.manifest.read_text(encoding='utf-8'))
    report = {'schema': 1, 'asset_commit': ASSET_COMMIT, 'original_sha256': ORIGINAL_SHA256,
              'manual_input_proof': False, 'promotion_ready': False, 'runs': [], 'errors': []}
    try:
        report['inputs'] = verify(runtime, manifest)
        report['source_sha256'] = sha(Path(__file__))
        engine = compile_harness(out)
        report['engine_sha256'] = sha(engine)
        cases = [] if args.hd_only else [('gog', None)]
        hd_metadata = None
        if args.proxy:
            proxy = args.proxy.resolve()
            proxy_manifest = json.loads(proxy.with_name('ddraw_surfdump_proxy.build.json').read_text(encoding='utf-8-sig'))
            if (proxy_manifest['generated_by'] != 'clash-hd-surface-dump-proxy'
                    or sha(proxy) != proxy_manifest['output_sha256'].lower()
                    or sha(root/'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp') != proxy_manifest['source_sha256'].lower()):
                raise ValueError('diagnostic proxy build/source identity differs')
            report['proxy_build'] = proxy_manifest
            if not args.hd_only:
                cases.append(('proxy', None))
        if args.complete_hd:
            candidate, hd_metadata = prepare_hd_bundle(runtime/'clash95.exe', out, args.hd_recipe, args.hd_resolution)
            report['hd_recipe'] = args.hd_recipe
            report['hd_candidate_manifest'] = hd_metadata
            if args.hd_recipe == 'completehd':
                report['complete_hd_manifest'] = hd_metadata
            cases.append((args.hd_recipe + '-proxy', candidate))
        for mode, candidate in cases:
            work = out / ('work-' + mode)
            shutil.copytree(runtime, work)
            for directory in manifest['runtime']['empty_directories']:
                (work / directory).mkdir(parents=True, exist_ok=True)
            using_proxy = mode != 'gog'
            if using_proxy:
                shutil.copy2(args.proxy, work / 'ddraw.dll')
            executable = work/'clash95.exe'
            expected = ORIGINAL_SHA256
            if candidate is not None:
                executable = work/candidate.name
                shutil.copy2(candidate, executable)
                expected = hd_metadata['candidate_sha256']
                verify_hd_sources(hd_metadata, root)
            if sha(executable) != expected:
                raise ValueError('staged executable differs from authenticated input')
            capture = out / mode
            capture.mkdir()
            before = sha(executable)
            env = {**os.environ, '_NT_SYMBOL_PATH': '.', '_NT_ALT_SYMBOL_PATH': '', 'CLASH_PROXY_PRESENT': '1' if using_proxy else '0'}
            started = time.monotonic()
            result = subprocess.run([str(engine), str(executable), str(capture), str(args.seconds), 'proxy' if using_proxy else 'gog'],
                                    cwd=work, env=env, capture_output=True, text=True, errors='replace', timeout=args.seconds+100)
            log = result.stdout + '\n' + result.stderr
            (capture / 'debugger.log').write_text(log, encoding='utf-8')
            for name in ('ddraw_surfdump_proxy.log','ddraw_surfdump_palette.bin'):
                if (work / name).is_file(): shutil.copy2(work / name, capture / name)
            if candidate is not None:
                verify_hd_sources(hd_metadata, root)
            snapshots = render(capture)
            dimensions_match = bool(snapshots) and all(
                f"{item['width']}x{item['height']}" == args.hd_resolution for item in snapshots) if candidate is not None else None
            row = {'mode': mode, 'exe_sha256': before, 'wrapper_sha256': sha(work / 'ddraw.dll'),
                   'returncode': result.returncode, 'elapsed_seconds': round(time.monotonic()-started,3),
                   **outcome(log, result.returncode),
                   'exe_unchanged': before == sha(executable),
                   'original_copy_unchanged': sha(work/'clash95.exe') == ORIGINAL_SHA256,
                   'stage': hd_metadata['stage'] if candidate is not None else 'original-unpatched',
                   'recipe_revision': hd_metadata['recipe_revision'] if candidate is not None else None,
                   'resolution': args.hd_resolution if candidate is not None else '640x480',
                   'candidate_sources_unchanged': True if candidate is not None else None,
                   'requested_surface_observed': dimensions_match,
                   'gameplay_verified': False,
                   'snapshots': snapshots, 'log_sha256': sha(capture / 'debugger.log')}
            report['runs'].append(row)
            print(json.dumps(row, indent=2), flush=True)
        report['original_inputs_unchanged'] = verify(runtime, manifest) == report['inputs']
        report['game_entry_executed'] = any(row['entry_observed'] for row in report['runs'])
    except Exception as error:
        report['errors'].append(f'{type(error).__name__}: {error}')
        print(report['errors'][-1], file=sys.stderr, flush=True)
    finally:
        (out / 'summary.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    return int(bool(report['errors']) or not report.get('game_entry_executed') or
               not report.get('original_inputs_unchanged') or
               any(not r['observation_complete'] or not r['owned_process_absent'] or not r['exe_unchanged']
                   or not r['original_copy_unchanged'] or r['requested_surface_observed'] is False for r in report['runs']))


if __name__ == '__main__':
    raise SystemExit(main())
