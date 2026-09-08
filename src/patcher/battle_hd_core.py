"""Exact-byte core patches for the isolated 1280x720 tactical battle lane.

The checked-in x86 encodings use the stock register/stack ABI. ASSEMBLY_BLOCKS
is the reproducible source of each encoding; Keystone/Unicorn are development
verification tools only, never patcher runtime dependencies. Geometry and
boundaries are statically/emulator tested, not claims of live rendering proof.
"""

try:
    from .battle_hd_layout import BATTLE_LAYOUT
except ImportError:
    from battle_hd_layout import BATTLE_LAYOUT

CORE_CODE_VA = 0x562000
CORE_CODE_OFFSET = 0x12CE00
CORE_CODE_LIMIT = 0x4000
EXPECTED_SOURCE_SHA256 = "500055d77d03d514e8d3168506bd10f67cd8569bcc450604ff8192f46cdaf3ae"

# (name, VA, assembly, exact machine-code hex). Relocated full_redraw labels
# retain original VAs solely to make its stock control flow reviewable.
ASSEMBLY_BLOCKS = (
    ('clamp_camera', 0x562000, """
pushad
mov esi, dword ptr [0x532048]
test esi, esi
jz done
mov ecx, dword ptr [esi + 804]
cmp ecx, 1
jl invalid
cmp ecx, 20
jg invalid
cmp dword ptr [esi + 800], 1
jl invalid
cmp dword ptr [esi + 800], 7
jg invalid
sub ecx, 17
jge max_ready
xor ecx, ecx
max_ready:
mov eax, dword ptr [esi + 808]
test eax, eax
jge lower_ready
xor eax, eax
lower_ready:
cmp eax, ecx
jle store_x
mov eax, ecx
store_x:
mov dword ptr [esi + 808], eax
mov dword ptr [esi + 812], 0
jmp done
invalid:
mov dword ptr [esi + 808], 0
mov dword ptr [esi + 812], 0
done:
popad
ret
""",
        '608b354820530085f674618b8e2403000083f9017c4283f9147f3d83be20030000017c3483be20030000077f2b83e9117d02'
        '31c98b862803000085c07d0231c039c87e0289c8898628030000c7862c03000000000000eb14c7862803000000000000c786'
        '2c0300000000000061c3'
    ),
    ('mouse_cell', 0x562100, """
push ebx
push ecx
push esi
call 0x562000
mov esi, dword ptr [0x532048]
test esi, esi
jz invalid
cmp dword ptr [esi + 804], 1
jl invalid
cmp dword ptr [esi + 804], 20
jg invalid
cmp dword ptr [esi + 800], 1
jl invalid
cmp dword ptr [esi + 800], 7
jg invalid
mov eax, dword ptr [0x544cfc]
mov edx, dword ptr [0x544d00]
mov cl, byte ptr [0x54512c]
sar eax, cl
sar edx, cl
sub eax, 32
cmp eax, 1088
jae invalid
sub edx, 136
cmp edx, 448
jae invalid
shr eax, 6
shr edx, 6
mov ebx, eax
add ebx, dword ptr [esi + 808]
cmp ebx, dword ptr [esi + 804]
jge invalid
cmp edx, dword ptr [esi + 800]
jge invalid
clc
pop esi
pop ecx
pop ebx
ret
invalid:
mov eax, -1
mov edx, -1
stc
pop esi
pop ecx
pop ebx
ret
""",
        '535156e8f8feffff8b354820530085f6747483be24030000017c6b83be24030000147f6283be20030000017c5983be200300'
        '00077f50a1fc4c54008b15004d54008a0d2c515400d3f8d3fa83e8203d40040000733181ea8800000081fac00100007323c1'
        'e806c1ea0689c3039e280300003b9e240300007d0d3b96200300007d05f85e595bc3b8ffffffffbafffffffff95e595bc3'
    ),
    ('recenter', 0x562200, """
pushad
call 0x562000
mov ecx, dword ptr [0x532048]
test ecx, ecx
jz done
cmp eax, 22
jae done
imul eax, eax, 31
movzx esi, word ptr [ecx + eax + 856]
movzx ebx, word ptr [ecx + eax + 858]
mov eax, esi
mov edx, ebx
call 0x562300
test eax, eax
jnz done
mov ecx, dword ptr [0x532048]
sub esi, 8
sub ebx, 3
mov dword ptr [ecx + 808], esi
mov dword ptr [ecx + 812], ebx
call 0x562000
done:
mov eax, dword ptr [0x532048]
mov dword ptr [esp + 28], eax
popad
ret
""",
        '60e8fafdffff8b0d4820530085c9744283f816733d6bc01f0fb7b401580300000fb79c015a03000089f089dae8cf00000085'
        'c0751d8b0d4820530083ee0883eb0389b12803000089992c030000e8aefdffffa1482053008944241c61c3'
    ),
    ('world_visible', 0x562300, """
push ecx
push ebx
mov ecx, dword ptr [0x532048]
test ecx, ecx
jz invisible
cmp dword ptr [ecx + 804], 1
jl invisible
cmp dword ptr [ecx + 804], 20
jg invisible
cmp dword ptr [ecx + 800], 1
jl invisible
cmp dword ptr [ecx + 800], 7
jg invisible
cmp eax, dword ptr [ecx + 804]
jae invisible
cmp edx, dword ptr [ecx + 800]
jae invisible
mov ebx, eax
sub ebx, dword ptr [ecx + 808]
cmp ebx, 17
jae invisible
mov ebx, edx
sub ebx, dword ptr [ecx + 812]
cmp ebx, 7
jae invisible
mov eax, 1
pop ebx
pop ecx
ret
invisible:
xor eax, eax
pop ebx
pop ecx
ret
""",
        '51538b0d4820530085c9745683b924030000017c4d83b924030000147f4483b920030000017c3b83b920030000077f323b81'
        '24030000732a3b9120030000732289c32b992803000083fb11731589d32b992c03000083fb077308b8010000005b59c331c0'
        '5b59c3'
    ),
    ('grid_coordinates', 0x562400, """
call 0x562100
jc invalid
mov ebp, eax
mov edi, edx
mov eax, edx
mov edx, dword ptr [0x532048]
mov esi, dword ptr [edx + 808]
add esi, ebp
add edi, dword ptr [edx + 812]
jmp 0x42cbc1
invalid:
jmp 0x42cbb8
""",
        'e8fbfcffff721f89c589d789d08b15482053008bb22803000001ee03ba2c030000e99ba7ecffe98da7ecff'
    ),
    ('pan_coordinates', 0x562480, """
call 0x562100
jc invalid
mov ebx, eax
mov esi, edx
mov edx, dword ptr [0x532048]
add ebx, dword ptr [edx + 808]
add esi, dword ptr [edx + 812]
jmp 0x42c8bc
invalid:
jmp 0x42c8df
""",
        'e87bfcffff721b89c389d68b1548205300039a2803000003b22c030000e91aa4ecffe938a4ecff'
    ),
    ('pan_entry', 0x562500, """
push ebx
push ecx
push edx
push esi
push edi
push ebp
call 0x562000
jmp 0x42c846
""",
        '535152565755e8f5faffffe936a3ecff'
    ),
    ('pan_clamp', 0x562540, """
call 0x562000
jmp 0x42cae0
""",
        'e8bbfaffffe996a5ecff'
    ),
    ('tile_guard', 0x562580, """
push eax
call 0x562300
test eax, eax
pop eax
jz invisible
push ebx
push ecx
push esi
push edi
push ebp
jmp 0x42ffb5
invisible:
ret
""",
        '50e87afdffff85c058740a5351565755e920daecffc3'
    ),
    ('tile_y', 0x562600, """
add eax, 136
mov ecx, dword ptr [ebp - 8]
jmp 0x42ffe6
""",
        '05880000008b4df8e9d9d9ecff'
    ),
    ('dirty_guard', 0x562640, """
push eax
call 0x562300
test eax, eax
pop eax
jz invisible
push ecx
push esi
push ebp
sub esp, 8
jmp 0x430b26
invisible:
ret
""",
        '50e8bafcffff85c058740b51565583ec08e9d0e4ecffc3'
    ),
    ('dirty_y', 0x5626C0, """
add edi, 200
call 0x42ffb0
jmp 0x430bab
""",
        '81c7c8000000e8e5d8ecffe9dbe4ecff'
    ),
    ('full_redraw', 0x562800, """
L_430c20:
push ebx
L_430c21:
push ecx
L_430c22:
push edx
L_430c23:
push esi
L_430c24:
push edi
L_430c25:
push ebp
L_430c26:
sub esp, 0xc
L_430c29:
call 0x562000
mov eax, dword ptr [0x5202e0]
L_430c2e:
mov ebx, dword ptr [0x532048]
L_430c34:
mov dword ptr [0x511230], eax
L_430c39:
mov edi, 17
L_430c3e:
mov ebx, dword ptr [ebx + 0x328]
L_430c44:
mov eax, dword ptr [0x532048]
L_430c49:
mov ecx, dword ptr [eax + 0x328]
L_430c4f:
add ecx, edi
L_430c51:
cmp ebx, ecx
L_430c53:
jge L_430c7b
L_430c55:
mov ecx, dword ptr [eax + 0x32c]
L_430c5b:
mov eax, dword ptr [0x532048]
L_430c60:
mov eax, dword ptr [eax + 0x32c]
L_430c66:
add eax, 7
L_430c68:
cmp ecx, eax
L_430c6a:
jge L_430c78
L_430c6c:
mov edx, ecx
L_430c6e:
mov eax, ebx
L_430c70:
call 0x42ffb0
L_430c75:
inc ecx
L_430c76:
jmp L_430c5b
L_430c78:
inc ebx
L_430c79:
jmp L_430c44
L_430c7b:
mov eax, dword ptr [0x544d00]
mov cl, byte ptr [0x54512c]
sar eax, cl
cmp eax, 584
jge L_430e5e
mov ebx, dword ptr [0x544d14]
add eax, dword ptr [ebx + 16]
cmp eax, 136
jle L_430e5e
mov eax, dword ptr [0x544cfc]
L_430c80:
mov ebx, dword ptr [0x544d14]
L_430c86:
mov cl, byte ptr [0x54512c]
L_430c8c:
mov esi, dword ptr [0x544d00]
L_430c92:
mov edi, dword ptr [ebx + 0xc]
L_430c95:
mov edx, dword ptr [ebx + 0x10]
L_430c98:
sar eax, cl
L_430c9a:
sar esi, cl
L_430c9c:
mov dword ptr [esp + 4], eax
L_430ca0:
mov dword ptr [esp + 8], esi
L_430ca4:
add edi, eax
L_430ca6:
add esi, edx
L_430ca8:
cmp eax, 1120
L_430cad:
jge L_430e5e
L_430cb3:
cmp edi, 0x20
L_430cb6:
jle L_430e5e
L_430cbc:
mov ecx, dword ptr [0x544d10]
L_430cc2:
mov ebp, ecx
L_430cc4:
cmp eax, 0x20
L_430cc7:
jl L_430e12
L_430ccd:
cmp edi, 0x20
L_430cd0:
jg L_430ce8
L_430cd2:
mov dword ptr [esp + 4], 0x21
L_430cda:
test ebp, ebp
L_430cdc:
je L_430ce8
L_430cde:
mov eax, 0x544cd8
L_430ce3:
call 0x460f90
L_430ce8:
cmp edi, 1119
L_430cee:
jle L_430d03
L_430cf0:
mov edi, 1119
L_430cf5:
test ebp, ebp
L_430cf7:
je L_430d03
L_430cf9:
mov eax, 0x544cd8
L_430cfe:
call 0x460f90
L_430d03:
cmp dword ptr [esp + 8], 136
L_430d08:
jge L_430d20
L_430d0a:
mov dword ptr [esp + 8], 136
L_430d12:
test ebp, ebp
L_430d14:
je L_430d20
L_430d16:
mov eax, 0x544cd8
L_430d1b:
call 0x460f90
L_430d20:
cmp esi, 583
L_430d26:
jle L_430d3b
L_430d28:
mov esi, 583
L_430d2d:
test ebp, ebp
L_430d2f:
je L_430d3b
L_430d31:
mov eax, 0x544cd8
L_430d36:
call 0x460f90
L_430d3b:
push 136
L_430d3d:
xor eax, eax
L_430d3f:
push 0x20
L_430d41:
mov ax, word ptr [esp + 0x10]
L_430d46:
mov ecx, 136
L_430d4b:
push eax
L_430d4c:
mov ebx, 0x20
L_430d51:
xor edx, edx
L_430d53:
push 1119
L_430d58:
mov dword ptr [esp + 0x10], eax
L_430d5c:
mov eax, dword ptr [0x5202e0]
L_430d61:
call 0x4024e0
L_430d66:
mov eax, dword ptr [esp]
L_430d69:
push eax
L_430d6a:
xor eax, eax
L_430d6c:
push 0x20
L_430d6e:
mov ax, si
L_430d71:
push eax
L_430d72:
xor eax, eax
L_430d74:
mov ecx, dword ptr [esp + 0xc]
L_430d78:
mov ax, word ptr [esp + 0x10]
L_430d7d:
mov ebx, 0x20
L_430d82:
push eax
L_430d83:
xor edx, edx
L_430d85:
mov eax, dword ptr [0x5202e0]
L_430d8a:
call 0x4024e0
L_430d8f:
test ebp, ebp
L_430d91:
je L_430d9d
L_430d93:
mov eax, 0x544cd8
L_430d98:
call 0x461000
L_430d9d:
xor ecx, ecx
L_430d9f:
mov cx, word ptr [esp + 8]
L_430da4:
xor ebx, ebx
L_430da6:
push ecx
L_430da7:
mov bx, word ptr [esp + 8]
L_430dac:
xor eax, eax
L_430dae:
push ebx
L_430daf:
mov ax, si
L_430db2:
push eax
L_430db3:
xor eax, eax
L_430db5:
mov ax, di
L_430db8:
push eax
L_430db9:
xor edx, edx
L_430dbb:
mov eax, dword ptr [0x5202e0]
L_430dc0:
call 0x4024e0
L_430dc5:
test ebp, ebp
L_430dc7:
je L_430dd3
L_430dc9:
mov eax, 0x544cd8
L_430dce:
call 0x460ea0
L_430dd3:
cmp edi, 1119
L_430dd9:
je L_430e00
L_430ddb:
xor ecx, ecx
L_430ddd:
mov cx, word ptr [esp + 8]
L_430de2:
xor ebx, ebx
L_430de4:
push ecx
L_430de5:
mov bx, di
L_430de8:
xor eax, eax
L_430dea:
push ebx
L_430deb:
mov ax, si
L_430dee:
push eax
L_430def:
push 1119
L_430df4:
xor edx, edx
L_430df6:
mov eax, dword ptr [0x5202e0]
L_430dfb:
call 0x4024e0
L_430e00:
cmp esi, 583
L_430e06:
jne L_430e31
L_430e08:
add esp, 0xc
L_430e0b:
pop ebp
L_430e0c:
pop edi
L_430e0d:
pop esi
L_430e0e:
pop edx
L_430e0f:
pop ecx
L_430e10:
pop ebx
L_430e11:
ret
L_430e12:
mov dword ptr [esp + 4], 0x20
L_430e1a:
test ecx, ecx
L_430e1c:
je L_430ccd
L_430e22:
mov eax, 0x544cd8
L_430e27:
call 0x460f90
L_430e2c:
jmp L_430ccd
L_430e31:
xor ecx, ecx
L_430e33:
mov cx, si
L_430e36:
push ecx
L_430e37:
push 0x20
L_430e39:
push 583
L_430e3e:
mov ebx, 0x20
L_430e43:
push 1119
L_430e48:
mov eax, dword ptr [0x5202e0]
L_430e4d:
xor edx, edx
L_430e4f:
call 0x4024e0
L_430e54:
add esp, 0xc
L_430e57:
pop ebp
L_430e58:
pop edi
L_430e59:
pop esi
L_430e5a:
pop edx
L_430e5b:
pop ecx
L_430e5c:
pop ebx
L_430e5d:
ret
L_430e5e:
push 136
L_430e60:
push 0x20
L_430e62:
push 583
L_430e67:
mov ecx, 136
L_430e6c:
mov ebx, 0x20
L_430e71:
push 1119
L_430e76:
mov eax, dword ptr [0x5202e0]
L_430e7b:
xor edx, edx
L_430e7d:
call 0x4024e0
L_430e82:
add esp, 0xc
L_430e85:
pop ebp
L_430e86:
pop edi
L_430e87:
pop esi
L_430e88:
pop edx
L_430e89:
pop ecx
L_430e8a:
pop ebx
L_430e8b:
ret
""",
        '53515256575583ec0ce8f2f7ffffa1e00252008b1d48205300a330125100bf110000008b9b28030000a1482053008b882803'
        '000001f939cb7d278b882c030000a1482053008b802c03000083c00739c17d0c89ca89d8e855d7ecff41ebe243ebc8a1004d'
        '54008a0d2c515400d3f83d480200000f8dfd0100008b1d144d54000343103d880000000f8ee9010000a1fc4c54008b1d144d'
        '54008a0d2c5154008b35004d54008b7b0c8b5310d3f8d3fe894424048974240801c701d63d600400000f8db101000083ff20'
        '0f8ea80100008b0d104d540089cd83f8200f8c4b01000083ff207f16c74424042100000085ed740ab8d84c5400e896e6efff'
        '81ff5f0400007e13bf5f04000085ed740ab8d84c5400e87be6efff817c2408880000007d16c74424088800000085ed740ab8'
        'd84c5400e85be6efff81fe470200007e13be4702000085ed740ab8d84c5400e840e6efff688800000031c06a20668b442410'
        'b98800000050bb2000000031d2685f04000089442410a1e0025200e862fbe9ff8b04245031c06a206689f05031c08b4c240c'
        '668b442410bb200000005031d2a1e0025200e839fbe9ff85ed740ab8d84c5400e84be6efff31c9668b4c240831db51668b5c'
        '240831c0536689f05031c06689f85031d2a1e0025200e803fbe9ff85ed740ab8d84c5400e8b5e4efff81ff5f040000742531'
        'c9668b4c240831db516689fb31c0536689f050685f04000031d2a1e0025200e8c8fae9ff81fe47020000752983c40c5d5f5e'
        '5a595bc3c74424042000000085c90f84a5feffffb8d84c5400e84ce5efffe996feffff31c96689f1516a206847020000bb20'
        '000000685f040000a1e002520031d2e874fae9ff83c40c5d5f5e5a595bc368880000006a206847020000b988000000bb2000'
        '0000685f040000a1e002520031d2e843fae9ff83c40c5d5f5e5a595bc3'
    ),
    # Neighbor composition includes cells beyond the current tile. The stock
    # right/bottom checks compare the current cell with the count, admitting
    # count itself as a neighbor at the arena edge. Preserve all registers and
    # return CMP flags against count-1 before the original conditional branch.
    ('neighbor_col_eax_edx', 0x563000,
     'push ecx\nmov ecx, dword ptr [edx+804]\ndec ecx\ncmp eax, ecx\npop ecx\nret',
     '518b8a240300004939c859c3'),
    ('neighbor_row_eax_edx', 0x563040,
     'push ecx\nmov ecx, dword ptr [edx+800]\ndec ecx\ncmp eax, ecx\npop ecx\nret',
     '518b8a200300004939c859c3'),
    ('neighbor_row_eax_ecx', 0x563080,
     'push edx\nmov edx, dword ptr [ecx+800]\ndec edx\ncmp eax, edx\npop edx\nret',
     '528b91200300004a39d05ac3'),
    ('neighbor_row_ebp_edx', 0x5630C0,
     'push eax\nmov eax, dword ptr [edx+800]\ndec eax\ncmp ebp, eax\npop eax\nret',
     '508b82200300004839c558c3'),
    ('neighbor_col_eax_ecx', 0x563100,
     'push edx\nmov edx, dword ptr [ecx+804]\ndec edx\ncmp eax, edx\npop edx\nret',
     '528b91240300004a39d05ac3'),
    # Clip overlaps to existing cells as well as the physical battlefield.
    # Short arenas must leave the remaining columns/rows entirely clear.
    ('bounded_tile_blit', 0x563200, """
push eax
push edx
mov dword ptr [esp+12], 32
mov dword ptr [esp+16], 136
mov eax, dword ptr [0x532048]
mov edx, dword ptr [eax+804]
sub edx, dword ptr [eax+808]
cmp edx, 17
jle width_ready
mov edx, 17
width_ready:
shl edx, 6
add edx, 31
mov dword ptr [esp+20], edx
mov edx, dword ptr [eax+800]
cmp edx, 7
jle rows_ready
mov edx, 7
rows_ready:
shl edx, 6
add edx, 135
mov dword ptr [esp+24], edx
pop edx
pop eax
mov ebx, esi
mov ecx, dword ptr [ebp-12]
jmp dword ptr [edi+0x34]
""", '5052c744240c20000000c744241088000000a1482053008b90240300002b902803000083fa117e05ba11000000c1e20683c21f895424148b902003000083fa077e05ba07000000c1e20681c287000000895424185a5889f38b4df4ff6734'),
    # Battle shares both HD surfaces with the adventure renderer. The native
    # teardown only fades the palette, so the map's regional redraw leaves
    # battle pixels in map padding. Clear before native map graphics reload.
    ('clear_battle_surfaces_on_exit', 0x563300, """
pushfd
pushad
mov eax, dword ptr [0x5202e0]
test eax, eax
jz clear_primary
cmp eax, 0x51d4c0
je clear_primary
call 0x401e60
clear_primary:
mov eax, 0x51d4c0
call 0x401e60
popad
popfd
jmp 0x422960
""", '9c60a1e002520085c0740c3dc0d451007405e849ebe9ffb8c0d45100e83febe9ff619de938f6ebff'),
)

