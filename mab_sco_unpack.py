from struct import *
import json

def read_rgltag():
    size = unpack('<I', f.read(4))[0]
    if not size:
        return ''

    str = unpack(f'{size}s', f.read(size))[0].decode('utf-8')
    return str


with open('C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_advcamp_dale.sco', mode='rb') as f:
    magic = unpack('<I', f.read(4))[0]; assert(magic == 0xFFFFFD33)
    versi = unpack('<I', f.read(4))[0]; assert(versi == 4)

    object_count = unpack('<I', f.read(4))[0]

    mission_objects = []

    object_type = ['prop', 'entry', 'item', 'unused', 'plant', 'passage']

    for i in range(object_count):
        type   = unpack('<I',  f.read(4    ))[0]
        id     = unpack('<I',  f.read(4    ))[0]
        unk    = unpack('<I',  f.read(4    ))[0]
        mtx_a  = unpack('<3f', f.read(4 * 3))
        mtx_b  = unpack('<3f', f.read(4 * 3))
        mtx_c  = unpack('<3f', f.read(4 * 3))
        pos    = unpack('<3f', f.read(4 * 3))
        str    = read_rgltag()

        entry_no     = unpack('<I',  f.read(4    ))[0]
        menu_item_no = unpack('<I',  f.read(4    ))[0]
        scale        = unpack('<3f', f.read(4 * 3))

        object = {
            'type': object_type[type],
            'id': id,
            'unk': '%0#x' % unk,
            'mtx': [mtx_a, mtx_b, mtx_c],
            'pos': pos,
            'str': str,
            'entry_no': entry_no,
            'menu_entry_no': menu_item_no,
            'scale': scale,
        }

        print(i, object_type[type], str, entry_no)
        mission_objects.append(object)
    
    ai_mesh = {'vertices': [], 'edges': [], 'faces': []}

    section_size = unpack('<I', f.read(4))[0]
    vertex_count = unpack('<I', f.read(4))[0]

    for i in range(vertex_count):
        vertex = unpack('<3f', f.read(4 * 3))
        ai_mesh['vertices'].append(vertex)

    edge_count = unpack('<I', f.read(4))[0]

    for i in range(edge_count):
        edge = unpack('<5I', f.read(4 * 5))
        ai_mesh['edges'].append(edge)

    face_count = unpack('<I', f.read(4))[0]

    for i in range(face_count):
        edge_count = unpack('<I', f.read(4))[0]
        face = unpack(f'<{edge_count}I', f.read(4 * edge_count))
        edge = unpack(f'<{edge_count}I', f.read(4 * edge_count))
        has_more = unpack('<I', f.read(4))[0]

        ai_mesh_id = has_more and unpack('<I', f.read(4))[0] or 0

        ai_mesh['faces'].append({'edge_count': edge_count, 'face': face, 'edge': edge, 'has_more': has_more, 'ai_mesh_id': ai_mesh_id})

print(json.dumps(obj=mission_objects, indent=2, ensure_ascii=False))