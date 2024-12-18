import pathlib
from struct import *
import json, os, io
import sys; from sys import exit
import argparse

# swy: source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data
#      from a «scn_advcamp_dale» directory in the same folder as this script
path  = './scn_caras_galadhon_siege_orig.sco'

# swy: donor SCO with the AI mesh you want to copy over to the file above;
#      probably the original SCO file, it can't be the same file you want to write to
donor = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_caras_galadhon_siege_orig.sco'

# swy: target/output SCO file location with the combined/repacked data
output = 'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_caras_galadhon_siege.sco'


# swy: copy the AI mesh and ground stuff over from the other SCO file
def write_over_from(output_f, donor, write_mission_objects = False, write_ai_mesh = False, write_terrain = False):
    if not 'donor_file_data' in donor:
        print(f"[e] the binary data from the donor is missing; darn..."); exit(69)

    donor_file_data = donor['donor_file_data']
    with io.BytesIO(donor_file_data) as donor_f:
        donor_f.seek(0, os.SEEK_END); end_offset = donor_f.tell(); donor_f.seek(0, os.SEEK_SET) # swy: grab how big the file is in bytes

        magic = unpack('<I', donor_f.read(4))[0]; assert magic == 0xFFFFFD33, f"Unsupported header magic value ({magic:x}); older SCO versions with just scene objects are unsupported for now here. Re-save the donor file in the in-game editor to update the version and being able to unpack it."
        versi = unpack('<I', donor_f.read(4))[0]; assert versi in (3, 4),     f"Unsupported SCO version format ({versi:x}), re-save the donor file in the in-game editor to update the version and be able to unpack it."

        mission_obj_start_pos = donor_f.tell()

        # swy: walk over all the mission object/scene prop entries;
        #      due to the text/strings each of them takes a variable amount of bytes
        object_count = unpack('<I', donor_f.read(4))[0]

        for i in range(object_count):
            donor_f.seek(4 + 4 + 4 + (4*3) + (4*3) + (4*3) + (4*3), os.SEEK_CUR);
            rgltag_len = unpack('<I', donor_f.read(4))[0]
            donor_f.seek(rgltag_len + 4 + 4 + (4*3), os.SEEK_CUR);

        # swy: we've reached the end of the mission object section; the AI mesh chunk starts here.
        #      copy and paste the rest of the file
        print(f"[i] AI mesh of donor starts at offset {hex(donor_f.tell())}; copying from here onwards")
        
        ai_mesh_start_pos = donor_f.tell()

        if donor_f.tell() == end_offset: # swy: if we are already at the file ending just silently ignore any further sections, we'll copy zero bytes
            ai_mesh_section_size = 0
        else:
            ai_mesh_section_size = unpack('<I', donor_f.read(4))[0] + 4 # swy: the section size does not include the size field itself

        mission_obj_section_size = ai_mesh_start_pos - mission_obj_start_pos
        terrain_start_pos        = ai_mesh_start_pos + ai_mesh_section_size

        if (write_mission_objects):
            donor_f.seek(mission_obj_start_pos, io.SEEK_SET)
            output_f.write(donor_f.read(mission_obj_section_size))

        if (write_ai_mesh):
            donor_f.seek(ai_mesh_start_pos, io.SEEK_SET)
            output_f.write(donor_f.read(ai_mesh_section_size))

        if (write_terrain):
            donor_f.seek(terrain_start_pos, io.SEEK_SET)
            output_f.write(donor_f.read())

def copy_over_instead_of_repacking(option):
    return option not in ['keep', 'empty'] and 'donor_file_data' in option

