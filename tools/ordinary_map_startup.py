"""Explicit startup-only slot-zero controls for the owned ordinary-map driver.

This transforms authenticated harness source and launches nothing. The audited
legacy startup recipe bypasses acquisition/sleeps and menu predicates only
until the real slot-zero loader returns and calls PlayGame. Every owned startup
breakpoint is removed there before normal human-turn/selection observations.
No world renderer, army selection routine or gameplay predicate is invoked or
forced. Source compilation is not runtime, manual-input or promotion proof.
"""
from __future__ import annotations

import hashlib

ORIGINAL_SHA256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
# Exact original file-backed bytes, freshly checked on 2026-09-26. Globals are
# runtime input fields, not bytes borrowed from file offsets in the BSS.
NATIVE_ANCHORS = {
    0x44789A: '2eff15c0a54e00',
    0x46E4D0: '2eff15c0a54e00',
    0x46E6DF: '2eff15c0a54e00',
    0x46FD01: '2eff15c0a54e00',
    0x47BFD0: '53515283ec6089c383b8340100000075',
    0x47BD66: '8b4608508b10ff521c85c075b8',
    0x47BDAE: '8b4604508b10ff521c85c00f856cffffff',
    0x419B80: '53515256575589c3a1fc4c54008a0d2c515400',
    0x419C51: '85c07444837b2000743e89d8',
    0x447780: '5152e84927fdffba05000000b90100000089157c3d5400890d783d54005a59c3',
    0x448A68: '85c00f847e000000a1fc4c54008a0d2c',
    0x448AE3: '85c0740731c0e822160000',
    0x444490: '515256575583ec6489c789e2e81fffff',
    0x448B74: 'e8e72afcff',
    0x40B660: '5351525631d2685cc94e008915e85254',
}
# At each CALL or native function entry below, only the reviewed bootstrap
# substitutions are admitted. Load and PlayGame caller words remain native.
SITE_NAMES = {
    0x44789A: 'startup-sleep', 0x46E4D0: 'avi-sleep-a',
    0x46E6DF: 'avi-sleep-b', 0x46FD01: 'avi-sleep-c',
    0x47BFD0: 'startup-input-poll', 0x47BD66: 'mouse-acquire',
    0x47BDAE: 'keyboard-acquire', 0x419B80: 'widget-coordinate',
    0x419C51: 'main-click', 0x447780: 'main-load-callback',
    0x448A68: 'slot-zero-select', 0x448AE3: 'slot-zero-accept',
    0x444490: 'native-slot-load', 0x448B74: 'native-slot-load-return',
    0x40B660: 'native-playgame-entry',
}
SNAPSHOT_ANCHOR = 'static void snapshot(Session &s,const std::string &out,int sample,bool proxy) {\n'
LOADED_ANCHOR = ('        printf("REAL_LOADED pid=%lu base=%08lx entry=%08lx executable_sections_match=1\\n",'
                 'pid,base,entry); fflush(stdout);\n')
EVENT_ANCHOR = '                if (ip==entry && !entered) { entered=true; printf("REAL_EXE_ENTRY observed=1\\n"); }\n'


def verify_original_anchors(data):
    """Read-only source audit; an unknown executable cannot supply anchors."""
    if type(data) is not bytes or hashlib.sha256(data).hexdigest() != ORIGINAL_SHA256:
        raise ValueError('Unknown original executable')
    from src.patcher.partial_tile_clip import file_offset
    for address, expected in NATIVE_ANCHORS.items():
        raw=bytes.fromhex(expected)
        offset=file_offset(data,address,len(raw))
        if data[offset:offset+len(raw)] != raw:
            raise ValueError(f'Original startup anchor differs at {address:08x}')
    return dict(NATIVE_ANCHORS)


