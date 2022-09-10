from struct import *

def read_rgltag():
    size = unpack('<I', f.read(4))[0]
    if not size:
        return ''
    str = unpack(size + 's', f.read(size))[0]
    return str


with open('C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_advcamp_dale.sco', mode='rb') as f:
    magic = unpack('<I', f.read(4))[0]; assert(magic == 0xFFFFFD33)
    versi = unpack('<I', f.read(4))[0]; assert(versi == 4)

    object_count = unpack('<I', f.read(4))[0]


    type = unpack('<I', f.read(4))[0]
    id   = unpack('<I', f.read(4))[0]
    unk  = unpack('<I', f.read(4))[0]
    mtx  = unpack('<f<f<f', f.read(4 * 3))[0]

    pos          = unpack('<f<f<f', f.read(4 * 3))[0]

    entry_no     = unpack('<I', f.read(4))[0]
    menu_item_no = unpack('<I', f.read(4))[0]
    scale        = unpack('<f<f<f', f.read(4 * 3))[0]

    print(magic)