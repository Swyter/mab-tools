from struct import *
import json, os

def write_rgltag(str):
    str_enc = str.encode('utf-8'); str_enc_len = len(str_enc)
    f.write(pack('<I', str_enc_len))
    f.write(pack(f'{str_enc_len}s', str_enc))


path = './scn_advcamp_dale.sco'

scene_file = path.replace('\\', '/').split('/')[-1].split('.')[0]

with open(path, mode='wb') as f:
    f.write(pack('<I', 0xFFFFFD33)) # swy: magic value
    f.write(pack('<I', 4)) # swy: SCO file version

    with open(f"{scene_file}/mission_objects.json") as f_json:
       mission_objects = json.load(f_json)

    object_count = len(mission_objects)

    f.write(pack('<I', object_count))

    object_type = {'prop': 0, 'entry': 1, 'item': 2, 'unused': 3, 'plant': 4, 'passage': 5}

    for i, object in enumerate(mission_objects):
        f.write(pack('<I',  object_type[object["type"]]))
        f.write(pack('<I',  object["id"]))
        f.write(pack('<I',  int(object["garbage"], 16)))
        f.write(pack('<3f', *object["rotation_matrix"][0]))
        f.write(pack('<3f', *object["rotation_matrix"][1]))
        f.write(pack('<3f', *object["rotation_matrix"][2]))
        f.write(pack('<3f', *object["pos"]))
        write_rgltag(object["str"])

        f.write(pack('<I',   object["entry_no"]))
        f.write(pack('<I',   object["menu_entry_no"]))
        f.write(pack('<3f', *object["scale"]))
    
    # swy: stub this AI mesh section for now; this is empty
    f.write(pack('<I', 4*3)) # ai_mesh_section_size
    f.write(pack('<I', 0)) # vertex_count
    f.write(pack('<I', 0)) # edge_count
    f.write(pack('<I', 0)) # face_count


    f.write(pack('<I', 0xFF4AD1A6)) # swy: terrain_magic value
    f.write(pack('<I', 4*4)) # swy: terrain_section_size
    f.write(pack('<I', 0)) # swy: num_layers
    f.write(pack('<I', 0)) # swy: scene_width value
    f.write(pack('<I', 0)) # swy: scene_height value