# (group, file offset, old hex, new hex, rationale with VA/RVA).
PATCH_SPECS = (
    ('battle-hd-viewport', 0x02E93D, 'e81e34ffff', 'e8be3d1300', 'VA 0042F53D, RVA 02F53D: clear shared HD primary/back surfaces after battle free and before native map graphics reload, removing stale battle pixels from map padding'),
    ('battle-hd-viewport', 0x02F430, '89f38b4df4ff5734', 'e8cb311300909090', 'VA 00430030, RVA 030030: clip terrain sprite to existing visible cells and physical battlefield, preserving native image bounds and overlap within the field'),
    ('battle-hd-viewport', 0x02F4EE, '8b4df489f3ff5734', 'e80d311300909090', 'VA 004300EE, RVA 0300EE: clip movement-area overlay to existing visible cells and physical battlefield'),
    ('battle-hd-viewport', 0x02F649, '89f38b4df4ff5734', 'e8b22f1300909090', 'VA 00430249, RVA 030249: clip neighboring movement-area overlay to existing visible cells and physical battlefield'),
    ('battle-hd-viewport', 0x02F744, '8b4df489f3ff5734', 'e8b72e1300909090', 'VA 00430344, RVA 030344: clip active movement-area overlay to existing visible cells and physical battlefield'),
    ('battle-hd-viewport', 0x02FD8C, '8b4df489f3ff5734', 'e86f281300909090', 'VA 0043098C, RVA 03098C: clip alternate movement-area overlay to existing visible cells and physical battlefield'),
    ('battle-hd-viewport', 0x02FC07, '89f38b4df4ff5734', 'e8f4291300909090', 'VA 00430807, RVA 030807: clip selected-unit marker to existing visible cells and physical battlefield'),
    ('battle-hd-viewport', 0x02F0CA, '8b8224030000', '8b8220030000', 'VA 0042FCCA, RVA 02FCCA: animation lower-neighbor limit uses arena rows, not columns'),
    ('battle-hd-viewport', 0x02F206, '3baa20030000', 'e8b532130090', 'VA 0042FE06, RVA 02FE06: guard next-row animation neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02F24B, '3b8224030000', 'e8b031130090', 'VA 0042FE4B, RVA 02FE4B: guard next-column animation neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02F293, '3baa20030000', 'e82832130090', 'VA 0042FE93, RVA 02FE93: guard next-row diagonal animation neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02F29E, '3b8224030000', 'e85d31130090', 'VA 0042FE9E, RVA 02FE9E: guard next-column diagonal animation neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02F825, '3b8220030000', 'e8162c130090', 'VA 00430425, RVA 030425: guard next-row diagonal sprite neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02F830, '3b8224030000', 'e8cb2b130090', 'VA 00430430, RVA 030430: guard next-column diagonal sprite neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02F93A, '3b8120030000', 'e8412b130090', 'VA 0043053A, RVA 03053A: guard next-row sprite neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02F9A4, '3b8220030000', 'e8972a130090', 'VA 004305A4, RVA 0305A4: guard next-row diagonal sprite neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02FA1F, '3b8124030000', 'e8dc2a130090', 'VA 0043061F, RVA 03061F: guard next-column diagonal sprite neighbor against actual arena boundary'),
    ('battle-hd-viewport', 0x02FA87, '3b8224030000', 'e87429130090', 'VA 00430687, RVA 030687: guard next-column sprite neighbor against actual arena boundary'),
    ('battle-hd-camera', 0x026220, '51525689c2', 'e9dbb31300', 'VA 00426E20, RVA 026E20: guarded 17-column camera recenter, retaining an already visible selection'),
    ('battle-hd-camera', 0x02B4F0, '53515689c1', 'e90b621300', 'VA 0042C0F0, RVA 02C0F0: actual-map-aware 17x7 visibility test'),
    ('battle-hd-camera', 0x02BC40, '535152565755', 'e9bb5c130090', 'VA 0042C840, RVA 02C840: clamp the camera before keyboard and drag panning'),
    ('battle-hd-camera', 0x02BD42, '83c207', '83c211', 'VA 0042C942, RVA 02C942: right-scroll extent is 17 columns'),
    ('battle-hd-camera', 0x02BE81, 'a148205300', 'e9ba5a1300', 'VA 0042CA81, RVA 02CA81: replace drag clamp with nonnegative map-aware clamp'),
    ('battle-hd-input', 0x02BC70, '8b15fc4c5400', 'e90b5c130090', 'VA 0042C870, RVA 02C870: pan occupancy lookup rejects gutters and missing map cells'),
    ('battle-hd-input', 0x02BF58, '8b15fc4c5400', 'e9a358130090', 'VA 0042CB58, RVA 02CB58: physical-coordinate tactical hit testing with half-open pixel and actual map bounds'),
    ('battle-hd-viewport', 0x02F3B0, '5351565755', 'e9cb251300', 'VA 0042FFB0, RVA 02FFB0: tile renderer rejects coordinates outside real map and expanded visible cells'),
    ('battle-hd-viewport', 0x02F3E0, '83c0108b4df8', 'e91b26130090', 'VA 0042FFE0, RVA 02FFE0: tile and composed sprite projection top16 to136'),
    ('battle-hd-viewport', 0x02FF20, '51565583ec08', 'e91b1b130090', 'VA 00430B20, RVA 030B20: dirty and animation tile redraw guarded by actual map visibility'),
    ('battle-hd-viewport', 0x02FF33, '83c607', '83c611', 'VA 00430B33, RVA 030B33: dirty tile visibility spans17 columns'),
    ('battle-hd-viewport', 0x02FF8B, '0510000000', '0588000000', 'VA 00430B8B, RVA 030B8B: dirty tile source/destination top follows y136 projection'),
    ('battle-hd-viewport', 0x02FFA3, '83c750e805f4ffff', 'e9181b1300909090', 'VA 00430BA3, RVA 030BA3: dirty tile bottom follows y136 projection (bottom-exclusive cell offset200)'),
    ('battle-hd-viewport', 0x030020, '535152565755', 'e9db1b130090', 'VA 00430C20, RVA 030C20: expanded17x7 full redraw, physical bounds and gutter-safe cursor copybacks'),

)


def _check_layout():
    actual = (BATTLE_LAYOUT.width, BATTLE_LAYOUT.height, BATTLE_LAYOUT.left,
              BATTLE_LAYOUT.top, BATTLE_LAYOUT.columns, BATTLE_LAYOUT.rows,
              BATTLE_LAYOUT.tile_size, BATTLE_LAYOUT.sidebar_left)
    if actual != (1280, 720, 32, 136, 17, 7, 64, 1120):
        raise ValueError("Battle core encodings require the frozen 1280x720 layout")


def _code_bytes():
    _check_layout()
    code = bytearray(CORE_CODE_LIMIT)
    end = 0
    for name, va, _assembly, encoding in ASSEMBLY_BLOCKS:
        offset = va - CORE_CODE_VA
        data = bytes.fromhex(encoding)
        if offset < end or offset + len(data) > len(code):
            raise ValueError(f"Core code block overlaps or exceeds allocation: {name}")
        code[offset:offset + len(data)] = data
        end = offset + len(data)
    return bytes(code[:end])


def build_patches():
    """Return guarded source edits; the caller appends CORE_CODE separately."""
    _check_layout()
    return PATCH_SPECS


CORE_CODE = _code_bytes()
