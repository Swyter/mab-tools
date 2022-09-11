from struct import *
import json, os

def read_rgltag():
    size = unpack('<I', f.read(4))[0]
    if not size:
        return ''

    str = unpack(f'{size}s', f.read(size))[0].decode('utf-8')
    return str


path = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_lebennin_coast_3.sco'

scene_file = path.replace('\\', '/').split('/')[-1].split('.')[0]

os.makedirs(scene_file, exist_ok=True) # https://stackoverflow.com/a/41959938/674685

with open(path, mode='rb') as f:
    magic = unpack('<I', f.read(4))[0]; assert(magic == 0xFFFFFD33)
    versi = unpack('<I', f.read(4))[0]; assert(versi == 4)

    object_count = unpack('<I', f.read(4))[0]

    mission_objects = []

    object_type = ['prop', 'entry', 'item', 'unused', 'plant', 'passage']

    for i in range(object_count):
        type    = unpack('<I',  f.read(4    ))[0]
        id      = unpack('<I',  f.read(4    ))[0]
        garbage = unpack('<I',  f.read(4    ))[0]
        mtx_a   = unpack('<3f', f.read(4 * 3))
        mtx_b   = unpack('<3f', f.read(4 * 3))
        mtx_c   = unpack('<3f', f.read(4 * 3))
        pos     = unpack('<3f', f.read(4 * 3))
        str     = read_rgltag()

        entry_no     = unpack('<I',  f.read(4    ))[0]
        menu_item_no = unpack('<I',  f.read(4    ))[0]
        scale        = unpack('<3f', f.read(4 * 3))

        object = {
            'type': object_type[type],
            'id': id,
            'garbage': '%0#x' % garbage,
            'rotation_matrix': [mtx_a, mtx_b, mtx_c],
            'pos': pos,
            'str': str,
            'entry_no': entry_no,
            'menu_entry_no': menu_item_no,
            'scale': scale,
        }

        print(i, object_type[type], str, entry_no)
        mission_objects.append(object)
    
    ai_mesh = {'vertices': [], 'edges': [], 'faces': []}

    ai_mesh_section_size = unpack('<I', f.read(4))[0]
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


    terrain_magic = unpack('<I', f.read(4))[0]; assert(terrain_magic == 0xFF4AD1A6)
    terrain_section_size = unpack('<I', f.read(4))[0]
    num_layers = unpack('<I', f.read(4))[0]
    scene_width = unpack('<I', f.read(4))[0]
    scene_height = unpack('<I', f.read(4))[0]

    block_count = scene_width * scene_height

    ground = {}

    for i in range(num_layers):
        index = unpack('<I', f.read(4))[0]
        layer_str = read_rgltag()
        enabled = unpack('<I', f.read(4))[0]


        ground[layer_str] = []

        print(">> ", index, layer_str, enabled)

        if enabled:
            remaining_blocks = block_count

            while remaining_blocks > 0:
                rle = unpack('<I', f.read(4))[0]

                if rle:
                    ground[layer_str].append(([0] * rle))

                remaining_blocks -= rle

                if remaining_blocks <= 0:
                    break

                elem_count = unpack('<I', f.read(4))[0]

                remaining_blocks -= elem_count

                if layer_str == 'ground_elevation':
                    elem = unpack(f'<{elem_count}f', f.read(4 * elem_count)) # swy: 4-byte float
                elif layer_str == 'ground_leveling':
                    elem = unpack(f'<{elem_count}I', f.read(4 * elem_count)) # swy: 4-byte unsigned integer (uint) that holds vertex coloring
                else:
                    elem = unpack(f'<{elem_count}B', f.read(1 * elem_count)) # swy: 1 unsigned byte


                ground[layer_str].append(elem)

            # swy: floating point grayscale with the raw terrain height at each point
            if layer_str == 'ground_elevation':
                with open(f"{scene_file}/layer_{layer_str}.pfm", mode='wb') as fw:
                    # swy: format spec at http://netpbm.sourceforge.net/doc/pfm.html;
                    #      small three-line ASCII header with binary floats afterwards. e.g.: 
                    #      Pf
                    #      71 71
                    #      -1.000
                    fw.write(f'Pf\n{scene_width} {scene_height}\n-1.000\n'.encode('utf-8')) # swy: PF has RGB color, Pf is grayscale. align the first binary bytes to 16 bytes with the extra padded .000 in the ASCII part, make the number negative to let the program know that we're using little-endian floats

                    flattened_list = [value for sub_list in ground[layer_str] for value in sub_list]
                    fw.write(pack(f'<{scene_width * scene_height}f', *flattened_list))
            elif layer_str == 'ground_leveling':
                with open(f"{scene_file}/layer_{layer_str}.ppm", mode='wb') as fw:
                    # swy: format spec at http://netpbm.sourceforge.net/doc/pgm.html;
                    #      small three-line ASCII header with binary floats afterwards. e.g.: 
                    #      P5
                    #      71 71
                    #      255
                    fw.write(f'P6\n{scene_width} {scene_height}\n255\n'.encode('utf-8'))

                    flattened_list = [value for sub_list in ground[layer_str] for value in sub_list]

                    for elem in flattened_list:
                        fw.write(pack(f'<3B', (elem >> 8*3) & 0xF, (elem >> 8*2) & 0xF, (elem >> 8*1) & 0xF))
            # swy: unsigned byte (0-254) grayscale with the amount of paint
            elif not layer_str == 'ground_leveling':
                with open(f"{scene_file}/layer_{layer_str}.pgm", mode='wb') as fw:
                    # swy: format spec at http://netpbm.sourceforge.net/doc/pgm.html;
                    #      small three-line ASCII header with binary floats afterwards. e.g.: 
                    #      P5
                    #      71 71
                    #      255
                    fw.write(f'P5\n{scene_width} {scene_height}\n255\n'.encode('utf-8'))

                    flattened_list = [value for sub_list in ground[layer_str] for value in sub_list]
                    fw.write(pack(f'<{scene_width * scene_height}B', *flattened_list))

js = json.dumps(obj=mission_objects, indent=2, ensure_ascii=False)
print(js)

with open(f"{scene_file}/mission_objects.json", mode='w') as fw:
    fw.write(js)