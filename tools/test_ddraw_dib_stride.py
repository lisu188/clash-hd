"""Compile the production row adapter; Windows also exercises real memory-DC GDI."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'src/ddraw_surfdump_proxy/ddraw_surfdump_proxy.cpp'
FIXTURE = r'''
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <vector>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#else
using BYTE = unsigned char;
using DWORD = uint32_t;
#endif
PRODUCTION_HELPER
static BYTE value(DWORD x, DWORD y) { return static_cast<BYTE>((x * 7 + y * 19 + 11) % 251 + 1); }
static bool gdi_equal(const BYTE* data, DWORD w, DWORD h) {
#ifdef _WIN32
    HDC dc = CreateCompatibleDC(nullptr);
    if (!dc) return false;
    BITMAPINFO dst = {};
    dst.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    dst.bmiHeader.biWidth = w; dst.bmiHeader.biHeight = -static_cast<LONG>(h);
    dst.bmiHeader.biPlanes = 1; dst.bmiHeader.biBitCount = 32;
    void* bits = nullptr;
    HBITMAP bitmap = CreateDIBSection(dc, &dst, DIB_RGB_COLORS, &bits, nullptr, 0);
    if (!bitmap) { DeleteDC(dc); return false; }
    HGDIOBJ old = SelectObject(dc, bitmap);
    struct { BITMAPINFOHEADER header; RGBQUAD colors[256]; } src = {};
    src.header.biSize = sizeof(BITMAPINFOHEADER);
    src.header.biWidth = w; src.header.biHeight = -static_cast<LONG>(h);
    src.header.biPlanes = 1; src.header.biBitCount = 8;
    src.header.biClrUsed = 256; src.header.biClrImportant = 256;
    for (unsigned i = 0; i < 256; ++i) {
        src.colors[i].rgbRed = static_cast<BYTE>(i);
        src.colors[i].rgbGreen = static_cast<BYTE>(255-i);
        src.colors[i].rgbBlue = static_cast<BYTE>((i*7)%256);
    }
    SetStretchBltMode(dc, COLORONCOLOR);
    const int rendered = StretchDIBits(dc, 0, 0, w, h, 0, 0, w, h,
        data, reinterpret_cast<BITMAPINFO*>(&src), DIB_RGB_COLORS, SRCCOPY);
    GdiFlush();
    bool equal = rendered == static_cast<int>(h);
    const BYTE* rgb = static_cast<const BYTE*>(bits);
    for (DWORD y = 0; y < h; ++y) for (DWORD x = 0; x < w; ++x) {
        const BYTE index = value(x,y); const size_t off = (size_t(y)*w+x)*4;
        equal = equal && rgb[off] == BYTE((index*7)%256) && rgb[off+1] == BYTE(255-index) && rgb[off+2] == index;
    }
    SelectObject(dc,old); DeleteObject(bitmap); DeleteDC(dc);
    return equal;
#else
    const size_t stride = ((size_t(w)*8 + 31)/32)*4;
    for (DWORD y = 0; y < h; ++y) for (DWORD x = 0; x < w; ++x)
        if (data[y*stride+x] != value(x,y)) return false;
    return true;
#endif
}
int main() {
    unsigned cases=0, aligned=0, repacked=0, legacy_failures=0;
    for (DWORD w : {1u,2u,3u,4u,5u,6u,7u,640u,800u,802u,1024u,1280u,1366u,1920u,2560u,3440u,3840u}) {
        const DWORD h=7, dib=(w+3)&~3u;
        std::vector<DWORD> pitches = {w,w+1,dib,dib+4};
        std::sort(pitches.begin(),pitches.end()); pitches.erase(std::unique(pitches.begin(),pitches.end()),pitches.end());
        for (DWORD pitch : pitches) {
            std::vector<BYTE> src(size_t(pitch)*h,0xd7), scratch;
            for(DWORD y=0;y<h;++y) for(DWORD x=0;x<w;++x) src[size_t(y)*pitch+x]=value(x,y);
            const auto before=src;
            const BYTE* converted=indexed_dib_rows(src,w,h,pitch,scratch);
            if(!converted || before!=src || !gdi_equal(converted,w,h)) return 10;
            if(pitch==dib) { if(converted!=src.data() || !scratch.empty()) return 11; ++aligned; }
            else {
                if(converted!=scratch.data() || scratch.size()!=size_t(dib)*h) return 12;
                for(DWORD y=0;y<h;++y) for(DWORD x=w;x<dib;++x) if(scratch[size_t(y)*dib+x]) return 13;
                ++repacked;
            }
            ++cases;
        }
        if(w==802 || w==1366) {
            std::vector<BYTE> legacy(size_t(dib)*h,0xd7);
            for(DWORD y=0;y<h;++y) for(DWORD x=0;x<w;++x) legacy[size_t(y)*w+x]=value(x,y);
            if(gdi_equal(legacy.data(),w,h)) return 14;
            ++legacy_failures;
        }
    }
    std::vector<BYTE> src(12), scratch;
    for (const auto& v : std::vector<std::vector<DWORD>>{{0,2,6},{6,0,6},{6,2,5},{6,3,6},{6,2,0}})
        if(indexed_dib_rows(src,v[0],v[1],v[2],scratch)!=nullptr) return 15;
    std::cout << "{\"cases\":" << cases << ",\"zero_copy_cases\":" << aligned
        << ",\"repacked_cases\":" << repacked << ",\"legacy_failures_reproduced\":" << legacy_failures
#ifdef _WIN32
        << ",\"native_gdi_executed\":true}"
#else
        << ",\"native_gdi_executed\":false}"
#endif
        << std::endl;
    return 0;
}
'''


class DibStrideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='clash-dib-stride-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.source = SOURCE.read_text()
        start = cls.source.index('const BYTE* indexed_dib_rows(')
        end = cls.source.index('\n}\n', start)+3
        cls.helper = cls.source[start:end]
        cpp = cls.root/'fixture.cpp'; cpp.write_text(FIXTURE.replace('PRODUCTION_HELPER',cls.helper))
        if os.name == 'nt':
            vswhere=Path(os.environ['ProgramFiles(x86)'])/'Microsoft Visual Studio/Installer/vswhere.exe'
            install=subprocess.check_output([str(vswhere),'-latest','-products','*','-requires',
                'Microsoft.VisualStudio.Component.VC.Tools.x86.x64','-property','installationPath'],text=True).strip()
            vc=Path(install)/'VC/Auxiliary/Build/vcvars32.bat'
            exe=cls.root/'fixture.exe'; cmd=cls.root/'compile.cmd'
            cmd.write_text(f'@echo off\ncall "{vc}" >nul\ncl /nologo /EHsc /W4 /MT "{cpp}" /Fe"{exe}" /link gdi32.lib user32.lib\nexit /b %ERRORLEVEL%\n',encoding='ascii')
            command=['cmd.exe','/d','/c',str(cmd)]
        else:
            compiler=shutil.which('g++')
            if not compiler: raise AssertionError('A C++ compiler is required for the production-helper fixture')
            exe=cls.root/'fixture';command=[compiler,'-std=c++17','-Wall','-Wextra','-Werror',str(cpp),'-o',str(exe)]
        built=subprocess.run(command,cwd=cls.root,capture_output=True,text=True,timeout=90)
        if built.returncode: raise AssertionError(built.stdout+built.stderr)
        result=subprocess.run([str(exe)],capture_output=True,text=True,timeout=30)
        if result.returncode: raise AssertionError(f'native fixture exit {result.returncode}: {result.stdout} {result.stderr}')
        cls.receipt=json.loads(result.stdout)
        print('DIB_STRIDE '+json.dumps(cls.receipt),flush=True)

    def test_production_packing_and_real_gdi_on_windows(self):
        self.assertGreaterEqual(self.receipt['cases'],50)
        self.assertEqual(self.receipt['cases'],self.receipt['zero_copy_cases']+self.receipt['repacked_cases'])
        self.assertEqual(self.receipt['native_gdi_executed'],os.name=='nt')

    def test_both_non_dword_launcher_widths_reproduce_the_legacy_bug(self):
        self.assertEqual(self.receipt['legacy_failures_reproduced'],2)

    def test_only_presentation_uses_the_adapter_and_surface_layout_stays_intact(self):
        method=self.source.split('    void present_to_window() {',1)[1].split('\n    LONG ref_count_;',1)[0]
        self.assertIn('indexed_dib_rows(pixels_, width_, height_, pitch_, aligned_pixels)',method)
        self.assertIn('dib_pixels, reinterpret_cast<BITMAPINFO*>(&bmi)',method)
        self.assertNotIn('pixels_.data(), reinterpret_cast<BITMAPINFO*>(&bmi)',method)
        self.assertNotIn('pitch_ =',method)
        self.assertNotIn('pixels_.resize',method)
        self.assertIn('if (!g_present_enabled || !g_present_hwnd)',method)


if __name__=='__main__': unittest.main(verbosity=2)
