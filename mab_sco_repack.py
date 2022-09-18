from email import header
from struct import *
import json, os, io

def write_rgltag(str):
    str_enc = str.encode('utf-8'); str_enc_len = len(str_enc)
    f.write(pack('<I', str_enc_len))
    f.write(pack(f'{str_enc_len}s', str_enc))

# swy: source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data
#      from a «scn_advcamp_dale» directory in the same folder as this script
path  = './scn_advcamp_dale.sco'

# swy: donor SCO with the AI mesh and terrain stuff you want to copy over to the file above;
#      probably the original SCO file, it can't be the same file you want to write to
donor = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_advcamp_dale_rgb_mod.sco'

# swy: target/output SCO file location with the combined data
output = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_advcamp_dale.sco'

scene_file =  path.replace('\\', '/').split('/')[-1].split('.')[0]
donor_file = donor.replace('\\', '/').split('/')[-1].split('.')[0]

with open(output, mode='wb') as f:
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
    
#   # swy: stub this AI mesh section for now; this is empty
#   f.write(pack('<I', 4*3)) # ai_mesh_section_size
#   f.write(pack('<I', 0)) # vertex_count
#   f.write(pack('<I', 0)) # edge_count
#   f.write(pack('<I', 0)) # face_count


    # swy: copy the AI mesh and ground stuff over from the other SCO file
    with open(donor, mode='rb') as wf:
        magic = unpack('<I', wf.read(4))[0]; assert(magic == 0xFFFFFD33)
        versi = unpack('<I', wf.read(4))[0]; assert(versi == 4)

        # swy: walk over all the mission object/scene prop entries;
        #      due to the text/strings each of them takes a variable amount of bytes
        object_count = unpack('<I', wf.read(4))[0]

        for i in range(object_count):
            wf.seek(4 + 4 + 4 + (4*3) + (4*3) + (4*3) + (4*3), os.SEEK_CUR);
            rgltag_len = unpack('<I', wf.read(4))[0]
            wf.seek(rgltag_len + 4 + 4 + (4*3), os.SEEK_CUR);

        # swy: we've reached the end of the mission object section; the AI mesh chunk starts here.
        #      copy and paste the rest of the file
        print(f"[i] AI mesh of donor {donor_file} starts at offset; copying from here onwards:", hex(wf.tell()))
        f.write(wf.read())

    ground_layer_look_up = {
        'gray_stone.pgm': 0, 'brown_stone.pgm': 1, 'turf.pgm': 2, 'steppe.pgm': 3, 'snow.pgm': 4, 'earth.pgm': 5, 'desert.pgm': 6, 'forest.pgm': 7,
        'pebbles.pgm': 8, 'village.pgm': 9, 'path.pgm': 10, 'ground_elevation.pfm': -7793, 'ground_leveling.ppm': -12565
    }

    last_scene_width = 0; last_scene_height = 0

    for i, ground_layer in enumerate(ground_layer_look_up):

        try:
            with open(f"{scene_file}/layer_{ground_layer}", 'rb') as f_image:
                ext = ground_layer.split('.')[1].lower()

                ascii_header = [line.decode('utf-8').replace('\n', '').replace('\r', '').split(' ')  for line in [f_image.readline(),f_image.readline(),f_image.readline()]]
                magic  =     ascii_header[0][0]
                width  = int(ascii_header[1][0])
                height = int(ascii_header[1][1])

                print(f'[i] found {ground_layer}; type {magic}, {width} x {height}')
                if magic == 'P5' and ext == 'pgm':
                    header_maxval = float(ascii_header[2][0]); assert(header_maxval == 255)

                    byte_offset = f_image.tell()
                    f_image.seek(0, io.SEEK_END)
                    bytes_remain = f_image.tell() - byte_offset
                    f_image.seek(byte_offset)

                    bytes_to_read = width * height; assert(bytes_to_read == bytes_remain)
                    bytess = unpack(f'<{bytes_to_read}B', f_image.read(bytes_to_read))
                    print('test pgm')
                elif magic == 'P6' and ext == 'ppm':
                    print('test ppm')
                elif magic == 'Pf' and ext == 'pfm':
                    print('test pfm')
                #print(f_image.readline(),f_image.readline(),f_image.readline())
                #print(ext, [h.decode('utf-8').replace('\n', '').replace('\r', '') for h in f_image.readlines()])


        except FileNotFoundError:
            print(f'[!] no layer_{ground_layer} here, skipping...')


    f.write(pack('<I', 0xFF4AD1A6)) # swy: terrain_magic value
    f.write(pack('<I', 4*4)) # swy: terrain_section_size
    f.write(pack('<I', 0)) # swy: num_layers
    f.write(pack('<I', 0)) # swy: scene_width value
    f.write(pack('<I', 0)) # swy: scene_height value