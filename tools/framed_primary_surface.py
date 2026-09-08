"""Pure validation of a paused, cached proxy-primary snapshot.

This module reads no files/processes and calls no COM, debugger or Win32 API.
It checks supplied bytes and explicit observation bindings. The future host
must authenticate those reads, the complete source-bound trace and module
identity; an internally consistent packet is not runtime or visual proof.

Native473840 caches a full IDirectDrawSurface::Lock description at B+38;
4738B0 and the reviewed proxy Unlock do not invalidate its pixel allocation.
The primary is P=51D4C0 -> B=[P+BC] -> COM surface=[B+A4], never [P+4]/E0.
FakePalette has the reviewed MSVC x86 single-interface layout (vptr, LONG,
DWORD, 256 PALETTEENTRYs); no std::vector layout is inferred here.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import struct

PRIMARY = 0x51D4C0
PRIMARY_VTABLE = 0x50EEC4
PRIMARY_BYTES = 0xDC
BACKEND_BYTES = 0xB0
SURFACE_VTABLE_BYTES = 36 * 4
PALETTE_VTABLE_BYTES = 7 * 4
PALETTE_ENTRIES_OFFSET = 12
PALETTE_BYTES = PALETTE_ENTRIES_OFFSET + 1024
# Exact reviewed build RTTI identifies these as FakeSurface and FakePalette.
SURFACE_VTABLE_RVA = 0x1939C
PALETTE_VTABLE_RVA = 0x19340
LOCK_RETURN = 0x473872
LOCK_CALL = 0x47386F
U32 = 1 << 32
DDSD_REQUIRED = 0x100F | 0x800  # CAPS, HEIGHT, WIDTH, PITCH, PIXELFORMAT, LPSURFACE
DDPF_REQUIRED = 0x60  # RGB | PALETTEINDEXED8
PRIMARY_CAPS = 0x200
SUPPORTED_PROXY_SOURCE_SHA256 = "407d41d0d548e6217c6041181efb6466efa90f447110c5b8857bf92714ecb8eb"
SUPPORTED_PROXY_SHA256 = "b173a9dd4ce772eb5b56f341acdf4b329ed4ffdd638c1fce5cc37dd332804b70"
LIMITS = [
    "Caller must authenticate actual owned-process reads, paused thread, candidate and complete canonical trace.",
    "Lock and palette observations are required inputs; this helper does not authenticate their provenance.",
    "Only the pinned reviewed proxy build is supported; caller must authenticate that exact module in the owned process.",
    "Cached pointer is valid only for this pinned proxy's fixed allocation lifetime, not arbitrary DirectDraw wrappers.",
    "Primary pixels measure the captured route boundary; no nonblack, complete UI, input, cleanup or promotion verdict is inferred.",
]


class PrimarySnapshotError(ValueError):
    pass


def _need(condition, message):
    if not condition:
        raise PrimarySnapshotError(message)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _digest(value, label):
    _need(isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value), label + " SHA-256 is invalid")
    return value


def _range(address, size, label):
    _need(type(address) is int and type(size) is int and address > 0 and size > 0
          and address + size <= U32, label + " range is zero, invalid or overflowing")


def _u32(data, offset):
    return struct.unpack_from('<I', data, offset)[0]


@dataclass(frozen=True)
class Read:
    address: int
    data: bytes


@dataclass(frozen=True)
class Snapshot:
    primary: Read
    backend: Read
    surface: Read
    surface_vtable: Read
    palette: Read
    palette_vtable: Read


@dataclass(frozen=True)
class Region:
    address: int
    size: int
    state: int  # Recorded VirtualQueryEx MEM_COMMIT=0x1000.
    protect: int


def primary_read_plan(width, height):
    """Return dependencies, not addresses guessed from another process/run."""
    _dimensions(width, height)
    return dict(schema='clash95_cached_primary_read_plan_v1', read_only=True,
        reads=[dict(name='primary', address=PRIMARY, bytes=PRIMARY_BYTES),
               dict(name='backend', address_from='u32(primary+0xBC)', bytes=BACKEND_BYTES),
               dict(name='surface', address_from='u32(backend+0xA4)', bytes=4),
               dict(name='surface_vtable', address_from='u32(surface)', bytes=SURFACE_VTABLE_BYTES),
               dict(name='palette', address_from='authenticated current SetPalette observation', bytes=PALETTE_BYTES),
               dict(name='palette_vtable', address_from='u32(palette)', bytes=PALETTE_VTABLE_BYTES),
               dict(name='pixels', address_from='u32(backend+0x5C)', bytes=width*height)],
        repeat_after_pixels=['primary','backend','surface','surface_vtable','palette','palette_vtable'],
        requirements=['Exact source-bound successful full-surface Lock at native473872 for the current backend/COM object.',
                      'Current attached palette identity and complete palette entries, not only last global palette-file contents.',
                      'Exact readable committed ranges and full ReadProcessMemory byte counts; all headers/palette stable across capture.',
                      'Primary/candidate/proxy/process/thread identity belongs to the same paused capture.'],
        supported_proxy_sha256=SUPPORTED_PROXY_SHA256,
        supported_proxy_source_sha256=SUPPORTED_PROXY_SOURCE_SHA256,
        proxy_vtable_rvas=dict(surface=SURFACE_VTABLE_RVA,palette=PALETTE_VTABLE_RVA),
        lock_abi=dict(call_eip=LOCK_CALL, return_eip=LOCK_RETURN,
                      stack_argument_bytes=20, arguments=['COM surface','NULL rect','backend+0x38','1','NULL event']),
        runtime_ready=False, limits=list(LIMITS))


def _dimensions(width, height):
    _need(type(width) is int and type(height) is int and 640 <= width <= 8192
          and 480 <= height <= 8192 and width % 2 == height % 2 == 0,
          'unsupported explicit physical dimensions')


class _Proxy:
    """Small PE32 DLL reader: canonical vtable bytes with loader HIGHLOW fixups."""
    def __init__(self, image, expected_sha256, base):
        _need(isinstance(image, bytes), 'proxy image must be immutable bytes')
        _need(_sha(image) == _digest(expected_sha256, 'proxy'), 'proxy image hash mismatch')
        _need(len(image) >= 0x100 and image[:2] == b'MZ', 'invalid proxy DOS header')
        off = _u32(image,0x3C)
        _need(off + 248 <= len(image) and image[off:off+4] == b'PE\0\0', 'invalid proxy PE header')
        machine,count = struct.unpack_from('<HH',image,off+4)
        optional_size,flags = struct.unpack_from('<HH',image,off+20)
        opt=off+24
        _need(machine == 0x14C and 1 <= count <= 96 and optional_size == 224
              and flags & 0x2000 and struct.unpack_from('<H',image,opt)[0] == 0x10B,
              'proxy must be a PE32 x86 DLL')
        self.image=image; self.base=base; self.preferred=_u32(image,opt+28)
        self.size=_u32(image,opt+56); _range(base,self.size,'proxy module')
        self.sections=[]
        _need(opt+224+count*40 <= len(image), 'truncated proxy sections')
        for index in range(count):
            p=opt+224+index*40
            vs,rva,rs,ro=struct.unpack_from('<4I',image,p+8); ch=_u32(image,p+36)
            length=max(vs,rs)
            _need(length > 0 and rva+length <= self.size and (rs == 0 or ro+rs <= len(image)),
                  'invalid proxy section extent')
            _need(all(rva+length <= x[0] or x[0]+x[1] <= rva for x in self.sections), 'overlapping proxy sections')
            self.sections.append((rva,length,rs,ro,ch))
        self.fixups=[]
        reloc,size=struct.unpack_from('<II',image,opt+96+5*8)
        if size:
            table=self.raw(reloc,size); pos=0
            while pos<len(table):
                _need(pos+8<=len(table),'truncated proxy relocation block')
                page,n=struct.unpack_from('<II',table,pos)
                _need(n>=8 and n%2==0 and pos+n<=len(table),'invalid proxy relocation block')
                for q in range(pos+8,pos+n,2):
                    tag=struct.unpack_from('<H',table,q)[0];kind=tag>>12;address=page+(tag&4095)
                    _need(kind in (0,3),'unsupported proxy relocation kind')
                    if kind:
                        _need(address+4<=self.size and address not in self.fixups,'invalid duplicate proxy relocation')
                        self.fixups.append(address)
                pos+=n
        _need(base==self.preferred or self.fixups,'rebased proxy has no fixups')

    def section(self,rva,size):
        found=[x for x in self.sections if x[0]<=rva and rva+size<=x[0]+x[1]]
        _need(len(found)==1,'proxy address is outside one mapped section')
        return found[0]

    def raw(self,rva,size):
        s=self.section(rva,size)
        _need(s[3]>0 and rva+size<=s[0]+s[2],'proxy bytes are not file-backed')
        pos=s[3]+rva-s[0]
        return self.image[pos:pos+size]

    def vtable(self,read):
        rva=read.address-self.base; s=self.section(rva,len(read.data))
        _need(s[4]&0x40000000 and not s[4]&0x80000000, 'proxy vtable is not immutable readable module data')
        expected=bytearray(self.raw(rva,len(read.data)))
        for site in self.fixups:
            if site+4<=rva or site>=rva+len(expected):continue
            _need(rva<=site and site+4<=rva+len(expected),'partial proxy vtable relocation')
            i=site-rva;struct.pack_into('<I',expected,i,(_u32(expected,i)+self.base-self.preferred)&0xFFFFFFFF)
        _need(bytes(expected)==read.data,'loaded proxy vtable differs from pinned DLL')
        for i in range(0,len(read.data),4):
            address=_u32(read.data,i)
            section=self.section(address-self.base,1)
            _need(section[4]&0x20000000,'proxy COM method is outside executable module code')


def _read(value,address,size,label,regions):
    _need(isinstance(value,Read) and isinstance(value.data,bytes),label+' is not an immutable read')
    _range(address,size,label)
    _need(value.address==address and len(value.data)==size,label+' address or exact byte count differs')
    cursor=address
    for region in sorted(regions,key=lambda r:r.address):
        _range(region.address,region.size,'memory region')
        if region.address <= cursor < region.address+region.size:
            _need(region.state==0x1000 and region.protect in (2,4,8,0x20,0x40,0x80),label+' is not committed/readable or has guard protection')
            cursor=min(address+size,region.address+region.size)
            if cursor==address+size:break
    _need(cursor==address+size,label+' is not completely covered by readable regions')


def validate_snapshot(before,after,pixels,*,width,height,proxy_image,expected_proxy_sha256,
                      proxy_base,regions,identity,lock_observation,palette_observation):
    """Raise on invalid input; return only internal snapshot consistency.

    `identity` and observations must come from a separately authenticated host
    trace, never approval records or manually authored success flags. Their
    field equality is checked here; their authenticity is deliberately not.
    """
    _dimensions(width,height)
    _need(isinstance(before,Snapshot) and isinstance(after,Snapshot),'both snapshots required')
    for label in Snapshot.__dataclass_fields__:
        for snapshot in (before,after):
            value=getattr(snapshot,label)
            _need(isinstance(value,Read) and isinstance(value.data,bytes),label+' is not an immutable read')
            _range(value.address,len(value.data),label)
    _need(before==after,'primary/header/palette bytes changed across capture')
    _need(isinstance(regions,(tuple,list)) and all(isinstance(r,Region) for r in regions),'readable-region observations required')
    for region in regions:
        _range(region.address,region.size,'memory region')
        _need(type(region.state) is int and type(region.protect) is int,'invalid memory-region flags')
    ordered=sorted(regions,key=lambda r:r.address)
    _need(all(a.address+a.size<=b.address for a,b in zip(ordered,ordered[1:])),'overlapping memory-region claims')
    _need(expected_proxy_sha256==SUPPORTED_PROXY_SHA256,'unsupported proxy build/private palette ABI')
    proxy=_Proxy(proxy_image,expected_proxy_sha256,proxy_base)
    _read(before.primary,PRIMARY,PRIMARY_BYTES,'primary',regions)
    p=before.primary.data
    _need(struct.unpack_from('<HH',p)==(width,height) and _u32(p,0xB8)==PRIMARY_VTABLE
          and _u32(p,0xD4)==8,'primary dimensions/vtable/depth differ')
    backend=_u32(p,0xBC);_read(before.backend,backend,BACKEND_BYTES,'backend',regions)
    b=before.backend.data;surface=_u32(b,0xA4)
    _read(before.surface,surface,4,'COM surface',regions)
    _read(before.surface_vtable,_u32(before.surface.data,0),SURFACE_VTABLE_BYTES,'surface vtable',regions)
    _need(before.surface_vtable.address==proxy_base+SURFACE_VTABLE_RVA,'COM object is not the pinned FakeSurface interface')
    proxy.vtable(before.surface_vtable)
    _need(_u32(b,0x38)==108 and _u32(b,0x3C)==DDSD_REQUIRED,'cached full Lock descriptor missing or unsupported')
    _need((_u32(b,0x40),_u32(b,0x44),_u32(b,0x48))==(height,width,width),'cached dimensions/pitch differ')
    _need((_u32(b,0x80),_u32(b,0x84),_u32(b,0x88),_u32(b,0x8C))==(32,DDPF_REQUIRED,0,8)
          and b[0x90:0xA0]==bytes(16),'cached pixel format is not the exact indexed8 proxy format')
    _need(_u32(b,0xA0)==PRIMARY_CAPS,'cached descriptor is not the simple proxy primary surface')
    pointer=_u32(b,0x5C);_read(pixels,pointer,width*height,'pixels',regions)
    reads=(before.primary,before.backend,before.surface,before.palette)
    for index,read in enumerate(reads):
        _need(pointer+len(pixels.data)<=read.address or read.address+len(read.data)<=pointer,'pixels overlap identity/header/palette memory')
        for other in reads[index+1:]:
            _need(read.address+len(read.data)<=other.address or other.address+len(other.data)<=read.address,
                  'identity/header/palette memory aliases another object')
        _need(read.address+len(read.data)<=proxy.base or proxy.base+proxy.size<=read.address,
              'mutable object aliases proxy module memory')
    _need(pointer+len(pixels.data)<=proxy.base or proxy.base+proxy.size<=pointer,'pixels overlap proxy module memory')
    _need(isinstance(identity,dict) and isinstance(lock_observation,dict) and isinstance(palette_observation,dict),'trace identity/lock/current palette observations required')
    keys=('run_id','process_id','process_start','candidate_sha256','proxy_sha256','thread_id','trace_sha256','capture_boundary')
    _need(all(k in identity for k in keys),'incomplete capture identity')
    _need(all(type(identity.get(k)) is int and identity[k]>0 for k in
              ('ready_line','last_primary_lock_line','current_palette_line')),'invalid capture trace line identity')
    for key in ('candidate_sha256','proxy_sha256','trace_sha256'):_digest(identity[key],key)
    _need(identity['proxy_sha256']==expected_proxy_sha256,'capture/proxy identity differs')
    _need(all(isinstance(identity[k],str) and identity[k] for k in ('run_id','process_start','capture_boundary'))
          and all(type(identity[k]) is int and 0<identity[k]<U32 for k in ('process_id','thread_id')),'invalid run/process/thread identity')
    for observation,label in ((lock_observation,'Lock'),(palette_observation,'palette')):
        _need(all(observation.get(k)==identity[k] for k in keys),label+' observation belongs to another capture')
        _need(type(observation.get('line')) is int and 0<observation['line']<=identity.get('ready_line',0),label+' observation is stale or after capture boundary')
    lock=lock_observation
    _need(lock.get('schema')=='clash95_full_primary_lock_v1' and lock.get('return_eip')==LOCK_RETURN
          and type(lock.get('hresult')) is int and lock['hresult']==0 and lock.get('rect_is_null') is True,
          'successful source-bound full-surface Lock observation required')
    _need(lock.get('call_eip')==LOCK_CALL and type(lock.get('call_line')) is int
          and 0<lock['call_line']<lock['line']
          and type(lock.get('call_esp')) is int and 0<lock['call_esp']<U32-20
          and type(lock.get('return_esp')) is int and lock['return_esp']==lock['call_esp']+20
          and type(lock.get('flags')) is int and lock['flags']==1
          and type(lock.get('event_handle')) is int and lock['event_handle']==0,
          'full Lock call/return native stdcall pairing differs')
    _need(lock.get('line')==identity.get('last_primary_lock_line') and
          all(lock.get(k)==v for k,v in dict(backend=backend,surface=surface,descriptor=backend+0x38,
              pixels=pointer,width=width,height=height,pitch=width,descriptor_sha256=_sha(b[0x38:0xA4])).items()),
          'last full Lock does not bind this current cached descriptor')
    pal=palette_observation
    _need(pal.get('schema')=='clash95_current_primary_palette_v1' and pal.get('surface')==surface
          and pal.get('line')==identity.get('current_palette_line'),'current attached primary palette observation required')
    _read(before.palette,pal.get('palette'),PALETTE_BYTES,'current palette',regions)
    _need(_u32(before.palette.data,4)>0,'palette has no live reference')
    _read(before.palette_vtable,_u32(before.palette.data,0),PALETTE_VTABLE_BYTES,'palette vtable',regions)
    _need(before.palette_vtable.address==proxy_base+PALETTE_VTABLE_RVA,'palette is not the pinned FakePalette interface')
    proxy.vtable(before.palette_vtable)
    palette_bytes=before.palette.data[PALETTE_ENTRIES_OFFSET:]
    _need(pal.get('entries_address')==before.palette.address+PALETTE_ENTRIES_OFFSET
          and pal.get('entries_sha256')==_sha(palette_bytes) and pal.get('entry_count')==256,
          'current palette entries differ from bound observation')
    return dict(schema='clash95_cached_primary_snapshot_v1',cached_primary_snapshot_valid=True,
        source_authenticated=False,runtime_passed=False,visual_passed=False,manual_input_proof=False,promotion_ready=False,
        primary=PRIMARY,backend=backend,surface=surface,pixels=pointer,width=width,height=height,pitch=width,
        bytes=len(pixels.data),pixel_sha256=_sha(pixels.data),palette_sha256=_sha(palette_bytes),
        descriptor_sha256=_sha(b[0x38:0xA4]),proxy_sha256=expected_proxy_sha256,identity=dict(identity),
        proxy_source_sha256=SUPPORTED_PROXY_SOURCE_SHA256,
        limits=list(LIMITS))
