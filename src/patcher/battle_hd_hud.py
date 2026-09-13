"""Exact-byte guarded HUD patches for the 1280x720 battle validation stage.

The new .btlhd section owns these small x86 helpers. Native frame artwork is
loaded from the user-owned game at runtime into a temporary 640x480 surface.
Only the border and sidebar rectangles leave that scratch surface. In
particular, a stats refresh never copies across the battlefield.

Instruction bytes below were read from the SHA-256 identified executable;
recovered C supplied names, not byte authority. The root patcher verifies the
whole input hash and each old-byte record before adding this section. Helpers
have annotated assembly and reproducible machine bytes; generation itself
requires only the Python standard library. This module claims no runtime or
visible validation result.
"""

from __future__ import annotations

try:
    from .battle_hd_layout import BATTLE_LAYOUT
except ImportError:
    from battle_hd_layout import BATTLE_LAYOUT

HUD_CODE_VA = 0x566000
HUD_CODE_LIMIT = 0x56E000
HUD_CODE_FILE_OFFSET = 0x130E00
HUD_SOURCE_SHA256 = '500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae'
HUD_GROUPS = (
    "battle-hd-frame", "battle-hd-hud", "battle-hd-descriptors",
    "battle-hd-dialogs", "battle-hd-tooltip",
)

# (source left, top, width, height, destination left, top), half-open extents.
FRAME_BLITS = ((0, 0, 32, 480, 0, 120),
 (480, 0, 160, 480, 1120, 120),
 (32, 0, 448, 16, 32, 120),
 (32, 464, 448, 16, 32, 584),
 (32, 0, 448, 16, 480, 120),
 (32, 464, 448, 16, 480, 584),
 (32, 0, 192, 16, 928, 120),
 (32, 464, 192, 16, 928, 584))

