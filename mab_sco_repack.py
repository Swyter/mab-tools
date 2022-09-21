from email import header
from struct import *
import json, os, io

def write_rgltag(str):
    str_enc = str.encode('utf-8'); str_enc_len = len(str_enc)
    f.write(pack('<I', str_enc_len))
    f.write(pack(f'{str_enc_len}s', str_enc))

# swy: source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data
#      from a «scn_advcamp_dale» directory in the same folder as this script
path  = './scn_caras_galadhon_siege.sco'

# swy: donor SCO with the AI mesh you want to copy over to the file above;
#      probably the original SCO file, it can't be the same file you want to write to
donor = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_caras_galadhon_siege_orig.sco'

# swy: target/output SCO file location with the combined/repacked data
output = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_caras_galadhon_siege.sco'

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

    vertices = []; faces = []    

    with open(f"{scene_file}/ai_mesh.obj") as f_obj:
        for line in f_obj:
            # swy: strip anything to the right of a line comment marker
            line = line[:line.find('//')]
            line = line[:line.find('#' )]
            line = line.split()
            print(line)

            if not line or len(line) < 4:
                continue

            if line[0] == 'v':
                vertices.append([float(token) for token in line[1:]])
            elif line[0] == 'f':
                faces.append([int(token) - 1 for token in line[1:]]) # swy: convert from Wavefront OBJs start-at-1 to M&B's start-at-0 vertex indices

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
                        header_end_byte_offset = f_image.tell()
                    except UnicodeDecodeError:
                        line = '' # swy: skip weird stuff or characters with wrong encoding
                        break

                    # swy: ignore dummy second (comment) lines like the funky '# Created by GIMP version 2.10.32 PNM plug-in'
                    if not line or line[0] == '#' or line.startswith('--') or line[0] not in '0123456789+-.,P':
                        continue

                    ascii_header += [line.split(' ')]
                    ascii_header_flattened = [value.strip() for sub_list in ascii_header for value in sub_list if value != ''] # swy: photoshop exports width and height in different lines, and maxval in the fourth line, don't depend on the line position, only the 'token' order matters

                    # swy: the format only has four tokens, that can be part of different lines or just separated by whitespace; this format is way too lax
                    if len(ascii_header_flattened) > 4:
                        break

                if ascii_header_flattened[0][0] != 'P':
                    print(f'[e] invalid {ground_layer} header format; skipping')
                    continue

                magic  =       ascii_header_flattened[0]  # line 1, magic value
                width  =   int(ascii_header_flattened[1]) # line 2, width and height
                height =   int(ascii_header_flattened[2])
                maxval = float(ascii_header_flattened[3]) # line 3, extra thing

                # swy: grab how far away we are from the start after reading the ASCII part, use it to compute how many bytes the rest of the data takes
                f_image.seek(0, io.SEEK_END); bytes_remain = f_image.tell() - header_end_byte_offset; f_image.seek(header_end_byte_offset)

                if not last_scene_width:
                    last_scene_width = width
                else:
                    if last_scene_width != width:
                        print('[e] the width of all layer images must match'); exit(2)
                        
                if not last_scene_height:
                    last_scene_height = height
                else:
                    if last_scene_height != height:
                        print('[e] the height of all layer images must match'); exit(2)

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
        layer_data = ground[layer_name]
        layer_index = ground_layer_look_up[ground_layer]
        layer_data_len = len(layer_data)
        layer_last_idx = layer_data_len - 1
        layer_has_data = layer_data_len > 0

        print(f'[-] compressing and writing layer {layer_name}...')

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
        write_block = False

        for i in range(layer_data_len):
            is_zero = (layer_data[i] == zero)

            if block_begins_at == i and is_zero and not in_a_string_of_zeroes: # swy: if our block starts with zeroes, note it down
                in_a_string_of_zeroes = True
                first_zero = i
            elif not is_zero and in_a_string_of_zeroes: # swy: if our block started and continued being all zeroes, note down where it ended
                last_zero = i - 1
                in_a_string_of_zeroes = False
            elif not is_zero and not first_zero and not last_zero: # swy: if the block didn't start with zeroes at all, mark the variables in a way that amount_of_preceding_zeros gets set to 0
                first_zero =  0
                last_zero  = -1

            # swy: write the final block if we've reached the end
            if i >= layer_last_idx:
                write_block = True

                # swy: mark us (the last element in the array) as the last zero, the condition above only detects the 
                #      last zero in retrospective by looking at the following (non-zero) entry
                if is_zero and in_a_string_of_zeroes:
                    last_zero = i
                    in_a_string_of_zeroes = False

            
            # swy: write and then start a new block if we find zeroes after a non-zero block
            if (is_zero and not in_a_string_of_zeroes and last_zero):
                write_block = True

            if write_block:
                # swy: fix ground_elevation being off by one when there are no preceding zeroes
                #      we are at the end of the line, writing the block due to being the last idx
                #      and we want a slice as big as the entire data array (i + 1)
                last_slice_idx = last_zero == -1 and i + 1 or i

                data_slice = layer_data[last_zero + 1: last_slice_idx]
                amount_of_preceding_zeros = ((last_zero + 1) - (first_zero + 1)) + 1

                if (amount_of_preceding_zeros < 0):
                    print("[e] the amount of preceding zeroes can't be negative")

                f.write(pack('<I', amount_of_preceding_zeros)) # swy: rle

                if data_slice:
                    f.write(pack('<I', len(data_slice))) # swy: elem_count

                    if   layer_name == 'ground_elevation':
                        f.write(pack(f'<{len(data_slice)}f', *data_slice))
                    elif layer_name == 'ground_leveling':
                        f.write(pack(f'>{len(data_slice)}I', *data_slice))
                    else:
                        f.write(pack(f'<{len(data_slice)}B', *data_slice))

                # swy: reset the state machine back, a new block may start at this (i) element
                block_begins_at = i
                first_zero = None
                last_zero = None
                in_a_string_of_zeroes = False
                write_block = False

                # swy: there is no goto in Python to rewind this loop and parse a possible first zero in the new block,
                #      so duplicate the condition above that we wouldn't ever reach and call it a day
                if is_zero:
                    in_a_string_of_zeroes = True
                    first_zero = i

    # swy: fill terrain_section_size afterwards, once we know how bit the section really is
    terrain_section_end_pos = f.tell()
    f.seek(terrain_section_size_start_pos, io.SEEK_SET)
    f.write(pack('<I', terrain_section_end_pos - (terrain_section_size_start_pos + 4)))

    print(f'[i] done!')