CONTROLLER_SOURCE = r'''
// Disclosed bootstrap-only controls; retired before all ordinary-map evidence.
struct StartupSite {
    ULONG address,id=DEBUG_ANY_ID,hits=0;
    const char *name,*hex;
    IDebugBreakpoint *bp=nullptr;
};
struct StartupController {
    Session &s;
    std::vector<StartupSite> sites;
    bool retired=false,load_seen=false,load_returned=false,main_requested=false;
    ULONG engine_process=0,engine_primary=0,load_sp=0,loaded_gd=0,total_hits=0,main_widget=0;
    ULONGLONG created=0,deadline=0;
    static constexpr ULONG raw_x=0x544cfc,raw_y=0x544d00,buttons=0x544d04;
    static constexpr ULONG primary_button=0x5451c0,shift_address=0x54512c;
    static constexpr ULONG menu_choice=0x543d7c,menu_exit=0x543d78;
    static constexpr ULONG selected_slot=0x5441e0,load_accept=0x544190;
    static constexpr ULONG main_x=__MAIN_X__,main_y=__MAIN_Y__;

    static ULONGLONG creation(Session &owner) {
        FILETIME a={},b={},c={},d={};
        if (!GetProcessTimes(owner.process,&a,&b,&c,&d)) throw std::runtime_error("startup process creation unavailable");
        return (static_cast<ULONGLONG>(a.dwHighDateTime)<<32)|a.dwLowDateTime;
    }
    void owner() const {
        if (!s.process || !s.primary_thread || WaitForSingleObject(s.process,0)!=WAIT_TIMEOUT ||
            WaitForSingleObject(s.primary_thread,0)!=WAIT_TIMEOUT || GetProcessId(s.process)!=s.owned_pid ||
            GetThreadId(s.primary_thread)!=s.primary_tid || GetProcessIdOfThread(s.primary_thread)!=s.owned_pid ||
            creation(s)!=created) throw std::runtime_error("startup retained identity differs");
    }
    static std::vector<unsigned char> decode(const char *hex) {
        std::vector<unsigned char> result;
        auto digit=[](char c)->unsigned { if(c>='0'&&c<='9')return c-'0'; if(c>='a'&&c<='f')return c-'a'+10; throw std::runtime_error("startup hex rejected"); };
        size_t length=strlen(hex); if(!length || length%2)throw std::runtime_error("startup anchor length rejected");
        for(size_t i=0;i<length;i+=2)result.push_back(static_cast<unsigned char>(digit(hex[i])*16+digit(hex[i+1])));
        return result;
    }
    static std::vector<unsigned char> disk_read(const std::vector<unsigned char> &disk,ULONG va,size_t size) {
        if(disk.size()<64)throw std::runtime_error("startup disk header missing");
        ULONG pe=0;memcpy(&pe,disk.data()+60,4);
        if(pe>disk.size() || sizeof(IMAGE_NT_HEADERS32)>disk.size()-pe)throw std::runtime_error("startup PE header bounds");
        auto *nt=reinterpret_cast<const IMAGE_NT_HEADERS32 *>(disk.data()+pe);
        size_t first=static_cast<size_t>(pe)+24+nt->FileHeader.SizeOfOptionalHeader;
        if(nt->Signature!=IMAGE_NT_SIGNATURE || nt->FileHeader.Machine!=IMAGE_FILE_MACHINE_I386 ||
            nt->OptionalHeader.Magic!=IMAGE_NT_OPTIONAL_HDR32_MAGIC || nt->OptionalHeader.ImageBase!=0x400000 ||
            first>disk.size() || nt->FileHeader.NumberOfSections>(disk.size()-first)/sizeof(IMAGE_SECTION_HEADER))
            throw std::runtime_error("startup PE section bounds or mapping");
        ULONG rva=va-0x400000;
        auto *sections=reinterpret_cast<const IMAGE_SECTION_HEADER *>(disk.data()+first);
        for(ULONG i=0;i<nt->FileHeader.NumberOfSections;++i) {
            const auto &sec=sections[i];
            if(rva<sec.VirtualAddress)continue;
            ULONGLONG delta=static_cast<ULONGLONG>(rva)-sec.VirtualAddress;
            ULONGLONG offset=static_cast<ULONGLONG>(sec.PointerToRawData)+delta;
            if(delta+size<=sec.SizeOfRawData && offset+size<=disk.size())
                return std::vector<unsigned char>(disk.begin()+static_cast<size_t>(offset),disk.begin()+static_cast<size_t>(offset+size));
        }
        throw std::runtime_error("startup anchor has no file-backed section");
    }
    StartupController(Session &owner_session,const std::vector<unsigned char> &disk,ULONG base):s(owner_session) {
        if(base!=0x400000)throw std::runtime_error("startup requires authenticated preferred-base candidate");
        created=creation(s);owner();deadline=GetTickCount64()+45000;
        check(s.system->GetProcessIdBySystemId(s.owned_pid,&engine_process),"startup owned engine process");
        check(s.system->GetThreadIdBySystemId(s.primary_tid,&engine_primary),"startup owned engine thread");
        sites={__SITE_ROWS__};
        // Check every source/disk/loaded anchor before installing any control.
        for(const auto &site:sites) {
            auto expected=decode(site.hex);
            if(disk_read(disk,site.address,expected.size())!=expected || s.read(site.address,static_cast<ULONG>(expected.size()))!=expected)
                throw std::runtime_error("startup disk or loaded bytes differ");
            printf("OWNED_STARTUP_BYTES address=%08lx hex=%s disk=1 loaded=1\n",site.address,site.hex);
        }
        try {
            for(auto &site:sites) {
                check(s.control->AddBreakpoint(DEBUG_BREAKPOINT_CODE,DEBUG_ANY_ID,&site.bp),"startup add owned breakpoint");
                check(site.bp->GetId(&site.id),"startup breakpoint id");
                check(site.bp->SetOffset(site.address),"startup breakpoint address");
                check(site.bp->SetMatchThreadId(engine_primary),"startup primary-thread match");
                check(site.bp->AddFlags(DEBUG_BREAKPOINT_ENABLED),"startup enable breakpoint");
            }
        } catch(...) { cleanup();throw; }
        printf("OWNED_STARTUP_ARMED count=%zu slot=0 main=(%lu,%lu) load=(320,166) bootstrap_controls=1 manual_input=0\n",sites.size(),main_x,main_y);fflush(stdout);
    }
    ~StartupController(){cleanup();}
    void cleanup() noexcept {
        // DbgEng destroys breakpoint objects on removal; IUnknown cannot retain them.
        for(auto &site:sites)if(site.bp){auto *removed=site.bp;site.bp=nullptr;s.control->RemoveBreakpoint(removed);}
    }
    ULONG reg(const char *name) {
        ULONG index=0;DEBUG_VALUE value={};check(s.registers->GetIndexByName(name,&index),"startup register index");
        check(s.registers->GetValue(index,&value),"startup register value");
        if(value.Type!=DEBUG_VALUE_INT32)throw std::runtime_error("startup register is not x86");return value.I32;
    }
    void set_reg(const char *name,ULONG number) {
        if(strcmp(name,"eax") && strcmp(name,"eip") && strcmp(name,"esp"))throw std::runtime_error("startup register allowlist");
        ULONG index=0;DEBUG_VALUE value={};value.Type=DEBUG_VALUE_INT32;value.I32=number;
        check(s.registers->GetIndexByName(name,&index),"startup write register index");
        check(s.registers->SetValue(index,&value),"startup write register");
    }
    void write(ULONG address,ULONG value,ULONG size=4) {
        bool allowed=(size==4 && (address==raw_x||address==raw_y||address==buttons||address==menu_choice||address==menu_exit)) ||
                     (size==1 && address==primary_button);
        if(!allowed)throw std::runtime_error("startup memory allowlist");
        ULONG actual=0;check(s.memory->WriteVirtual(address,&value,size,&actual),"startup bounded input/menu write");
        if(actual!=size || memcmp(s.read(address,size).data(),&value,size))throw std::runtime_error("startup write verification");
    }
    void point(ULONG x,ULONG y) {
        ULONG shift=s.read(shift_address,1)[0];
        if(shift>20 || x>(0x7fffffffU>>shift) || y>(0x7fffffffU>>shift))throw std::runtime_error("startup cursor shift bound");
        write(raw_x,x<<shift);write(raw_y,y<<shift);write(primary_button,0x80,1);write(buttons,1);
    }
    void pop_return(bool zero_eax) {
        ULONG sp=reg("esp"),target=s.word(sp);
        if(sp<0x10000||sp>0x7ffdfff8||target<0x400000||target>=0x4ec000)throw std::runtime_error("startup return outside native code");
        if(zero_eax)set_reg("eax",0);
        set_reg("eip",target);set_reg("esp",sp+4);
    }
    void retire() {
        write(primary_button,0,1);write(buttons,0);
        for(auto &site:sites) {
            if(!site.bp)throw std::runtime_error("startup lost owned breakpoint");
            auto *removed=site.bp;site.bp=nullptr;
            check(s.control->RemoveBreakpoint(removed),"retire owned startup breakpoint");
            printf("OWNED_STARTUP_RETIRED_SITE id=%lu address=%08lx name=%s hits=%lu\n",site.id,site.address,site.name,site.hits);
        }
        retired=true;
        printf("OWNED_STARTUP_RETIRED count=%zu remaining=0 slot=0 load_seen=1 load_returned=1 gd=%08lx total_hits=%lu buttons=0\n",sites.size(),loaded_gd,total_hits);fflush(stdout);
    }
    bool on_event(ULONG type,ULONG process,ULONG thread,ULONG64 ip) {
        if(retired || type!=DEBUG_EVENT_BREAKPOINT)return false;
        DEBUG_LAST_EVENT_INFO_BREAKPOINT info={};ULONG event=0,pid=0,tid=0,used=0,description_used=0;char description[256]={};
        check(s.control->GetLastEventInformation(&event,&pid,&tid,&info,sizeof(info),&used,description,sizeof(description),&description_used),"startup actual breakpoint event");
        StartupSite *owned=nullptr;for(auto &site:sites)if(site.id==info.Id)owned=&site;
        if(!owned)return false;
        owner();ULONG real_pid=0,real_tid=0;
        check(s.system->GetCurrentProcessSystemId(&real_pid),"startup current process");
        check(s.system->GetCurrentThreadSystemId(&real_tid),"startup current thread");
        if(event!=type||pid!=process||tid!=thread||used!=sizeof(info)||process!=engine_process||thread!=engine_primary||
           real_pid!=s.owned_pid||real_tid!=s.primary_tid||ip!=owned->address||reg("eip")!=owned->address||
           GetTickCount64()>=deadline||++total_hits>50000)throw std::runtime_error("startup event ownership, address or deadline differs");
        ++owned->hits;
        if(owned->hits<=8)printf("OWNED_STARTUP_EVENT id=%lu address=%08lx name=%s hit=%lu\n",owned->id,owned->address,owned->name,owned->hits);
        switch(owned->address) {
        case 0x44789a:case 0x46e4d0:case 0x46e6df:case 0x46fd01: {
            ULONG sp=reg("esp");if(sp<0x10000||sp>0x7ffdfff8)throw std::runtime_error("startup Sleep argument stack bound");
            set_reg("eip",owned->address+7);set_reg("esp",sp+4);break;
        }
        case 0x47bfd0:pop_return(true);break;
        case 0x47bd66:set_reg("eax",0);set_reg("eip",0x47bd73);break;
        case 0x47bdae:set_reg("eax",0);set_reg("eip",0x47bdbf);break;
        case 0x419b80: {
            ULONG descriptor=reg("eax");
            if(descriptor<0x10000||descriptor>0x7ffdffcc)throw std::runtime_error("startup widget bound");
            // Only the actual main Load widget receives synthetic coordinates.
            // An unrelated notice/dialog is never clicked or dismissed here.
            if(s.word(menu_choice)!=5 && s.word(descriptor+0x20)==0x447780) {
                main_widget=descriptor;point(main_x,main_y);
            }
            break;
        }
        case 0x419c51:
            if(s.word(menu_choice)!=5) {
                ULONG descriptor=reg("ebx");
                if(descriptor==main_widget && main_widget && s.word(descriptor+0x20)==0x447780)set_reg("eax",1);
                else if(reg("eax"))throw std::runtime_error("startup unexpected widget or notice click");
            }
            break;
        case 0x447780:
            if(main_requested||!main_widget||reg("eax")!=main_widget||s.word(reg("esp"))!=0x419c60)
                throw std::runtime_error("startup main load callback/caller differs");
            main_requested=true;write(menu_choice,5);write(menu_exit,1);pop_return(false);break;
        case 0x448a68:
            if(!main_requested||s.word(menu_choice)!=5)throw std::runtime_error("startup slot select outside load menu");
            point(320,166);set_reg("eax",1);break;
        case 0x448ae3:
            if(!main_requested||s.word(menu_choice)!=5||s.word(selected_slot)!=0)throw std::runtime_error("startup nonzero or unselected load slot");
            set_reg("eax",1);break;
        case 0x444490:
            if(load_seen||!main_requested||reg("eax")!=0||s.word(selected_slot)!=0||s.word(load_accept)!=1||
               s.word(menu_choice)!=5||s.word(reg("esp"))!=0x448b74)throw std::runtime_error("startup loader is not the native slot-zero call");
            load_seen=true;load_sp=reg("esp");break;
        case 0x448b74:
            if(!load_seen||load_returned||reg("esp")!=load_sp+4)throw std::runtime_error("startup load did not return to its native caller");
            loaded_gd=s.word(0x5202e4);if(loaded_gd<0x10000||loaded_gd>0x7ffe0000-586398)throw std::runtime_error("startup loaded GD bound");
            load_returned=true;break;
        case 0x40b660:
            if(!load_returned||reg("esp")!=load_sp||s.word(reg("esp"))!=0x448b79||s.word(0x5202e4)!=loaded_gd)
                throw std::runtime_error("startup unexpected PlayGame entry");
            retire();break;
        default:throw std::runtime_error("startup unknown owned control");
        }
        fflush(stdout);check(s.control->SetExecutionStatus(DEBUG_STATUS_GO),"continue disclosed startup only");return true;
    }
};
'''