# Each assembly fragment is local patch code, not a copied game routine.
# (name, virtual address, reproducible x86 assembly, machine bytes as hex).
HUD_CODE_FRAGMENTS = (
    (
        'create native frame scratch', 0x00566000,
        """push ebx
push ecx
push edx
push esi
push edi
mov eax,188
call 0x461c00
test eax,eax
jz create_done
mov edx,640
mov ebx,480
call 0x403d70
mov esi,eax
test esi,esi
jz create_done
call 0x401e60
mov eax,dword ptr [0x5202bc]
mov edx,0
call 0x405ec0
mov edx,eax
mov eax,esi
mov ebx,0
mov ecx,0
push 0
push 0
push 1
push -1
push -1
push -1
push -1
mov edi,dword ptr [esi+184]
call dword ptr [edi+52]
mov eax,dword ptr [0x5202bc]
mov edx,1
call 0x405ec0
mov edx,eax
mov eax,esi
mov ebx,335
mov ecx,0
push 0
push 0
push 1
push -1
push -1
push -1
push -1
mov edi,dword ptr [esi+184]
call dword ptr [edi+52]
mov eax,dword ptr [0x5202bc]
mov edx,2
call 0x405ec0
mov edx,eax
mov eax,esi
mov ebx,0
mov ecx,243
push 0
push 0
push 1
push -1
push -1
push -1
push -1
mov edi,dword ptr [esi+184]
call dword ptr [edi+52]
mov eax,dword ptr [0x5202bc]
mov edx,3
call 0x405ec0
mov edx,eax
mov eax,esi
mov ebx,335
mov ecx,243
push 0
push 0
push 1
push -1
push -1
push -1
push -1
mov edi,dword ptr [esi+184]
call dword ptr [edi+52]
mov eax,esi
create_done:
pop edi
pop esi
pop edx
pop ecx
pop ebx
ret""",
        (
            '5351525657b8bc000000e8f1bbefff85c00f84f0000000ba80020000bbe0010000e84adde9ff89c685f60f84d7000000e82b'
            'bee9ffa1bc025200ba00000000e87cfee9ff89c289f0bb00000000b9000000006a006a006a016aff6aff6aff6aff8bbeb800'
            '0000ff5734a1bc025200ba01000000e848fee9ff89c289f0bb4f010000b9000000006a006a006a016aff6aff6aff6aff8bbe'
            'b8000000ff5734a1bc025200ba02000000e814fee9ff89c289f0bb00000000b9f30000006a006a006a016aff6aff6aff6aff'
            '8bbeb8000000ff5734a1bc025200ba03000000e8e0fde9ff89c289f0bb4f010000b9f30000006a006a006a016aff6aff6aff'
            '6aff8bbeb8000000ff573489f05f5e5a595bc3'
        ),
    ),
    (
        'HD frame before terrain', 0x00566110,
        """pushfd
pushad
call 0x566000
mov esi,eax
test esi,esi
jz frame_done
mov eax,0x51d4c0
call 0x401e60
mov eax,esi
mov edx,0x51d4c0
mov ebx,0
mov ecx,0
push 120
push 0
push 479
push 31
call 0x4024e0
mov eax,esi
mov edx,0x51d4c0
mov ebx,480
mov ecx,0
push 120
push 1120
push 479
push 639
call 0x4024e0
mov eax,esi
mov edx,0x51d4c0
mov ebx,32
mov ecx,0
push 120
push 32
push 15
push 479
call 0x4024e0
mov eax,esi
mov edx,0x51d4c0
mov ebx,32
mov ecx,464
push 584
push 32
push 479
push 479
call 0x4024e0
mov eax,esi
mov edx,0x51d4c0
mov ebx,32
mov ecx,0
push 120
push 480
push 15
push 479
call 0x4024e0
mov eax,esi
mov edx,0x51d4c0
mov ebx,32
mov ecx,464
push 584
push 480
push 479
push 479
call 0x4024e0
mov eax,esi
mov edx,0x51d4c0
mov ebx,32
mov ecx,0
push 120
push 928
push 15
push 223
call 0x4024e0
mov eax,esi
mov edx,0x51d4c0
mov ebx,32
mov ecx,464
push 584
push 928
push 479
push 223
call 0x4024e0
mov edx,dword ptr [0x5202e0]
test edx,edx
jz frame_free
mov eax,0x51d4c0
xor ebx,ebx
xor ecx,ecx
push 0
push 0
push 719
push 1279
call 0x4024e0
frame_free:
mov eax,esi
mov ecx,dword ptr [esi+184]
mov edx,2
call dword ptr [ecx]
frame_done:
popad
popfd
ret""",
        (
            '9c60e8e9feffff89c685f60f846b010000b8c0d45100e835bde9ff89f0bac0d45100bb00000000b9000000006a786a0068df'
            '0100006a1fe894c3e9ff89f0bac0d45100bbe0010000b9000000006a78686004000068df010000687f020000e86dc3e9ff89'
            'f0bac0d45100bb20000000b9000000006a786a206a0f68df010000e84cc3e9ff89f0bac0d45100bb20000000b9d001000068'
            '480200006a2068df01000068df010000e825c3e9ff89f0bac0d45100bb20000000b9000000006a7868e00100006a0f68df01'
            '0000e801c3e9ff89f0bac0d45100bb20000000b9d0010000684802000068e001000068df01000068df010000e8d7c2e9ff89'
            'f0bac0d45100bb20000000b9000000006a7868a00300006a0f68df000000e8b3c2e9ff89f0bac0d45100bb20000000b9d001'
            '0000684802000068a003000068df01000068df000000e889c2e9ff8b15e002520085d2741cb8c0d4510031db31c96a006a00'
            '68cf02000068ff040000e863c2e9ff89f08b8eb8000000ba02000000ff11619dc3'
        ),
    ),
    (
        'frame entry 0x42e8c4', 0x00566290,
        """mov dword ptr [0x511230],0x51d4c0
call 0x566110
jmp 0x42e9a0""",
        (
            'c70530125100c0d45100e871feffffe9fc86ecff'
        ),
    ),
    (
        'frame entry 0x42eb6c', 0x005662B0,
        """mov dword ptr [0x511230],ebp
lea esi,[esp+0x70]
call 0x566110
jmp 0x42ec4d""",
        (
            '892d301251008d742470e851feffffe98989ecff'
        ),
    ),
    (
        'stats sidebar background only', 0x005662D0,
        """pushfd
pushad
call 0x566000
mov esi,eax
test esi,esi
jz sidebar_done
mov eax,esi
mov edx,dword ptr [0x5202e0]
mov ebx,480
xor ecx,ecx
push 120
push 1120
push 479
push 639
call 0x4024e0
mov eax,esi
mov ecx,dword ptr [esi+184]
mov edx,2
call dword ptr [ecx]
sidebar_done:
popad
popfd
ret""",
        (
            '9c60e829fdffff89c685f6743489f08b15e0025200bbe001000031c96a78686004000068df010000687f020000e8dec1e9ff'
            '89f08b8eb8000000ba02000000ff11619dc3'
        ),
    ),
    (
        'stats background entry', 0x00566320,
        """mov dword ptr [0x511230],eax
call 0x5662d0
jmp 0x431051""",
        (
            'a330125100e8a6ffffffe922adecff'
        ),
    ),
    (
        'stat hover final Y', 0x00566330,
        """cmp eax,150
jl 0x42e1f5
jmp 0x42e188""",
        (
            '3d960000000f8cba7eecffe9487eecff'
        ),
    ),
    (
        'stat hover final Y', 0x00566340,
        """cmp eax,203
jg 0x42e1f5
jmp 0x42e195""",
        (
            '3dcb0000000f8faa7eecffe9457eecff'
        ),
    ),
    (
        'stat hover final Y', 0x00566350,
        """cmp eax,211
jl 0x42e230
jmp 0x42e217""",
        (
            '3dd30000000f8cd57eecffe9b77eecff'
        ),
    ),
    (
        'morale fill destination Y; morale fill destination X', 0x00566360,
        """push 146
push 1174
jmp 0x431135""",
        (
            '68920000006896040000e9c6adecff'
        ),
    ),
    (
        'morale text capture bottom; morale text capture left', 0x00566370,
        """push 209
mov ebx,1140
jmp 0x4311c6""",
        (
            '68d1000000bb74040000e947aeecff'
        ),
    ),
    (
        'morale text capture bottom; morale text capture top', 0x00566380,
        """push 209
mov ecx,189
jmp 0x4311e8""",
        (
            '68d1000000b9bd000000e959aeecff'
        ),
    ),
    (
        'morale text destination Y; morale text destination X', 0x00566390,
        """push 189
push 1140
jmp 0x431240""",
        (
            '68bd0000006874040000e9a1aeecff'
        ),
    ),
    (
        'stat label final Y; stat label final right', 0x005663A0,
        """push 226
push 1258
jmp 0x4312af""",
        (
            '68e200000068ea040000e900afecff'
        ),
    ),
    (
        'stat present rectangle final coordinate; stat present rectangle final coordinate', 0x005663B0,
        """push 130
push 1138
jmp 0x4317fe""",
        (
            '68820000006872040000e93fb4ecff'
        ),
    ),
    (
        'animated morale fill destination', 0x005663C0,
        """push 146
push 1174
jmp 0x430f46""",
        (
            '68920000006896040000e977abecff'
        ),
    ),
    (
        'battle results scope entry', 0x00566400,
        """pushfd
push edx
mov edx,dword ptr [0x511230]
mov dword ptr [0x566804],edx
mov dword ptr [0x566800],1
pop edx
popfd
jmp 0x445360""",
        '9c528b1530125100891504685600c70500685600010000005a9de941efedff',
    ),
    (
        'battle results native-size geometry', 0x00566440,
        """mov dword ptr [esp+0x1c],eax
cmp dword ptr [0x566800],0
je results_native_geometry
mov esi,720
sub esi,eax
sar esi,1
mov edi,256
results_native_geometry:
mov eax,188
jmp 0x4454b0""",
        '8944241c833d0068560000740ebed002000029c6d1febf00010000b8bc000000e94bf0edff',
    ),
    (
        'results capture follows computed origin', 0x00566480,
        """lea ebx,[edi+639]
push ebx
mov ebx,edi
jmp 0x4454ec""",
        '8d9f7f0200005389fbe95ef0edff',
    ),
    (
        'results second sprite follows computed origin', 0x005664A0,
        """mov bx,ax
add ebx,edi
mov eax,dword ptr [esp]
jmp 0x445548""",
        '6689c301fb8b0424e99bf0edff',
    ),
    (
        'results text follows computed origin', 0x005664C0,
        """lea eax,[edi+569]
push eax
lea eax,[edi+70]
push eax
jmp 0x445580""",
        '8d8739020000508d474650e9b0f0edff',
    ),
    (
        'battle results scope return', 0x00566500,
        """pushfd
cmp dword ptr [0x566800],0
je results_not_active
pushad
mov eax,dword ptr [0x566804]
mov dword ptr [0x511230],eax
mov dword ptr [0x566800],0
mov eax,0x544cd8
mov edx,576
mov ebx,360
call 0x460af0
popad
results_not_active:
popfd
mov eax,0x544cd8
jmp 0x42f4e6""",
        '9c833d0068560000742a60a104685600a330125100c7050068560000000000b8d84c5400ba40020000bb68010000e8bda5efff619db8d84c5400e9a78fecff',
    ),
    (
        'battle results private scope state', 0x00566800,
        '.byte 0,0,0,0,0,0,0,0',
        '0000000000000000',
    ),
 )

