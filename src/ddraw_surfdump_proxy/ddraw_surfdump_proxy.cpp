#define WIN32_LEAN_AND_MEAN
#define DIRECTDRAW_VERSION 0x0300
#include <windows.h>
#include <initguid.h>
#include <ddraw.h>

#include <algorithm>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <vector>

namespace {

void log_line(const char* format, ...) {
    char module_path[MAX_PATH] = {};
    HMODULE module = GetModuleHandleA("ddraw.dll");
    if (!module || !GetModuleFileNameA(module, module_path, sizeof(module_path))) {
        return;
    }

    char* slash = strrchr(module_path, '\\');
    if (slash) {
        slash[1] = '\0';
    }
    lstrcatA(module_path, "ddraw_surfdump_proxy.log");

    char message[1024] = {};
    va_list args;
    va_start(args, format);
    _vsnprintf_s(message, sizeof(message), _TRUNCATE, format, args);
    va_end(args);

    HANDLE file = CreateFileA(
        module_path,
        FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        nullptr,
        OPEN_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        nullptr);
    if (file == INVALID_HANDLE_VALUE) {
        return;
    }
    DWORD written = 0;
    WriteFile(file, message, static_cast<DWORD>(strlen(message)), &written, nullptr);
    WriteFile(file, "\r\n", 2, &written, nullptr);
    CloseHandle(file);
}

bool proxy_output_path(const char* filename, char* output_path, DWORD output_size) {
    if (!filename || !output_path || output_size == 0) {
        return false;
    }
    output_path[0] = '\0';
    HMODULE module = GetModuleHandleA("ddraw.dll");
    if (!module || !GetModuleFileNameA(module, output_path, output_size)) {
        return false;
    }

    char* slash = strrchr(output_path, '\\');
    if (!slash) {
        return false;
    }
    slash[1] = '\0';
    lstrcatA(output_path, filename);
    return true;
}

void write_palette_file(const PALETTEENTRY* entries) {
    if (!entries) {
        return;
    }

    char path[MAX_PATH] = {};
    if (!proxy_output_path("ddraw_surfdump_palette.bin", path, sizeof(path))) {
        return;
    }

    HANDLE file = CreateFileA(
        path,
        GENERIC_WRITE,
        FILE_SHARE_READ | FILE_SHARE_WRITE,
        nullptr,
        CREATE_ALWAYS,
        FILE_ATTRIBUTE_NORMAL,
        nullptr);
    if (file == INVALID_HANDLE_VALUE) {
        return;
    }
    DWORD written = 0;
    WriteFile(file, entries, 256 * sizeof(PALETTEENTRY), &written, nullptr);
    CloseHandle(file);
}

bool is_equal_iid(REFIID left, REFIID right) {
    return IsEqualGUID(left, right) != FALSE;
}

bool should_log(LONG* counter, LONG limit = 96) {
    return InterlockedIncrement(counter) <= limit;
}

class FakePalette final : public IDirectDrawPalette {
public:
    FakePalette(DWORD caps, LPPALETTEENTRY entries) : ref_count_(1), caps_(caps) {
        if (entries) {
            memcpy(entries_, entries, sizeof(entries_));
        } else {
            memset(entries_, 0, sizeof(entries_));
        }
        write_palette_file(entries_);
        log_line("FakePalette created caps=0x%08lx", caps_);
    }

    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, LPVOID* object) override {
        if (!object) {
            return E_POINTER;
        }
        if (is_equal_iid(riid, IID_IUnknown) || is_equal_iid(riid, IID_IDirectDrawPalette)) {
            *object = static_cast<IDirectDrawPalette*>(this);
            AddRef();
            return S_OK;
        }
        *object = nullptr;
        return E_NOINTERFACE;
    }

    ULONG STDMETHODCALLTYPE AddRef() override {
        return InterlockedIncrement(&ref_count_);
    }

