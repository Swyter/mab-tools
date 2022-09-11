from struct import *
import json, os

def write_rgltag(str):
    str_enc = str.encode('utf-8'); str_enc_len = len(str_enc)
    f.write(pack('<I', str_enc_len))
    pack(f'{str_enc_len}s', str_enc)


path = './scn_advcamp_dale.sco'

scene_file = path.replace('\\', '/').split('/')[-1].split('.')[0]

with open(path, mode='wb') as f:
    f.write(pack('<I', 0xFFFFFD33))
    f.write(pack('<I', 4))

    with open(f"{scene_file}/mission_objects.json") as f_json:
       mission_objects = json.load(f_json)

    object_count = len(mission_objects)

    f.write(pack('<I', object_count))

    object_type = {'prop': 0, 'entry': 1, 'item': 2, 'unused': 3, 'plant': 4, 'passage': 5}

    for i, object in enumerate(mission_objects):
        f.write(pack('<I',  object_type[object["type"]]))
        f.write(pack('<I',  object["id"]))
        f.write(pack('<I',  int(object["garbage"])))
        f.write(pack('<3f', object["mtx_a"]))
        f.write(pack('<3f', object["mtx_b"]))
        f.write(pack('<3f', object["mtx_c"]))
        f.write(pack('<3f', object["pos"]))
        write_rgltag(object["str"])

        f.write(pack('<I',  object["entry_no"]))
        f.write(pack('<I',  object["menu_item_no"]))
        f.write(pack('<3f', object["scale"]))
    
    exit()

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
                    if layer_str == 'ground_leveling':
                        ground[layer_str].append(([0xFFFFFF] * rle)) # swy: make empty RGB vertex paint cells white
                    else:
                        ground[layer_str].append(([       0] * rle)) # swy: otherwise make them pure black

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

            # swy: floating point grayscale with the raw terrain height at each point. Note: Photoshop 2017 wrongly loads these files vertically flipped
            if layer_str == 'ground_elevation':
                with open(f"{scene_file}/layer_{layer_str}.pfm", mode='wb') as fw:
                    # swy: format spec at http://netpbm.sourceforge.net/doc/pfm.html; scanlines from left to right, from BOTTOM to top
                    #      small three-line ASCII header with binary floats afterwards. e.g.: 
                    #      Pf
                    #      71 71
                    #      -1.000
                    fw.write(f'Pf\n{scene_width} {scene_height}\n-1.000\n'.encode('utf-8')) # swy: PF has RGB color, Pf is grayscale. align the first binary bytes to 16 bytes with the extra padded .000 in the ASCII part, make the number negative to let the program know that we're using little-endian floats

                    flattened_list = [value for sub_list in ground[layer_str] for value in sub_list]
                    reversed_list = []

                    # swy: reverse the row ordering because the PFM format is from bottom to top, unlike every other NetPBM one, of course :)
                    for i in reversed(range(scene_height)):
                        reversed_list += flattened_list[i*scene_width : (i*scene_width) + scene_width][::-1] # swy: grab one "line" worth of data from the farthest point, and add it first; sort them backwards

                    fw.write(pack(f'<{scene_width * scene_height}f', *reversed_list))

            # swy: Red/Green/Blue vertex coloring/terrain tinting
            elif layer_str == 'ground_leveling':
                with open(f"{scene_file}/layer_{layer_str}.ppm", mode='wb') as fw:
                    # swy: format spec at http://netpbm.sourceforge.net/doc/ppm.html; scanlines from left to right, from TOP to bottom
                    #      small three-line ASCII header with binary floats afterwards. e.g.: 
                    #      P6
                    #      71 71
                    #      255
                    fw.write(f'P6\n{scene_width} {scene_height}\n255\n'.encode('utf-8'))

                    flattened_list = [value for sub_list in ground[layer_str] for value in sub_list]
                    reversed_list = []
                    # swy: flip or mirror each row from right-to-left to left-to-right
                    for i in range(scene_height):
                        reversed_list += flattened_list[i*scene_width : (i*scene_width) + scene_width][::-1]

                    for elem in reversed_list:
                        fw.write(pack(f'<3B', (elem >> 8*2) & 0xFF, (elem >> 8*1) & 0xFF, (elem >> 8*0) & 0xFF))

            # swy: unsigned byte (0-254) grayscale with the amount of paint for this material/layer
            elif not layer_str == 'ground_leveling':
                with open(f"{scene_file}/layer_{layer_str}.pgm", mode='wb') as fw:
                    # swy: format spec at http://netpbm.sourceforge.net/doc/pgm.html; scanlines from left to right, from TOP to bottom
                    #      small three-line ASCII header with binary floats afterwards. e.g.: 
                    #      P5
                    #      71 71
                    #      255
                    fw.write(f'P5\n{scene_width} {scene_height}\n255\n'.encode('utf-8'))

                    flattened_list = [value for sub_list in ground[layer_str] for value in sub_list]
                    reversed_list = []
                    # swy: flip or mirror each row from right-to-left to left-to-right
                    for i in range(scene_height):
                        reversed_list += flattened_list[i*scene_width : (i*scene_width) + scene_width][::-1]

                    fw.write(pack(f'<{scene_width * scene_height}B', *reversed_list))

js = json.dumps(obj=mission_objects, indent=2, ensure_ascii=False)
print(js)

with open(f"{scene_file}/mission_objects.json", mode='w') as fw:
    fw.write(js)