def sco_repack(input_folder, output_sco, mission_objects_from = False, ai_mesh_from = False, terrain_from = False):
    def write_rgltag(str):
        str_enc = str.encode('utf-8'); str_enc_len = len(str_enc)
        f.write(pack('<I', str_enc_len))
        f.write(pack(f'{str_enc_len}s', str_enc))

    scene_file = input_folder + '.sco'
    donor_file = donor.replace('\\', '/').split('/')[-1].split('.')[0]

    if not output_sco:
        output_sco = f'{pathlib.Path(input_folder)}.sco'

    if not os.path.isdir(input_folder):
        print(f"[e] the unpacked «{input_folder}» SCO folder doesn't seem to exist")
        exit(1)

    print(f'[i] repacking the data from the «{input_folder}» folder\n' + \
          f'                           into «{output_sco}»')

    try:
        with open(output_sco, mode='wb') as f:
            f.write(pack('<I', 0xFFFFFD33)) # swy: magic value
            f.write(pack('<I', 4)) # swy: SCO file version
            
            if copy_over_instead_of_repacking(mission_objects_from):
                print(f"[>] copying over the mission object section from donor «{mission_objects_from['donor_filename']}» file")
                write_over_from(f, mission_objects_from, write_mission_objects=True)
            else:
                mission_objects = []

                if not mission_objects_from == 'empty':
                    try:
                        with open(f"{input_folder}/mission_objects.json", encoding='utf-8-sig') as f_json:
                            mission_objects = json.load(f_json)
                    except OSError as e:
                        print(f"[!] skipping mission objects/scene props: {e}", file=sys.stderr)

                object_count = len(mission_objects)
                f.write(pack('<I', object_count))

                print(f"[i] writing {object_count} mission objects from the JSON file\n")

                object_type = {'prop': 0, 'entry': 1, 'item': 2, 'unused': 3, 'plant': 4, 'passage': 5}

                last_garbage_val = 0x1337 # swy: we'll use this if the JSON doesn't have a custom garbage value set

                for i, object in enumerate(mission_objects):
                    assert 'type' in object and object['type'] in object_type, f'the prop type for object {i} needs to be either «prop», «entry», «item», «unused», «plant» or «passage»'

                    if 'garbage' in object and i == 0: # swy: if the first entry has a custom garbage value, reuse it for everyone else, the newer unpacker only writes them if they are different from the first one
                        last_garbage_val = int(object['garbage'], 16)

                    f.write(pack('<I',               'type' in object and object_type[object['type']]  or object_type['prop']))
                    f.write(pack('<I',                 'id' in object and object['id']                 or 0                  ))
                    f.write(pack('<I',            'garbage' in object and int(object['garbage'], 16)   or last_garbage_val   ))
                    f.write(pack('<3f', *('rotation_matrix' in object and object['rotation_matrix'][0] or [1, 0, 0])         ))
                    f.write(pack('<3f', *('rotation_matrix' in object and object['rotation_matrix'][1] or [0, 1, 0])         ))
                    f.write(pack('<3f', *('rotation_matrix' in object and object['rotation_matrix'][2] or [0, 0, 1])         ))
                    f.write(pack('<3f', *(            'pos' in object and object['pos']                or [0, 0, 0])         ))
                    write_rgltag(                     'str' in object and object['str']                or ''                  )

                    f.write(pack('<I',           'entry_no' in object and object['entry_no']           or  0                 ))
                    f.write(pack('<I',      'menu_entry_no' in object and object['menu_entry_no']      or  0                 ))
                    f.write(pack('<3f', *(          'scale' in object and object["scale"]              or [1, 1, 1])         ))


            if copy_over_instead_of_repacking(ai_mesh_from):
                print(f"[>] copying over the AI mesh section from donor «{ai_mesh_from['donor_filename']}» file")
                write_over_from(f, ai_mesh_from, write_ai_mesh=True)

            else:
                # swy: convert the AI mesh section from a Wavefront OBJ file and
                #      regenerate the extra face <-> edge <-> vertex linked data
                vertices = []; faces = []    

                def getleftpart(line, token):
                        pos = line.find(token)
                        if pos != -1:
                            return line[:pos]
                        else:
                            return line
                if not ai_mesh_from == 'empty':
                    try:
                        with open(f"{input_folder}/ai_mesh.obj", encoding='utf-8-sig') as f_obj:
                            for i, line in enumerate(f_obj):
                                # swy: strip anything to the right of a line comment marker
                                line = getleftpart(line, '#' )
                                line = line.split()

                                if not line or len(line) < 4:
                                    continue

                                if line[0] == 'v':
                                    vertices.append([float(token)  for token in line[1:]])
                                elif line[0] == 'f':
                                    faces.append([int(getleftpart(token, '/')) - 1  for token in line[1:]]) # swy: convert from Wavefront OBJs start-at-1 to M&B's start-at-0 vertex indices
                    except OSError as e:
                        print(f"[!] skipping AI mesh: {e}", file=sys.stderr)

                # swy: crummy way of regenerating an acceptable edge-face data,
                #      this is a bit like some halfedge data structure for A* traversal

                print("[i] recomputing edge data from the face-vertex mapping in the Wavefront OBJ file")
                faces_in_edge = {} # swy: face idx that this edge is part of
                faces_in_edge_idx = {}
                edges_in_face = {} # swy: edge members of a face
                for i, elem in enumerate(faces):
                    face_data = elem
                    edges_in_face[i] = []
                    for j, elem in enumerate(face_data):
                        a = face_data[j]; b = face_data[((j+1) % len(face_data))]
                        
                        if f'{a}-{b}' in faces_in_edge:
                            print(f'[e] {a}-{b} detected non-manifold edge at face index {i} -- between {repr(vertices[a])} and {repr(vertices[b])}\n    This means that some of your vertices/edges are part of more than two faces, please fix this in the original 3D mesh. This may cause issues, ignoring.')
                            #exit(4)
                        if f'{b}-{a}' in faces_in_edge:
                            #print(f'{b}-{a} already exists (r) -- {faces_in_edge[f"{b}-{a}"]} {i}')
                            faces_in_edge[f'{b}-{a}'].append(i)
                            edges_in_face[i].append(faces_in_edge_idx[f'{b}-{a}'])
                            continue

                        #print(f'new {a}-{b} -- {i}')
                        faces_in_edge_idx[f'{a}-{b}'] = len(faces_in_edge)
                        faces_in_edge[f'{a}-{b}'] = [i]
                        edges_in_face[i].append(faces_in_edge_idx[f'{a}-{b}'])

                print(f"[i] done; got {len(vertices)} vertices, {len(faces_in_edge)} valid edges and {len(faces)} faces in this AI mesh")

                ai_mesh_section_size_start_pos = f.tell()
                f.write(pack('<I', 0)) # ai_mesh_section_size, we go back and fix/overwrite this one at the end

                f.write(pack('<I', len(vertices))) # vertex_count
                for vtx in vertices:
                    #y = vtx[1] # swy: make it upright when the model Y-is-up
                    #z = vtx[2]
                    #vtx[1] = z
                    #vtx[2] = y
                    f.write(pack('<3f', *vtx[:3]))

                f.write(pack('<I', len(faces_in_edge))) # edge_count
                for edg in faces_in_edge:
                    a, b = (int(token)  for token in edg.split('-'))

                    data = faces_in_edge[edg]
                    face_count = len(data)

                    # swy: if this edge is only part of a single poly pad out the
                    #      remaining field with this dummy value the game uses
                    if face_count < 2:
                        data.append(-10000)

                    f.write(pack('<I', face_count)) # face_count
                    f.write(pack('<I', a)) # vtx_a
                    f.write(pack('<I', b)) # vtx_b
                    f.write(pack('<I', data[0])) # face_idx_r
                    f.write(pack('<i', data[1])) # face_idx_l


                f.write(pack('<I', len(faces))) # face_count
                for i, fcs in enumerate(faces):
                    f.write(pack('<I', len(fcs))) # vtx_and_edge_count
                    f.write(pack(f'<{len(fcs)}I', *fcs)) # vertices
                    f.write(pack(f'<{len(fcs)}I', *edges_in_face[i])) # edges
                    f.write(pack('<I', 0)) # has_more

                # swy: fill ai_mesh_section_size afterwards, once we know how big the section really is
                ai_mesh_section_end_pos = f.tell()
                f.seek(ai_mesh_section_size_start_pos, io.SEEK_SET)
                f.write(pack('<I', ai_mesh_section_end_pos - (ai_mesh_section_size_start_pos + 4)))
                f.seek(ai_mesh_section_end_pos, io.SEEK_SET)
                print(f"[i] done writing the AI mesh data\n")


            if copy_over_instead_of_repacking(terrain_from):
                print(f"[>] copying over the terrain section from donor «{terrain_from['donor_filename']}» file")
                write_over_from(f, terrain_from, write_terrain=True)

            else:
                # swy: convert the individual heightmap/RGB paint/material image files into actual ground/terrain
                #      layer blocks. these are optionally RLE-encoded using a matching algorithm
                #      to get the same file back for the same unmodified exported data.
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

                    # swy: as a bit of retro-compatible usability improvement, accept «layer_ground_tinting.ppm» as a stand-in filename for TaleWorld's «layer_ground_leveling.ppm»
                    #      which as a layer name sucks and is practically misleading, as people confuse this RGB color tinting data with the «ground_elevation» gray heightmap
                    if ground_layer == 'ground_leveling.ppm' and os.path.exists(f"{input_folder}/layer_ground_tinting.ppm"):
                        ground_layer = 'ground_tinting.ppm'
                    
                    if not terrain_from == 'empty':
                        try:
                            with open(f"{input_folder}/layer_{ground_layer}", 'rb') as f_image:
                                ascii_header = [] # swy: grab the three ASCII lines that make out the header of these NetPBM formats; strip their carriage returns and split each line into words/tokens
                                ascii_header_flattened = []
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
                                    if len(ascii_header_flattened) >= 4:
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
                                    assert maxval == 255
                                    cells_to_read = width * height
                                    bytes_to_read = cells_to_read * 1; assert(cells_to_read == bytes_remain)
                                    contents_orig = []; contents_orig = unpack(f'<{cells_to_read}B', f_image.read(bytes_to_read))

                                    # swy: flip or mirror each row from right-to-left to left-to-right
                                    for i in range(last_scene_height):
                                        contents += contents_orig[i*last_scene_width : (i*last_scene_width) + last_scene_width][::-1]

                                elif magic == 'P6' and ext == 'ppm':
                                    assert maxval == 255
                                    cells_to_read = width * height
                                    bytes_to_read = cells_to_read * 3; assert bytes_to_read == bytes_remain
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
                                    assert maxval in [-1.0, 1.0]
                                    cells_to_read = width * height
                                    bytes_to_read = cells_to_read * 4; assert bytes_to_read == bytes_remain
                                    contents_orig = []; contents_orig = unpack(f'{maxval < 0.0 and "<" or ">"}{cells_to_read}f', f_image.read(bytes_to_read)) # swy: handle both big (1.0, '>f') and little-endian (-1.0, '<f') floats; just in case

                                    # swy: reverse the row ordering because the PFM format is from bottom to top, unlike every other NetPBM one, of course :)
                                    for i in reversed(range(last_scene_height)):
                                        contents += contents_orig[i*last_scene_width : (i*last_scene_width) + last_scene_width][::-1] # swy: grab one "line" worth of data from the farthest point, and add it first; sort them backwards


                                else:
                                    print(f'[e] Unknown NetPBM format, {magic}: use P5, P6 or Pf.'); exit(1)

                                ground[layer_name] = contents

                        except FileNotFoundError:
                            print(f'[!]    no layer_{ground_layer} here, skipping...')

                # swy: ensure we at least set the scene dimensions to zero if we're kind of writing an empty section
                last_scene_width  = last_scene_width  and last_scene_width  or 0
                last_scene_height = last_scene_height and last_scene_height or 0

                if last_scene_width == 0 and last_scene_height == 0:
                    print(f'[i] no need to write a terrain block when this looks like an interior scene; no layers. done!')
                    exit(0)

                f.write(pack('<I', 0xFF4AD1A6)) # swy: terrain_magic value
                terrain_section_size_start_pos = f.tell()
                f.write(pack('<I', 0)) # swy: terrain_section_size, we go back and fix/overwrite this one at the end
                f.write(pack('<I', len(ground_layer_look_up))) # swy: num_layers
                f.write(pack('<I', last_scene_width)) # swy: scene_width value
                f.write(pack('<I', last_scene_height)) # swy: scene_height value

                print(f'\n[i] writing a {last_scene_width} x {last_scene_height} terrain block')

                for i, ground_layer in enumerate(ground_layer_look_up):
                    layer_name = ground_layer.split('.')[0].lower()
                    layer_data = ground[layer_name]
                    layer_index = ground_layer_look_up[ground_layer]
                    layer_data_len = len(layer_data)
                    layer_last_idx = layer_data_len - 1
                    layer_has_data = layer_data_len > 0

                    print(f'[-] compressing and writing layer {layer_name}...')

                    f.write(pack('<i', layer_index))    # swy: index (signed)
                    write_rgltag(layer_name)            # swy: layer_str; this seems unused by the game, only pays attention to the layer ID to get its meaning
                    f.write(pack('<I', layer_has_data)) # swy: enabled; or not if the layer is empty

                    if not layer_has_data:
                        continue

                    # swy: a layer is made out of multiple zero-value run-length encoded blocks
                    #      this means that long strings of zeros are counted and collapsed into the rle field,
                    #      the game will add the same amount of zeros later, padding/inflating those empty zones while loading.
                    #      funnily enough the game doesn't detect if creating/splitting into a new block has more overhead/wastes more bytes
                    #      than just adding a few zeros like normal, if the string is short enough. this happens a lot ¯\_(ツ)_/¯
                    first_zero = None; last_zero = None

                    if layer_name == 'ground_elevation':
                        zero = False # swy: don't compress the floating point heightmap, use a single block
                    elif layer_name == 'ground_leveling':
                        zero = 0xFFFFFF00 # swy: opaque white
                    else:
                        zero = 0 # swy: everything else is grayscale; pure black

                    write_block = False

                    for i in range(layer_data_len):
                        im_zero = layer_data[i] == zero

                        prev_exists = (i - 1) >= 0
                        next_exists = (i + 1) <= layer_last_idx

                        prev_is_zero = prev_exists and (layer_data[i - 1] == zero) or False
                        next_is_zero = next_exists and (layer_data[i + 1] == zero) or False

                        if im_zero and not prev_exists: # swy: we're the first element and the first zero
                            first_zero = i

                        if im_zero and prev_exists and not prev_is_zero: # swy: we're the first zero after a non-zero block
                            first_zero = i

                        if im_zero and next_exists and next_is_zero: # swy: e.g.  00 [00] 00 FF
                            continue                                 #            ----------____  we're here, skip until the last zero

                        if im_zero and next_exists and not next_is_zero: # swy: e.g.  00 FF FF FF [00] FF
                            last_zero = i                                #            --________/  || we're here, write the first zero as a zero-count and write the rest. we'll head the following block
                            
                        if im_zero and not next_exists: # swy: e.g.  00 [00]     |    FF [00]
                            write_block = True          #            ------/     |    _/       if we are the last element of the thing
                            last_zero = i

                        if not next_exists: # we're the last element, zero or not we'll need to end and save
                            write_block = True

                        if not im_zero and next_exists and next_is_zero: # swy: we're the last non-zero and end of the block
                            write_block = True

                        if write_block:
                            if last_zero == i:
                                data_slice = None
                            if last_zero is None or first_zero is None: # swy: the whole block started with a non-zero and is non-zeroes all the way; no preceding zeroes at all; grab the whole chunk
                                data_slice = layer_data[0: i + 1]
                            else:
                                data_slice = layer_data[last_zero + 1: i + 1]
                                
                            if last_zero is None or first_zero is None:
                                amount_of_preceding_zeros = 0
                            else:
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
                            first_zero = None; last_zero = None
                            write_block = False

                # swy: fill terrain_section_size afterwards, once we know how big the section really is
                terrain_section_end_pos = f.tell()
                f.seek(terrain_section_size_start_pos, io.SEEK_SET)
                f.write(pack('<I', terrain_section_end_pos - (terrain_section_size_start_pos + 4)))

            print(f'[i] done!')
    except OSError as e:
        print(f"[e] couldn't open the target SCO file: {e}", file=sys.stderr)

