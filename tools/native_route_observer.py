"""Read-only native campaign callback observations on an authenticated game image."""
import re

SITES={'campaign':0x447700,'campaign_choice':0x448B90,'map_entry':0x40B660}
DISASSEMBLY_COMMIT='1a4b06280b88962e27d600b2670ee44acb316daf'


def instrument(source):
    anchor='                pause_owned(s);'
    declaration='        bool entered=false,exited=false,crashed=false;'
    exception='                else if (type==DEBUG_EVENT_EXCEPTION) {'
    if source.count(anchor)!=1 or source.count(declaration)!=1 or source.count(exception)!=1 or source.count('seconds>90')!=1:
        raise ValueError('Native harness insertion sites differ')
    setup=r'''
                if (!routes_armed) {
                    for (ULONG address : {0x447700u,0x448b90u,0x40b660u}) {
                        IDebugBreakpoint *watch=nullptr;
                        check(s.control->AddBreakpoint(DEBUG_BREAKPOINT_CODE,DEBUG_ANY_ID,&watch),"route breakpoint");
                        check(watch->SetOffset(address),"route breakpoint address");
                        check(watch->AddFlags(DEBUG_BREAKPOINT_ENABLED|DEBUG_BREAKPOINT_ONE_SHOT),"route breakpoint flags");
                        watch->Release();
                    }
                    routes_armed=true;
                    printf("ROUTE_ARMED after_initialization=1\n"); fflush(stdout);
                }
'''
    observed=r'''                else if (type==DEBUG_EVENT_BREAKPOINT && (ip==0x447700 || ip==0x448b90 || ip==0x40b660)) {
                    ULONG owner=0,tid=0;
                    check(s.system->GetCurrentProcessSystemId(&owner),"route owner");
                    check(s.system->GetCurrentThreadSystemId(&tid),"route thread");
                    if (owner!=s.owned_pid || tid!=s.primary_tid) throw std::runtime_error("route owner identity differs");
                    const char *name=ip==0x447700?"campaign":ip==0x448b90?"campaign_choice":"map_entry";
                    printf("ROUTE_NATIVE event=%s ip=%08llx tid=%lu raw_x=%ld raw_y=%ld game_data=%08lx\n",
                        name,ip,tid,static_cast<LONG>(s.word(0x544cfc)),static_cast<LONG>(s.word(0x544d00)),s.word(0x5202e4));
                    fflush(stdout);
                }
'''
    return source.replace(declaration,'        bool routes_armed=false;\n'+declaration).replace(anchor,anchor+setup).replace(exception,observed+exception).replace('seconds>90','seconds>180')


def parse(log):
    rows=[]
    for line in log.splitlines():
        if 'ROUTE_NATIVE' not in line:continue
        match=re.fullmatch(r'ROUTE_NATIVE event=(campaign|campaign_choice|map_entry) ip=([0-9a-f]{8}) tid=([0-9]+) raw_x=(-?[0-9]+) raw_y=(-?[0-9]+) game_data=([0-9a-f]{8})',line)
        if not match or int(match[2],16)!=SITES[match[1]] or int(match[3])<=0:
            raise ValueError('Malformed native route event')
        rows.append(dict(event=match[1],ip=match[2],tid=int(match[3]),raw_x=int(match[4]),raw_y=int(match[5]),game_data=match[6]))
    if len({r['event'] for r in rows})!=len(rows) or [r['event'] for r in rows]!=list(SITES)[:len(rows)] or len({r['tid'] for r in rows})>1:
        raise ValueError('Duplicated, cross-thread or reordered campaign route')
    return rows