def render_source(source, width, height):
    """Compose before the pause/phase transform; preserve all its anchors."""
    if type(source) is not str:
        raise TypeError('Harness source must be text')
    if 'StartupController' in source:
        raise ValueError('Harness already contains startup controls')
    if (type(width) is not int or type(height) is not int or not 640<=width<=4096
            or not 480<=height<=2160 or width%2 or height%2):
        raise ValueError('Bounded even native-menu dimensions required')
    for anchor in (SNAPSHOT_ANCHOR,LOADED_ANCHOR,EVENT_ANCHOR):
        if source.count(anchor)!=1:
            raise ValueError('Startup source anchor missing or duplicated')
    rows=','.join('{0x%08x,DEBUG_ANY_ID,0,"%s","%s",nullptr}' % (va,SITE_NAMES[va],raw)
                  for va,raw in NATIVE_ANCHORS.items())
    controller=CONTROLLER_SOURCE.replace('__MAIN_X__',str(220+(width-640)//2)).replace('__MAIN_Y__',str(158+(height-480)//2)).replace('__SITE_ROWS__',rows)
    source=source.replace(SNAPSHOT_ANCHOR,controller+SNAPSHOT_ANCHOR,1)
    source=source.replace(LOADED_ANCHOR,LOADED_ANCHOR+'        StartupController startup(s,disk,base);\n',1)
    source=source.replace(EVENT_ANCHOR,'                if (startup.on_event(type,proc,thread,ip)) continue;\n'+EVENT_ANCHOR,1)
    return source