if __name__ == "__main__":
    # swy: add some helpful commands and their documentation
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description='Repacks and intermixes Mount&Blade SceneObj files. Created by Swyter in 2022.',
                                     epilog=r'''
| Quick-ish help and how to restore already-unpacked versions of scene objects /
\_____________________________________________________________________________/

This is very powerful and allows you to repack a file partially, sourcing each of the three blocks/parts of an SCO file (mission objects/AI mesh/terrain-ground layers) from different SCO files.

Quick examples:
   mab_sco_repack ./scn_advcamp_dale                                                # this will generate some «scn_advcamp_dale.sco», it can be used for drag-and-dropping the folder directly over this tool.
   mab_sco_repack ./scn_advcamp_dale -o '../SceneObj/scn_advcamp_dale_repacked.sco' # save our repacked scene in a specific place or set a custom filename.
   mab_sco_repack ./scn_advcamp_dale -o scn_out.sco --aimesh keep                   # this overwrites scn_out.sco with the repacked data for props and terrain but leaves the existing AI mesh section alone and untouched.
   mab_sco_repack ./scn_advcamp_dale -o scn_out.sco -te scn_a.sco -ai scn_b.sco     # this combines the unpacked props with a copy of scn_a.sco's terrain and scn_b.sco's AI mesh.
   mab_sco_repack . -o scn_existing.sco -mo keep  -ai keep  -te keep                # this does nothing, as long as scn_existing.sco exists, all three sections are intact, the input goes unused.
   mab_sco_repack . -o scn_existing.sco -mo empty -ai keep  -te keep                # clears all the existing props in the output scene, but keeps the rest as-is; we're no repacking anything.
   mab_sco_repack . -o scn_blank_sc.sco -mo empty -ai empty -te empty               # create a completely empty SCO file from scratch, the first argument doesn't matter.
''')
    parser.add_argument('input', metavar='<unpacked-sco-folder>', help='the source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data from a «scn_advcamp_dale» directory in the same folder as this script')

    parser.add_argument('-o', '--output', metavar='<path-to-sco>', dest='output', required=False,
                        help='filename or path where to write the resulting .SCO; if not specified it will be saved in the current folder with the same name as the input folder plus the «.sco» extension, overwriting any files.')

    parser.add_argument('-mo', '--missionobjects', dest='sect_mission_objects', default='repack', metavar='<option>', required=False)
    parser.add_argument('-ai', '--aimesh',         dest='sect_ai_mesh',         default='repack', metavar='<option>', required=False)
    parser.add_argument('-te', '--terrain',        dest='sect_terrain',         default='repack', metavar='<option>', required=False,
                        help='by default the <option> is «repack», it will convert back the unpacked data in the folder you provide. You can use «keep» to retain the original data in the target SCO if it exists and avoid modifying that part, which is also faster than repacking and lossless, you can use «empty» or «blank» to completely remove any data previously that section, or, finally; you can provide a path to a different donor .sco file to copy that section over directly into the target .sco, losslessly replacing a section/block without having to unpack it first or merge it manually.')

    args = parser.parse_args() # args = parser.parse_args('/home/swyter/Descargas/scn_village_57 -o scn_village_repacked.sco'.split()) #'C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_lebennin_coast_3 -mo C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_lebennin_coast_3_orig.sco'.split())
    #args = parser.parse_args(["/home/swyter/.local/share/Steam/steamapps/common/MountBlade Warband/Modules/TLD/SceneObj_copy_sco/scn_gundabad_mirkwood_outpost", "-mo", "repack", "-ai", "/home/swyter/.local/share/Steam/steamapps/common/MountBlade Warband/Modules/TLD/SceneObj_copy_sco/scn_gundabad_mirkwood_outpost.sco", "-te", "repack", "-o", "/home/swyter/github/mab-tools/scn_gundabad_mirkwood_outpost_out.sco"])
    #args = parser.parse_args(["/home/swyter/.local/share/Steam/steamapps/common/MountBlade Warband/Modules/TLD/SceneObj_copy_sco/scn_scout_camp_mirk_evil_big", "-mo", "repack", "-ai", "/home/swyter/.local/share/Steam/steamapps/common/MountBlade Warband/Modules/TLD/SceneObj_copy_sco/scn_scout_camp_mirk_evil_big.sco", "-te", "repack", "-o", "/home/swyter/.local/share/Steam/steamapps/common/MountBlade Warband/Modules/TLD/SceneObj_copy_sco/scn_scout_camp_mirk_evil_big_out.sco"])

    if args.sect_mission_objects == args.sect_ai_mesh == args.sect_terrain == 'keep':
        print(f"[i] we were asked to keep all the three sections of «{args.output}» as-is. so we don't need to touch the file. ¯\_(ツ)_/¯")
        exit(0)

    # swy: if we are using donor files, especially with the 'keep' option where we are essentially overwriting the file itself,
    #      we need to read the entire contents just moments before. we can't read the previous data in the middle.
    def process(option):
        if option in ['empty', 'blank']:
            return 'empty'

        if option == 'repack':
            return option

        # swy: use the output file as donor file, this is just quicker to type
        if option == 'keep':
            option = args.output; assert args.output != None, 'To use the «keep» option you need to also specify some already-existing output .sco filename to get the partial data from. Use the --output <name> option.'

        try:
            with open(option, mode='rb') as donor_f:
                file_data = donor_f.read()
                print(f"[i] reading the donor file: {option} ({donor_f.tell() // 1024} KiB)"); write_over_from(None, {'donor_file_data': file_data}) # swy: call the write_over() function here with a dummy output to validate that the donor file is correct before replacing/overwriting it
                return {'donor_file_data': file_data, 'donor_filename': option}
        except OSError as e:
            print(f"[e] couldn't open the donor file: {e}", file=sys.stderr)
            exit(1)

    args.sect_mission_objects = process(args.sect_mission_objects)
    args.sect_ai_mesh         = process(args.sect_ai_mesh)
    args.sect_terrain         = process(args.sect_terrain)

    sco_repack(
        args.input, args.output, mission_objects_from=args.sect_mission_objects,
                                         ai_mesh_from=args.sect_ai_mesh,
                                         terrain_from=args.sect_terrain
    )

    #os.system("md5sum /home/swyter/.local/share/Steam/steamapps/common/MountBlade\ Warband/Modules/TLD/SceneObj_copy_sco/scn_gundabad_mirkwood_outpost.sco /home/swyter/github/mab-tools/scn_gundabad_mirkwood_outpost_out.sco")