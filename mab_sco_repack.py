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

    last_scene_width = None; last_scene_height = None

    for i, ground_layer in enumerate(ground_layer_look_up):

        try:
            with open(f"{scene_file}/layer_{ground_layer}", 'rb') as f_image:
                ext = ground_layer.split('.')[1].lower()

                # swy: grab the three ASCII lines that make out the header of these NetPBM formats; strip their carriage returns and split each line into words/tokens
                ascii_header = [
                    line.decode('utf-8').replace('\n', '').replace('\r', '').split(' ')           \
                        for line in [ f_image.readline(), f_image.readline(), f_image.readline() ]
                ]
                magic  =       ascii_header[0][0]  # line 1, magic value
                width  =   int(ascii_header[1][0]) # line 2, width and height
                height =   int(ascii_header[1][1])
                maxval = float(ascii_header[2][0]) # line 3, extra thing

                # swy: grab how far away we are from the start after reading the ASCII part, use it to compute how many bytes the rest of the data takes
                header_end_byte_offset = f_image.tell();                f_image.seek(0, io.SEEK_END)
                bytes_remain = f_image.tell() - header_end_byte_offset; f_image.seek(header_end_byte_offset)

                if not last_scene_width:
                    last_scene_width = width
                else:
                    if last_scene_width != width:
                        print('[e] the width of all layer images must match')
                        
                if not last_scene_height:
                    last_scene_height = height
                else:
                    if last_scene_height != height:
                        print('[e] the height of all layer images must match')

                # swy: actually read and interpret the binary data after the header, depending on the format/sub-variant
                print(f'[i] found layer_{ground_layer}; type {magic}, {width} x {height}')

                if magic == 'P5' and ext == 'pgm':
                    assert(maxval == 255)
                    cells_to_read = width * height
                    bytes_to_read = cells_to_read * 1; assert(cells_to_read == bytes_remain)
                    contents = unpack(f'<{cells_to_read}B', f_image.read(bytes_to_read))

                elif magic == 'P6' and ext == 'ppm':
                    assert(maxval == 255)
                    cells_to_read = width * height
                    bytes_to_read = cells_to_read * 3; assert(bytes_to_read == bytes_remain)
                    contents = unpack(f'<{cells_to_read*3}B', f_image.read(bytes_to_read))

                elif magic == 'Pf' and ext == 'pfm':
                    assert(maxval in [-1.0, 1.0])
                    cells_to_read = width * height
                    bytes_to_read = cells_to_read * 4; assert(bytes_to_read == bytes_remain)
                    contents = unpack(f'{maxval < 0.0 and "<" or ">"}{cells_to_read}f', f_image.read(bytes_to_read)) # swy: handle both big (1.0, '>f') and little-endian (-1.0, '<f') floats; just in case

                else:
                    print(f'[e] Unknown NetPBM format, {magic}: use P5, P6 or Pf.'); exit(1)

        except FileNotFoundError:
            print(f'[!]    no layer_{ground_layer} here, skipping...')


    f.write(pack('<I', 0xFF4AD1A6)) # swy: terrain_magic value
    f.write(pack('<I', 4*4)) # swy: terrain_section_size
    f.write(pack('<I', 0)) # swy: num_layers
    f.write(pack('<I', 0)) # swy: scene_width value
    f.write(pack('<I', 0)) # swy: scene_height value