    ULONG STDMETHODCALLTYPE Release() override {
        LONG count = InterlockedDecrement(&ref_count_);
        if (count == 0) {
            delete this;
        }
        return count;
    }

    HRESULT STDMETHODCALLTYPE GetCaps(LPDWORD caps) override {
        if (!caps) {
            return DDERR_INVALIDPARAMS;
        }
        *caps = caps_;
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetEntries(DWORD, DWORD base, DWORD count, LPPALETTEENTRY entries) override {
        if (!entries || base >= 256 || base + count > 256) {
            return DDERR_INVALIDPARAMS;
        }
        memcpy(entries, entries_ + base, count * sizeof(PALETTEENTRY));
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Initialize(LPDIRECTDRAW, DWORD, LPPALETTEENTRY) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE SetEntries(DWORD, DWORD base, DWORD count, LPPALETTEENTRY entries) override {
        if (!entries || base >= 256 || base + count > 256) {
            return DDERR_INVALIDPARAMS;
        }
        memcpy(entries_ + base, entries, count * sizeof(PALETTEENTRY));
        write_palette_file(entries_);
        return DD_OK;
    }

private:
    ~FakePalette() {
        log_line("FakePalette destroyed");
    }

    LONG ref_count_;
    DWORD caps_;
    PALETTEENTRY entries_[256];
};

class FakeSurface final : public IDirectDrawSurface {
public:
    FakeSurface(DWORD width, DWORD height, DWORD caps)
        : ref_count_(1),
          width_(std::max<DWORD>(1, width)),
          height_(std::max<DWORD>(1, height)),
          pitch_(std::max<DWORD>(1, width)),
          caps_(caps),
          attached_(nullptr),
          palette_(nullptr),
          pixels_(pitch_ * height_, 0) {
        log_line("FakeSurface created this=%p size=%lux%lu pitch=%lu caps=0x%08lx",
                 this, width_, height_, pitch_, caps_);
    }

    void attach(FakeSurface* surface) {
        if (attached_) {
            attached_->Release();
        }
        attached_ = surface;
        if (attached_) {
            attached_->AddRef();
        }
    }

    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, LPVOID* object) override {
        if (!object) {
            return E_POINTER;
        }
        if (is_equal_iid(riid, IID_IUnknown) || is_equal_iid(riid, IID_IDirectDrawSurface)) {
            *object = static_cast<IDirectDrawSurface*>(this);
            AddRef();
            return S_OK;
        }
        *object = nullptr;
        log_line("FakeSurface QueryInterface unsupported");
        return E_NOINTERFACE;
    }

    ULONG STDMETHODCALLTYPE AddRef() override {
        return InterlockedIncrement(&ref_count_);
    }

    ULONG STDMETHODCALLTYPE Release() override {
        LONG count = InterlockedDecrement(&ref_count_);
        if (count == 0) {
            delete this;
        }
        return count;
    }

    HRESULT STDMETHODCALLTYPE AddAttachedSurface(LPDIRECTDRAWSURFACE surface) override {
        FakeSurface* fake = dynamic_cast<FakeSurface*>(surface);
        if (!fake) {
            return DDERR_INVALIDOBJECT;
        }
        attach(fake);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE AddOverlayDirtyRect(LPRECT) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Blt(LPRECT dst_rect, LPDIRECTDRAWSURFACE src_surface, LPRECT src_rect, DWORD flags, LPDDBLTFX fx) override {
        static LONG log_count = 0;
        if (should_log(&log_count)) {
            log_line("FakeSurface Blt this=%p dst=%ld,%ld,%ld,%ld src=%p src_rect=%ld,%ld,%ld,%ld flags=0x%08lx fill=0x%08lx",
                     this,
                     dst_rect ? dst_rect->left : -1,
                     dst_rect ? dst_rect->top : -1,
                     dst_rect ? dst_rect->right : -1,
                     dst_rect ? dst_rect->bottom : -1,
                     src_surface,
                     src_rect ? src_rect->left : -1,
                     src_rect ? src_rect->top : -1,
                     src_rect ? src_rect->right : -1,
                     src_rect ? src_rect->bottom : -1,
                     flags,
                     fx ? fx->dwFillColor : 0);
        }
        if ((flags & DDBLT_COLORFILL) && fx) {
            BYTE color = static_cast<BYTE>(fx->dwFillColor & 0xff);
            fill_rect(dst_rect, color);
            return DD_OK;
        }

        FakeSurface* src = dynamic_cast<FakeSurface*>(src_surface);
        if (!src) {
            return DD_OK;
        }
        copy_from(src, dst_rect, src_rect);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE BltBatch(LPDDBLTBATCH batch, DWORD count, DWORD) override {
        if (!batch) {
            return DDERR_INVALIDPARAMS;
        }
        for (DWORD i = 0; i < count; ++i) {
            Blt(batch[i].lprDest, batch[i].lpDDSSrc, batch[i].lprSrc, batch[i].dwFlags, batch[i].lpDDBltFx);
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE BltFast(DWORD x, DWORD y, LPDIRECTDRAWSURFACE src_surface, LPRECT src_rect, DWORD) override {
        static LONG log_count = 0;
        if (should_log(&log_count)) {
            log_line("FakeSurface BltFast this=%p xy=(%lu,%lu) src=%p src_rect=%ld,%ld,%ld,%ld",
                     this,
                     x,
                     y,
                     src_surface,
                     src_rect ? src_rect->left : -1,
                     src_rect ? src_rect->top : -1,
                     src_rect ? src_rect->right : -1,
                     src_rect ? src_rect->bottom : -1);
        }
        RECT dst = {static_cast<LONG>(x), static_cast<LONG>(y), static_cast<LONG>(x), static_cast<LONG>(y)};
        if (src_rect) {
            dst.right += src_rect->right - src_rect->left;
            dst.bottom += src_rect->bottom - src_rect->top;
        }
        FakeSurface* src = dynamic_cast<FakeSurface*>(src_surface);
        if (!src) {
            return DD_OK;
        }
        copy_from(src, &dst, src_rect);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE DeleteAttachedSurface(DWORD, LPDIRECTDRAWSURFACE surface) override {
        if (attached_ && surface == attached_) {
            attached_->Release();
            attached_ = nullptr;
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE EnumAttachedSurfaces(LPVOID context, LPDDENUMSURFACESCALLBACK callback) override {
        if (attached_ && callback) {
            callback(static_cast<IDirectDrawSurface*>(attached_), nullptr, context);
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE EnumOverlayZOrders(DWORD, LPVOID, LPDDENUMSURFACESCALLBACK) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Flip(LPDIRECTDRAWSURFACE, DWORD) override {
        static LONG log_count = 0;
        if (should_log(&log_count)) {
            log_line("FakeSurface Flip this=%p attached=%p", this, attached_);
        }
        if (attached_) {
            copy_from(attached_, nullptr, nullptr);
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetAttachedSurface(LPDDSCAPS, LPDIRECTDRAWSURFACE* surface) override {
        if (!surface) {
            return DDERR_INVALIDPARAMS;
        }
        if (!attached_) {
            attached_ = new FakeSurface(width_, height_, DDSCAPS_BACKBUFFER | DDSCAPS_OFFSCREENPLAIN);
        }
        attached_->AddRef();
        *surface = static_cast<IDirectDrawSurface*>(attached_);
        log_line("FakeSurface GetAttachedSurface owner=%p attached=%p", this, attached_);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetBltStatus(DWORD) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetCaps(LPDDSCAPS caps) override {
        if (!caps) {
            return DDERR_INVALIDPARAMS;
        }
        caps->dwCaps = caps_;
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetClipper(LPDIRECTDRAWCLIPPER*) override {
        return DDERR_NOCLIPPERATTACHED;
    }

    HRESULT STDMETHODCALLTYPE GetColorKey(DWORD, LPDDCOLORKEY) override {
        return DDERR_NOCOLORKEY;
    }

    HRESULT STDMETHODCALLTYPE GetDC(HDC* dc) override {
        if (!dc) {
            return DDERR_INVALIDPARAMS;
        }
        *dc = nullptr;
        return DDERR_UNSUPPORTED;
    }

    HRESULT STDMETHODCALLTYPE GetFlipStatus(DWORD) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetOverlayPosition(LPLONG x, LPLONG y) override {
        if (x) {
            *x = 0;
        }
        if (y) {
            *y = 0;
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetPalette(LPDIRECTDRAWPALETTE* palette) override {
        if (!palette) {
            return DDERR_INVALIDPARAMS;
        }
        if (palette_) {
            palette_->AddRef();
        }
        *palette = palette_;
        return palette_ ? DD_OK : DDERR_NOPALETTEATTACHED;
    }

    HRESULT STDMETHODCALLTYPE GetPixelFormat(LPDDPIXELFORMAT format) override {
        if (!format) {
            return DDERR_INVALIDPARAMS;
        }
        fill_pixel_format(format);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetSurfaceDesc(LPDDSURFACEDESC desc) override {
        if (!desc) {
            return DDERR_INVALIDPARAMS;
        }
        fill_desc(desc, false);
        static LONG log_count = 0;
        if (should_log(&log_count, 32)) {
            log_line("FakeSurface GetSurfaceDesc this=%p size=%lux%lu pitch=%lu caps=0x%08lx",
                     this, width_, height_, pitch_, caps_);
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Initialize(LPDIRECTDRAW, LPDDSURFACEDESC) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE IsLost() override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Lock(LPRECT rect, LPDDSURFACEDESC desc, DWORD, HANDLE) override {
        if (!desc) {
            return DDERR_INVALIDPARAMS;
        }
        fill_desc(desc, true);
        if (rect) {
            LONG left = std::max<LONG>(0, std::min<LONG>(rect->left, static_cast<LONG>(width_ - 1)));
            LONG top = std::max<LONG>(0, std::min<LONG>(rect->top, static_cast<LONG>(height_ - 1)));
            desc->lpSurface = pixels_.data() + top * pitch_ + left;
        }
        static LONG log_count = 0;
        if (should_log(&log_count)) {
            log_line("FakeSurface Lock this=%p rect=%ld,%ld,%ld,%ld surface=%p",
                     this,
                     rect ? rect->left : -1,
                     rect ? rect->top : -1,
                     rect ? rect->right : -1,
                     rect ? rect->bottom : -1,
                     desc->lpSurface);
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE ReleaseDC(HDC) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Restore() override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE SetClipper(LPDIRECTDRAWCLIPPER) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE SetColorKey(DWORD, LPDDCOLORKEY) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE SetOverlayPosition(LONG, LONG) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE SetPalette(LPDIRECTDRAWPALETTE palette) override {
        log_line("FakeSurface SetPalette this=%p palette=%p", this, palette);
        if (palette) {
            palette->AddRef();
        }
        if (palette_) {
            palette_->Release();
        }
        palette_ = palette;
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Unlock(LPVOID) override {
        static LONG log_count = 0;
        if (should_log(&log_count)) {
            log_line("FakeSurface Unlock this=%p", this);
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE UpdateOverlay(LPRECT, LPDIRECTDRAWSURFACE, LPRECT, DWORD, LPDDOVERLAYFX) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE UpdateOverlayDisplay(DWORD) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE UpdateOverlayZOrder(DWORD, LPDIRECTDRAWSURFACE) override {
        return DD_OK;
    }

private:
    ~FakeSurface() {
        if (attached_) {
            attached_->Release();
        }
        if (palette_) {
            palette_->Release();
        }
        log_line("FakeSurface destroyed this=%p", this);
    }

    void fill_pixel_format(LPDDPIXELFORMAT format) {
        memset(format, 0, sizeof(*format));
        format->dwSize = sizeof(*format);
        format->dwFlags = DDPF_RGB | DDPF_PALETTEINDEXED8;
        format->dwRGBBitCount = 8;
    }

    void fill_desc(LPDDSURFACEDESC desc, bool include_surface) {
        DWORD incoming_size = desc->dwSize ? desc->dwSize : sizeof(*desc);
        memset(desc, 0, sizeof(*desc));
        desc->dwSize = incoming_size;
        desc->dwFlags = DDSD_WIDTH | DDSD_HEIGHT | DDSD_PITCH | DDSD_CAPS | DDSD_PIXELFORMAT;
        if (include_surface) {
            desc->dwFlags |= DDSD_LPSURFACE;
            desc->lpSurface = pixels_.data();
        }
        desc->dwWidth = width_;
        desc->dwHeight = height_;
        desc->lPitch = static_cast<LONG>(pitch_);
        desc->ddsCaps.dwCaps = caps_;
        fill_pixel_format(&desc->ddpfPixelFormat);
    }

    void fill_rect(LPRECT rect, BYTE color) {
        RECT r = normalized_rect(rect, width_, height_);
        for (LONG y = r.top; y < r.bottom; ++y) {
            memset(pixels_.data() + y * pitch_ + r.left, color, r.right - r.left);
        }
    }

    RECT normalized_rect(LPRECT rect, DWORD width, DWORD height) {
        RECT r = {0, 0, static_cast<LONG>(width), static_cast<LONG>(height)};
        if (rect) {
            r = *rect;
        }
        r.left = std::max<LONG>(0, std::min<LONG>(r.left, static_cast<LONG>(width)));
        r.top = std::max<LONG>(0, std::min<LONG>(r.top, static_cast<LONG>(height)));
        r.right = std::max<LONG>(r.left, std::min<LONG>(r.right, static_cast<LONG>(width)));
        r.bottom = std::max<LONG>(r.top, std::min<LONG>(r.bottom, static_cast<LONG>(height)));
        return r;
    }

    void copy_from(FakeSurface* src, LPRECT dst_rect, LPRECT src_rect) {
        if (!src) {
            return;
        }
        RECT src_r = normalized_rect(src_rect, src->width_, src->height_);
        RECT dst_r = normalized_rect(dst_rect, width_, height_);
        DWORD copy_width = static_cast<DWORD>(std::min<LONG>(src_r.right - src_r.left, dst_r.right - dst_r.left));
        DWORD copy_height = static_cast<DWORD>(std::min<LONG>(src_r.bottom - src_r.top, dst_r.bottom - dst_r.top));
        if (copy_width == 0 || copy_height == 0) {
            return;
        }
        for (DWORD y = 0; y < copy_height; ++y) {
            BYTE* dst = pixels_.data() + (dst_r.top + y) * pitch_ + dst_r.left;
            BYTE* src_line = src->pixels_.data() + (src_r.top + y) * src->pitch_ + src_r.left;
            memmove(dst, src_line, copy_width);
        }
    }

    LONG ref_count_;
    DWORD width_;
    DWORD height_;
    DWORD pitch_;
    DWORD caps_;
    FakeSurface* attached_;
    LPDIRECTDRAWPALETTE palette_;
    std::vector<BYTE> pixels_;
};

class FakeDirectDraw final : public IDirectDraw2 {
public:
    FakeDirectDraw() : ref_count_(1), width_(640), height_(480), bpp_(8) {
        log_line("FakeDirectDraw created this=%p", this);
    }

    HRESULT STDMETHODCALLTYPE QueryInterface(REFIID riid, LPVOID* object) override {
        if (!object) {
            return E_POINTER;
        }
        if (is_equal_iid(riid, IID_IUnknown) ||
            is_equal_iid(riid, IID_IDirectDraw) ||
            is_equal_iid(riid, IID_IDirectDraw2)) {
            *object = static_cast<IDirectDraw2*>(this);
            AddRef();
            log_line("FakeDirectDraw QueryInterface supported");
            return S_OK;
        }
        *object = nullptr;
        log_line("FakeDirectDraw QueryInterface unsupported");
        return E_NOINTERFACE;
    }

    ULONG STDMETHODCALLTYPE AddRef() override {
        return InterlockedIncrement(&ref_count_);
    }

    ULONG STDMETHODCALLTYPE Release() override {
        LONG count = InterlockedDecrement(&ref_count_);
        if (count == 0) {
            delete this;
        }
        return count;
    }

    HRESULT STDMETHODCALLTYPE Compact() override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE CreateClipper(DWORD, LPDIRECTDRAWCLIPPER*, IUnknown*) override {
        return DDERR_UNSUPPORTED;
    }

    HRESULT STDMETHODCALLTYPE CreatePalette(DWORD caps, LPPALETTEENTRY entries, LPDIRECTDRAWPALETTE* palette, IUnknown*) override {
        if (!palette) {
            return DDERR_INVALIDPARAMS;
        }
        *palette = new FakePalette(caps, entries);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE CreateSurface(LPDDSURFACEDESC desc, LPDIRECTDRAWSURFACE* surface, IUnknown*) override {
        if (!desc || !surface) {
            return DDERR_INVALIDPARAMS;
        }
        DWORD caps = desc->ddsCaps.dwCaps;
        DWORD width = (desc->dwFlags & DDSD_WIDTH) ? desc->dwWidth : width_;
        DWORD height = (desc->dwFlags & DDSD_HEIGHT) ? desc->dwHeight : height_;
        if (caps & DDSCAPS_PRIMARYSURFACE) {
            width = width_;
            height = height_;
        }
        FakeSurface* fake = new FakeSurface(width, height, caps);
        if ((caps & DDSCAPS_FLIP) || (desc->dwFlags & DDSD_BACKBUFFERCOUNT) || desc->dwBackBufferCount > 0) {
            fake->attach(new FakeSurface(width, height, DDSCAPS_BACKBUFFER | DDSCAPS_OFFSCREENPLAIN));
        }
        *surface = static_cast<IDirectDrawSurface*>(fake);
        log_line("FakeDirectDraw CreateSurface desc_flags=0x%08lx caps=0x%08lx size=%lux%lu backbuffers=%lu surface=%p",
                 desc->dwFlags, caps, width, height, desc->dwBackBufferCount, fake);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE DuplicateSurface(LPDIRECTDRAWSURFACE, LPDIRECTDRAWSURFACE*) override {
        return DDERR_UNSUPPORTED;
    }

    HRESULT STDMETHODCALLTYPE EnumDisplayModes(DWORD, LPDDSURFACEDESC, LPVOID, LPDDENUMMODESCALLBACK) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE EnumSurfaces(DWORD, LPDDSURFACEDESC, LPVOID, LPDDENUMSURFACESCALLBACK) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE FlipToGDISurface() override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetCaps(LPDDCAPS driver_caps, LPDDCAPS hel_caps) override {
        if (driver_caps) {
            memset(driver_caps, 0, driver_caps->dwSize ? driver_caps->dwSize : sizeof(DDCAPS));
            driver_caps->dwSize = sizeof(DDCAPS);
        }
        if (hel_caps) {
            memset(hel_caps, 0, hel_caps->dwSize ? hel_caps->dwSize : sizeof(DDCAPS));
            hel_caps->dwSize = sizeof(DDCAPS);
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetDisplayMode(LPDDSURFACEDESC desc) override {
        if (!desc) {
            return DDERR_INVALIDPARAMS;
        }
        DWORD incoming_size = desc->dwSize ? desc->dwSize : sizeof(*desc);
        memset(desc, 0, sizeof(*desc));
        desc->dwSize = incoming_size;
        desc->dwFlags = DDSD_WIDTH | DDSD_HEIGHT | DDSD_PITCH | DDSD_PIXELFORMAT;
        desc->dwWidth = width_;
        desc->dwHeight = height_;
        desc->lPitch = static_cast<LONG>(width_);
        desc->ddpfPixelFormat.dwSize = sizeof(desc->ddpfPixelFormat);
        desc->ddpfPixelFormat.dwFlags = DDPF_RGB | DDPF_PALETTEINDEXED8;
        desc->ddpfPixelFormat.dwRGBBitCount = bpp_;
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetFourCCCodes(LPDWORD count, LPDWORD codes) override {
        if (count) {
            *count = 0;
        }
        if (codes) {
            *codes = 0;
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetGDISurface(LPDIRECTDRAWSURFACE*) override {
        return DDERR_NOTFOUND;
    }

    HRESULT STDMETHODCALLTYPE GetMonitorFrequency(LPDWORD frequency) override {
        if (frequency) {
            *frequency = 60;
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetScanLine(LPDWORD scanline) override {
        if (scanline) {
            *scanline = 0;
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetVerticalBlankStatus(LPBOOL blank) override {
        if (blank) {
            *blank = FALSE;
        }
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE Initialize(GUID*) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE RestoreDisplayMode() override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE SetCooperativeLevel(HWND hwnd, DWORD flags) override {
        log_line("FakeDirectDraw SetCooperativeLevel hwnd=%p flags=0x%08lx", hwnd, flags);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE SetDisplayMode(DWORD width, DWORD height, DWORD bpp, DWORD refresh, DWORD flags) override {
        width_ = std::max<DWORD>(1, width);
        height_ = std::max<DWORD>(1, height);
        bpp_ = bpp ? bpp : 8;
        log_line("FakeDirectDraw SetDisplayMode %lux%lu bpp=%lu refresh=%lu flags=0x%08lx",
                 width_, height_, bpp_, refresh, flags);
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE WaitForVerticalBlank(DWORD, HANDLE) override {
        return DD_OK;
    }

    HRESULT STDMETHODCALLTYPE GetAvailableVidMem(LPDDSCAPS, LPDWORD total, LPDWORD free_mem) override {
        if (total) {
            *total = 64 * 1024 * 1024;
        }
        if (free_mem) {
            *free_mem = 64 * 1024 * 1024;
        }
        return DD_OK;
    }

private:
    ~FakeDirectDraw() {
        log_line("FakeDirectDraw destroyed this=%p", this);
    }

    LONG ref_count_;
    DWORD width_;
    DWORD height_;
    DWORD bpp_;
};

}  // namespace

HRESULT WINAPI DirectDrawCreate(GUID FAR* guid, LPDIRECTDRAW FAR* dd, IUnknown FAR*) {
    log_line("DirectDrawCreate guid=%p out=%p", guid, dd);
    if (!dd) {
        return DDERR_INVALIDPARAMS;
    }
    *dd = reinterpret_cast<LPDIRECTDRAW>(new FakeDirectDraw());
    return DD_OK;
}

HRESULT WINAPI DirectDrawCreateEx(GUID FAR* guid, LPVOID* dd, REFIID iid, IUnknown FAR*) {
    log_line("DirectDrawCreateEx guid=%p out=%p", guid, dd);
    if (!dd) {
        return DDERR_INVALIDPARAMS;
    }
    FakeDirectDraw* fake = new FakeDirectDraw();
    HRESULT hr = fake->QueryInterface(iid, dd);
    fake->Release();
    return hr;
}

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(instance);
        log_line("ddraw_surfdump_proxy loaded");
    } else if (reason == DLL_PROCESS_DETACH) {
        log_line("ddraw_surfdump_proxy unloaded");
    }
    return TRUE;
}
