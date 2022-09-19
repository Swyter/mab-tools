from email import header
from struct import *
import json, os, io

def write_rgltag(str):
    str_enc = str.encode('utf-8'); str_enc_len = len(str_enc)
    f.write(pack('<I', str_enc_len))
    f.write(pack(f'{str_enc_len}s', str_enc))

# swy: source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data
#      from a «scn_advcamp_dale» directory in the same folder as this script
path  = './scn_isengard_center.sco'

# swy: donor SCO with the AI mesh and terrain stuff you want to copy over to the file above;
#      probably the original SCO file, it can't be the same file you want to write to
donor = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_isengard_center_orig.sco'

# swy: target/output SCO file location with the combined data
output = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_isengard_center.sco'

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

        ai_mesh_start_pos = wf.tell()
        ai_mesh_section_size = unpack('<I', wf.read(4))[0]
        wf.seek(ai_mesh_start_pos, io.SEEK_SET)
        f.write(wf.read(ai_mesh_section_size + 4))

    ground = {}
    ground_layer_look_up = {
        'gray_stone.pgm': 0, 'brown_stone.pgm': 1, 'turf.pgm': 2, 'steppe.pgm': 3, 'snow.pgm': 4, 'earth.pgm': 5, 'desert.pgm': 6, 'forest.pgm': 7,
        'pebbles.pgm': 8, 'village.pgm': 9, 'path.pgm': 10, 'ground_elevation.pfm': -7793, 'ground_leveling.ppm': -12565
    }

    last_scene_width = None; last_scene_height = None

    for i, ground_layer in enumerate(ground_layer_look_up):
        layer_name = ground_layer.split('.')[0].lower()
        ext        = ground_layer.split('.')[1].lower()
        ground[layer_name] = []; contents = []

        try:
            with open(f"{scene_file}/layer_{ground_layer}", 'rb') as f_image:
                ascii_header = [] # swy: grab the three ASCII lines that make out the header of these NetPBM formats; strip their carriage returns and split each line into words/tokens

                while True:
                    try:
                        line = f_image.readline().decode('utf-8').replace('\n', '').replace('\r', '').replace('\t', ' ').strip()
                    except UnicodeDecodeError:
                        line = '' # swy: skip weird stuff or characters with wrong encoding

                    # swy: ignore dummy second (comment) lines like the funky '# Created by GIMP version 2.10.32 PNM plug-in'
                    if not line or line[0] == '#' or line.startswith('--') or line[0] not in '0123456789+-.,P':
                        continue

                    ascii_header += [line.split(' ')]

                    if len(ascii_header) >= 3:
                        break

                if len(ascii_header) < 3 or len(ascii_header[1]) < 2 or len(ascii_header[2]) < 1:
                    print(f'[e] invalid {ground_layer} header format; skipping')
                    continue

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
                    contents_orig = []; contents_orig = unpack(f'<{cells_to_read}B', f_image.read(bytes_to_read))

                    # swy: flip or mirror each row from right-to-left to left-to-right
                    for i in range(last_scene_height):
                        contents += contents_orig[i*last_scene_width : (i*last_scene_width) + last_scene_width][::-1]

                elif magic == 'P6' and ext == 'ppm':
                    assert(maxval == 255)
                    cells_to_read = width * height
                    bytes_to_read = cells_to_read * 3; assert(bytes_to_read == bytes_remain)
                    contents_orig = []; contents_orig_rgb_bytes = unpack(f'<{cells_to_read*3}B', f_image.read(bytes_to_read))

                    for i in range(cells_to_read):
                        r = (contents_orig_rgb_bytes[(i * 3) + 0] & 0xff)
                        g = (contents_orig_rgb_bytes[(i * 3) + 1] & 0xff)
                        b = (contents_orig_rgb_bytes[(i * 3) + 2] & 0xff)

                        packed_rgb = (r << (8*1)) | (g << (8*2)) | (b << (8*3))
                        contents_orig.append(packed_rgb)

                    # swy: flip or mirror each row from right-to-left to left-to-right
                    for i in range(last_scene_height):
                        contents += contents_orig[i*last_scene_width : (i*last_scene_width) + last_scene_width][::-1]

                elif magic == 'Pf' and ext == 'pfm':
                    assert(maxval in [-1.0, 1.0])
                    cells_to_read = width * height
                    bytes_to_read = cells_to_read * 4; assert(bytes_to_read == bytes_remain)
                    contents_orig = []; contents_orig = unpack(f'{maxval < 0.0 and "<" or ">"}{cells_to_read}f', f_image.read(bytes_to_read)) # swy: handle both big (1.0, '>f') and little-endian (-1.0, '<f') floats; just in case

                    # swy: reverse the row ordering because the PFM format is from bottom to top, unlike every other NetPBM one, of course :)
                    for i in reversed(range(last_scene_height)):
                        contents += contents_orig[i*last_scene_width : (i*last_scene_width) + last_scene_width][::-1] # swy: grab one "line" worth of data from the farthest point, and add it first; sort them backwards


                else:
                    print(f'[e] Unknown NetPBM format, {magic}: use P5, P6 or Pf.'); exit(1)

                ground[layer_name] = contents

        except FileNotFoundError:
            print(f'[!]    no layer_{ground_layer} here, skipping...')


    f.write(pack('<I', 0xFF4AD1A6)) # swy: terrain_magic value
    terrain_section_size_start_pos = f.tell()
    f.write(pack('<I', 0)) # swy: terrain_section_size, we go back and fix/overwrite this one at the end
    f.write(pack('<I', len(ground_layer_look_up))) # swy: num_layers
    f.write(pack('<I', last_scene_width)) # swy: scene_width value
    f.write(pack('<I', last_scene_height)) # swy: scene_height value

    for i, ground_layer in enumerate(ground_layer_look_up):
        layer_name = ground_layer.split('.')[0].lower()
        layer_index = ground_layer_look_up[ground_layer]
        layer_data_len = len(ground[layer_name])
        layer_has_data = layer_data_len > 0

        f.write(pack('<i', layer_index))    # swy: index (signed)
        write_rgltag(layer_name)            # swy: layer_str
        f.write(pack('<I', layer_has_data)) # swy: enabled

        if not layer_has_data:
            continue

        # swy: a layer is made out of multiple zero-value run-length encoded blocks
        #      this means that long strings of zeros are counted and collapsed into the rle field,
        #      the game will add the same amount of zeros later, padding/inflating those empty zones while loading.
        #      funnily enough the game doesn't detect if creating/splitting into a new block has more overhead/wastes more bytes
        #      than just adding a few zeros like normal, if the string is short enough. this happens a lot ¯\_(ツ)_/¯

        first_zero = None
        last_zero = None
        in_a_string_of_zeroes = False

        if layer_name == 'ground_elevation':
            zero = False # swy: don't compress the floating point heightmap, use a single block
        elif layer_name == 'ground_leveling':
            zero = 0xFFFFFF00 # swy: opaque white
        else:
            zero = 0 # swy: everything else is grayscale; pure black

        block_begins_at = 0

        for i in range(layer_data_len):
            is_zero = (ground[layer_name][i] == zero)

            if block_begins_at == i and is_zero and not in_a_string_of_zeroes:
                in_a_string_of_zeroes = True
                first_zero = i
            elif not is_zero and in_a_string_of_zeroes:
                last_zero = i - 1
                in_a_string_of_zeroes = False

            elif not is_zero and not in_a_string_of_zeroes:
                continue
            elif (is_zero and not in_a_string_of_zeroes) or (i >= layer_data_len):
                f.write(pack('<I', last_zero - first_zero)) # swy: rle
                f.write(pack('<I', len(ground[layer_name]))) # swy: elem_count

                if layer_name == 'ground_elevation':
                    f.write(pack(f'<{len(ground[layer_name])}f', *ground[layer_name]))
                elif layer_name == 'ground_leveling':
                    f.write(pack(f'>{len(ground[layer_name])}I', *ground[layer_name]))
                else:
                    f.write(pack(f'<{len(ground[layer_name])}B', *ground[layer_name]))



    # swy: fill terrain_section_size afterwards, once we know how bit the section really is
    terrain_section_end_pos = f.tell()
    f.seek(terrain_section_size_start_pos, io.SEEK_SET)
    f.write(pack('<I', terrain_section_end_pos - (terrain_section_size_start_pos + 4)))