# (group, file offset, old hex, new hex, rationale including VA/RVA).
HUD_PATCH_RECORDS = (
    ('battle-hd-frame', 0x02DCC4, 'a1bc025200891530125100', 'e9c7791300909090909090',
     'VA 0x0042E8C4, RVA 0x0002E8C4: draw native frame to scratch, then compose HD borders before terrain'),
    ('battle-hd-frame', 0x02DF6C, '31d2892d30125100', 'e93f771300909090',
     'VA 0x0042EB6C, RVA 0x0002EB6C: draw native frame to scratch, then compose HD borders before terrain'),
    ('battle-hd-hud', 0x0303DE, 'ba01000000', 'e93d531300',
     'VA 0x00430FDE, RVA 0x00030FDE: restore strictly cropped sidebar before stats without touching terrain'),
    ('battle-hd-hud', 0x03033F, '6a1a6816020000', 'e97c5413009090',
     'VA 0x00430F3F, RVA 0x00030F3F: animated morale fill destination +640,+120 matches stats redraw'),
    ('battle-hd-hud', 0x112FA4, 'f2018f00', '72040701',
     'VA 0x00514DA4, RVA 0x00114DA4: stat icon 0 draw/restore shared coordinates'),
    ('battle-hd-hud', 0x112FA8, 'f101b100', '71042901',
     'VA 0x00514DA8, RVA 0x00114DA8: stat icon 1 draw/restore shared coordinates'),
    ('battle-hd-hud', 0x112FAC, 'f101d300', '71044b01',
     'VA 0x00514DAC, RVA 0x00114DAC: stat icon 2 draw/restore shared coordinates'),
    ('battle-hd-hud', 0x112FB0, 'f101f500', '71046d01',
     'VA 0x00514DB0, RVA 0x00114DB0: stat icon 3 draw/restore shared coordinates'),
    ('battle-hd-hud', 0x112FB4, 'f1011701', '71048f01',
     'VA 0x00514DB4, RVA 0x00114DB4: stat icon 4 draw/restore shared coordinates'),
    ('battle-hd-hud', 0x112FB8, 'f1013901', '7104b101',
     'VA 0x00514DB8, RVA 0x00114DB8: stat icon 5 draw/restore shared coordinates'),
    ('battle-hd-descriptors', 0x112D78, 'f201000072010000', '72040000ea010000',
     'VA 0x00514B78, RVA 0x00114B78: battle command 0 origin +640,+120'),
    ('battle-hd-descriptors', 0x112DAD, '3102000072010000', 'b1040000ea010000',
     'VA 0x00514BAD, RVA 0x00114BAD: battle command 1 origin +640,+120'),
    ('battle-hd-descriptors', 0x112DE2, 'f201000091010000', '7204000009020000',
     'VA 0x00514BE2, RVA 0x00114BE2: battle command 2 origin +640,+120'),
    ('battle-hd-descriptors', 0x112E17, 'f2010000b0010000', '7204000028020000',
     'VA 0x00514C17, RVA 0x00114C17: battle command 3 origin +640,+120'),
    ('battle-hd-descriptors', 0x112E4C, '3102000091010000', 'b104000009020000',
     'VA 0x00514C4C, RVA 0x00114C4C: battle command 4 origin +640,+120'),
    ('battle-hd-descriptors', 0x112E81, 'f901000000000000', '7904000078000000',
     'VA 0x00514C81, RVA 0x00114C81: battle command 5 origin +640,+120'),
    ('battle-hd-descriptors', 0x019163, '813880020000', '813800050000',
     'VA 0x00419D63, RVA 0x00019D63: HD descriptor draw X clip'),
    ('battle-hd-descriptors', 0x01918C, '813980020000', '813900050000',
     'VA 0x00419D8C, RVA 0x00019D8C: HD descriptor draw X clip'),
    ('battle-hd-dialogs', 0x02CBE8, 'b8c0010000', 'b840040000',
     'VA 0x0042D7E8, RVA 0x0002D7E8: battle dialog horizontal span'),
    ('battle-hd-dialogs', 0x02CC0F, 'b8e0010000', 'b8d0020000',
     'VA 0x0042D80F, RVA 0x0002D80F: battle dialog vertical center'),
    ('battle-hd-dialogs', 0x02CE32, 'bbf0000000', 'bb68010000',
     'VA 0x0042DA32, RVA 0x0002DA32: battle dialog cursor return battlefield center'),
    ('battle-hd-dialogs', 0x02CE37, 'ba40010000', 'ba40020000',
     'VA 0x0042DA37, RVA 0x0002DA37: battle dialog cursor return battlefield center'),
    ('battle-hd-dialogs', 0x02CF54, 'b8c0010000', 'b840040000',
     'VA 0x0042DB54, RVA 0x0002DB54: battle dialog horizontal span'),
    ('battle-hd-dialogs', 0x02CF81, 'b8e0010000', 'b8d0020000',
     'VA 0x0042DB81, RVA 0x0002DB81: battle dialog vertical center'),
    ('battle-hd-dialogs', 0x02D25A, 'bbf0000000', 'bb68010000',
     'VA 0x0042DE5A, RVA 0x0002DE5A: battle dialog cursor return battlefield center'),
    ('battle-hd-dialogs', 0x02D25F, 'ba40010000', 'ba40020000',
     'VA 0x0042DE5F, RVA 0x0002DE5F: battle dialog cursor return battlefield center'),
    ('battle-hd-dialogs', 0x02E8DC, 'e87f5e0100', 'e81f6f1300',
     'VA 0x0042F4DC, RVA 0x0002F4DC: scope shared results message to battle while preserving its native return address'),
    ('battle-hd-dialogs', 0x02E8E1, 'b8d84c5400', 'e91a701300',
     'VA 0x0042F4E1, RVA 0x0002F4E1: restore results render device and scope, then queue battlefield-center cursor before teardown'),
    ('battle-hd-dialogs', 0x0448A7, '8944241cb8bc000000', 'e9940f120090909090',
     'VA 0x004454A7, RVA 0x000454A7: center native 640-wide results artwork only inside battle scope'),
    ('battle-hd-dialogs', 0x0448E7, '687f020000', 'e9940f1200',
     'VA 0x004454E7, RVA 0x000454E7: results background capture uses computed origin and native width'),
    ('battle-hd-dialogs', 0x044929, '31db', '89fb',
     'VA 0x00445529, RVA 0x00045529: results first sprite shares computed capture/restore origin; non-battle origin stays zero'),
    ('battle-hd-dialogs', 0x044942, '6689c38b0424', 'e9590f120090',
     'VA 0x00445542, RVA 0x00045542: results second sprite remains adjacent to first at computed origin'),
    ('battle-hd-dialogs', 0x044979, '68390200006a46', 'e9420f12009090',
     'VA 0x00445579, RVA 0x00045579: results text bounds follow artwork origin without changing text width or click behavior'),
    ('battle-hd-tooltip', 0x02D570, '81fa17020000', '81fa97040000',
     'VA 0x0042E170, RVA 0x0002E170: stat hover final X'),
    ('battle-hd-tooltip', 0x02D583, '83f81e7c6d', 'e9a8811300',
     'VA 0x0042E183, RVA 0x0002E183: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D588, '81fa6f020000', '81faef040000',
     'VA 0x0042E188, RVA 0x0002E188: stat hover final X'),
    ('battle-hd-tooltip', 0x02D590, '83f8537f60', 'e9ab811300',
     'VA 0x0042E190, RVA 0x0002E190: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D603, '81faf3010000', '81fa73040000',
     'VA 0x0042E203, RVA 0x0002E203: stat hover final X'),
    ('battle-hd-tooltip', 0x02D612, '83f85b7c19', 'e939811300',
     'VA 0x0042E212, RVA 0x0002E212: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D617, '81fa6f020000', '81faef040000',
     'VA 0x0042E217, RVA 0x0002E217: stat hover final X'),
    ('battle-hd-tooltip', 0x02D61F, '3d89000000', '3d01010000',
     'VA 0x0042E21F, RVA 0x0002E21F: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D63E, '81faf3010000', '81fa73040000',
     'VA 0x0042E23E, RVA 0x0002E23E: stat hover final X'),
    ('battle-hd-tooltip', 0x02D64D, '3d91000000', '3d09010000',
     'VA 0x0042E24D, RVA 0x0002E24D: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D654, '81fa6f020000', '81faef040000',
     'VA 0x0042E254, RVA 0x0002E254: stat hover final X'),
    ('battle-hd-tooltip', 0x02D65C, '3db3000000', '3d2b010000',
     'VA 0x0042E25C, RVA 0x0002E25C: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D67B, '81faf3010000', '81fa73040000',
     'VA 0x0042E27B, RVA 0x0002E27B: stat hover final X'),
    ('battle-hd-tooltip', 0x02D68A, '3db3000000', '3d2b010000',
     'VA 0x0042E28A, RVA 0x0002E28A: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D691, '81fa6f020000', '81faef040000',
     'VA 0x0042E291, RVA 0x0002E291: stat hover final X'),
    ('battle-hd-tooltip', 0x02D699, '3dd5000000', '3d4d010000',
     'VA 0x0042E299, RVA 0x0002E299: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D6B8, '81faf3010000', '81fa73040000',
     'VA 0x0042E2B8, RVA 0x0002E2B8: stat hover final X'),
    ('battle-hd-tooltip', 0x02D6C7, '3dd5000000', '3d4d010000',
     'VA 0x0042E2C7, RVA 0x0002E2C7: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D6CE, '81fa6f020000', '81faef040000',
     'VA 0x0042E2CE, RVA 0x0002E2CE: stat hover final X'),
    ('battle-hd-tooltip', 0x02D6D6, '3df7000000', '3d6f010000',
     'VA 0x0042E2D6, RVA 0x0002E2D6: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D6F5, '81faf3010000', '81fa73040000',
     'VA 0x0042E2F5, RVA 0x0002E2F5: stat hover final X'),
    ('battle-hd-tooltip', 0x02D704, '3df7000000', '3d6f010000',
     'VA 0x0042E304, RVA 0x0002E304: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D70B, '81fa6f020000', '81faef040000',
     'VA 0x0042E30B, RVA 0x0002E30B: stat hover final X'),
    ('battle-hd-tooltip', 0x02D713, '3d19010000', '3d91010000',
     'VA 0x0042E313, RVA 0x0002E313: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D732, '81faf3010000', '81fa73040000',
     'VA 0x0042E332, RVA 0x0002E332: stat hover final X'),
    ('battle-hd-tooltip', 0x02D741, '3d19010000', '3d91010000',
     'VA 0x0042E341, RVA 0x0002E341: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D748, '81fa6f020000', '81faef040000',
     'VA 0x0042E348, RVA 0x0002E348: stat hover final X'),
    ('battle-hd-tooltip', 0x02D750, '3d3b010000', '3db3010000',
     'VA 0x0042E350, RVA 0x0002E350: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D76F, '81faf3010000', '81fa73040000',
     'VA 0x0042E36F, RVA 0x0002E36F: stat hover final X'),
    ('battle-hd-tooltip', 0x02D77E, '3d3b010000', '3db3010000',
     'VA 0x0042E37E, RVA 0x0002E37E: stat hover final Y'),
    ('battle-hd-tooltip', 0x02D785, '81fa6f020000', '81faef040000',
     'VA 0x0042E385, RVA 0x0002E385: stat hover final X'),
    ('battle-hd-tooltip', 0x02D78D, '3d5d010000', '3dd5010000',
     'VA 0x0042E38D, RVA 0x0002E38D: stat hover final Y'),
    ('battle-hd-tooltip', 0x02E054, 'bbd3010000', 'bb4b020000',
     'VA 0x0042EC54, RVA 0x0002EC54: center battle tooltip strip within battlefield'),
    ('battle-hd-tooltip', 0x02E059, 'bad9010000', 'ba19030000',
     'VA 0x0042EC59, RVA 0x0002EC59: center battle tooltip strip within battlefield'),
    ('battle-hd-tooltip', 0x02E05E, 'b8a0000000', 'b8e0010000',
     'VA 0x0042EC5E, RVA 0x0002EC5E: center battle tooltip strip within battlefield'),
    ('battle-hd-hud', 0x03052E, '6a1a6816020000', 'e92d5213009090',
     'VA 0x0043112E, RVA 0x0003112E: morale fill destination Y; morale fill destination X'),
    ('battle-hd-hud', 0x0305BA, 'b945000000', 'b9bd000000',
     'VA 0x004311BA, RVA 0x000311BA: morale text capture top'),
    ('battle-hd-hud', 0x0305BF, '6a59bbf4010000', 'e9ac5113009090',
     'VA 0x004311BF, RVA 0x000311BF: morale text capture bottom; morale text capture left'),
    ('battle-hd-hud', 0x0305CB, '686a020000', '68ea040000',
     'VA 0x004311CB, RVA 0x000311CB: morale text capture right'),
    ('battle-hd-hud', 0x0305E1, '6a59b945000000', 'e99a5113009090',
     'VA 0x004311E1, RVA 0x000311E1: morale text capture bottom; morale text capture top'),
    ('battle-hd-hud', 0x0305E8, 'bbf4010000', 'bb74040000',
     'VA 0x004311E8, RVA 0x000311E8: morale text capture left'),
    ('battle-hd-hud', 0x0305ED, '686a020000', '68ea040000',
     'VA 0x004311ED, RVA 0x000311ED: morale text capture right'),
    ('battle-hd-hud', 0x030639, '6a4568f4010000', 'e9525113009090',
     'VA 0x00431239, RVA 0x00031239: morale text destination Y; morale text destination X'),
    ('battle-hd-hud', 0x0306A8, '6a6a686a020000', 'e9f35013009090',
     'VA 0x004312A8, RVA 0x000312A8: stat label final Y; stat label final right'),
    ('battle-hd-hud', 0x0306AF, '68f4010000', '6874040000',
     'VA 0x004312AF, RVA 0x000312AF: stat label final left'),
    ('battle-hd-hud', 0x030704, '6897000000', '680f010000',
     'VA 0x00431304, RVA 0x00031304: stat label final Y'),
    ('battle-hd-hud', 0x030709, '686a020000', '68ea040000',
     'VA 0x00431309, RVA 0x00031309: stat label final right'),
    ('battle-hd-hud', 0x03070E, '68f4010000', '6874040000',
     'VA 0x0043130E, RVA 0x0003130E: stat label final left'),
    ('battle-hd-hud', 0x03074C, '68db000000', '6853010000',
     'VA 0x0043134C, RVA 0x0003134C: stat label final Y'),
    ('battle-hd-hud', 0x030751, '686a020000', '68ea040000',
     'VA 0x00431351, RVA 0x00031351: stat label final right'),
    ('battle-hd-hud', 0x030756, '68f4010000', '6874040000',
     'VA 0x00431356, RVA 0x00031356: stat label final left'),
    ('battle-hd-hud', 0x0307A0, '68b9000000', '6831010000',
     'VA 0x004313A0, RVA 0x000313A0: stat label final Y'),
    ('battle-hd-hud', 0x0307A5, '686a020000', '68ea040000',
     'VA 0x004313A5, RVA 0x000313A5: stat label final right'),
    ('battle-hd-hud', 0x0307AA, '68f4010000', '6874040000',
     'VA 0x004313AA, RVA 0x000313AA: stat label final left'),
    ('battle-hd-hud', 0x0307E5, 'b917010000', 'b98f010000',
     'VA 0x004313E5, RVA 0x000313E5: stat sprite final Y'),
    ('battle-hd-hud', 0x0307F2, 'bbf2010000', 'bb72040000',
     'VA 0x004313F2, RVA 0x000313F2: status portrait x'),
    ('battle-hd-hud', 0x030847, 'b9f3000000', 'b96b010000',
     'VA 0x00431447, RVA 0x00031447: stat sprite final Y'),
    ('battle-hd-hud', 0x03084C, 'bbe8010000', 'bb68040000',
     'VA 0x0043144C, RVA 0x0003144C: status badges x'),
    ('battle-hd-hud', 0x030868, 'b86a020000', 'b8ea040000',
     'VA 0x00431468, RVA 0x00031468: status badge right edge'),
    ('battle-hd-hud', 0x0308C1, 'b9ff000000', 'b977010000',
     'VA 0x004314C1, RVA 0x000314C1: stat sprite final Y'),
    ('battle-hd-hud', 0x030A46, 'bf11020000', 'bf91040000',
     'VA 0x00431646, RVA 0x00031646: ammunition icon x'),
    ('battle-hd-hud', 0x030AC5, 'b9b4000000', 'b92c010000',
     'VA 0x004316C5, RVA 0x000316C5: stat sprite final Y'),
    ('battle-hd-hud', 0x030B0F, '681f010000', '6897010000',
     'VA 0x0043170F, RVA 0x0003170F: stat label final Y'),
    ('battle-hd-hud', 0x030B14, '686a020000', '68ea040000',
     'VA 0x00431714, RVA 0x00031714: stat label final right'),
    ('battle-hd-hud', 0x030B19, '68f4010000', '6874040000',
     'VA 0x00431719, RVA 0x00031719: stat label final left'),
    ('battle-hd-hud', 0x030B52, '6841010000', '68b9010000',
     'VA 0x00431752, RVA 0x00031752: stat label final Y'),
    ('battle-hd-hud', 0x030B57, '686a020000', '68ea040000',
     'VA 0x00431757, RVA 0x00031757: stat label final right'),
    ('battle-hd-hud', 0x030B5C, '68f4010000', '6874040000',
     'VA 0x0043175C, RVA 0x0003175C: stat label final left'),
    ('battle-hd-hud', 0x030BA7, 'b918000000', 'b990000000',
     'VA 0x004317A7, RVA 0x000317A7: stat sprite final Y'),
    ('battle-hd-hud', 0x030BB4, 'bbf5010000', 'bb75040000',
     'VA 0x004317B4, RVA 0x000317B4: selected unit portrait x'),
    ('battle-hd-hud', 0x030BCC, 'b970020000', 'b9f0040000',
     'VA 0x004317CC, RVA 0x000317CC: stat present/cursor rectangle'),
    ('battle-hd-hud', 0x030BD1, 'bb0a000000', 'bb82000000',
     'VA 0x004317D1, RVA 0x000317D1: stat present/cursor rectangle'),
    ('battle-hd-hud', 0x030BD6, 'baf2010000', 'ba72040000',
     'VA 0x004317D6, RVA 0x000317D6: stat present/cursor rectangle'),
    ('battle-hd-hud', 0x030BE0, '6862010000', '68da010000',
     'VA 0x004317E0, RVA 0x000317E0: stat present rectangle final coordinate'),
    ('battle-hd-hud', 0x030BF7, '6a0a68f2010000', 'e9b44b13009090',
     'VA 0x004317F7, RVA 0x000317F7: stat present rectangle final coordinate; stat present rectangle final coordinate'),
    ('battle-hd-hud', 0x030BFE, '6862010000', '68da010000',
     'VA 0x004317FE, RVA 0x000317FE: stat present rectangle final coordinate'),
    ('battle-hd-hud', 0x030C03, 'b90a000000', 'b982000000',
     'VA 0x00431803, RVA 0x00031803: stat present/cursor rectangle'),
    ('battle-hd-hud', 0x030C08, 'bbf2010000', 'bb72040000',
     'VA 0x00431808, RVA 0x00031808: stat present/cursor rectangle'),
    ('battle-hd-hud', 0x030C0D, '6870020000', '68f0040000',
     'VA 0x0043180D, RVA 0x0003180D: stat present rectangle final coordinate'),
 )


def _build_code() -> bytes:
    end = max(va + len(bytes.fromhex(code)) for _, va, _, code in HUD_CODE_FRAGMENTS)
    if end > HUD_CODE_LIMIT:
        raise ValueError("battle HUD helper code exceeds its reserved section slice")
    result = bytearray(end - HUD_CODE_VA)
    occupied: set[int] = set()
    for _, va, _, code in HUD_CODE_FRAGMENTS:
        block = bytes.fromhex(code)
        start = va - HUD_CODE_VA
        slots = set(range(start, start + len(block)))
        if start < 0 or occupied.intersection(slots):
            raise ValueError("battle HUD helper code overlaps another helper")
        occupied.update(slots)
        result[start:start + len(block)] = block
    return bytes(result)


HUD_CODE = _build_code()


def build_patches() -> list[tuple[str, int, str, str, str]]:
    """Return source-file patches; the root patcher appends HUD_CODE separately."""
    if (BATTLE_LAYOUT.battlefield != (32, 136, 1120, 584)
            or BATTLE_LAYOUT.sidebar != (1120, 120, 1280, 600)):
        raise ValueError("HUD byte inventory supports only the audited 1280x720 layout")
    return list(HUD_PATCH_RECORDS)
