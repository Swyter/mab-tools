import argparse
import datetime
import pathlib
import re
from struct import *
import json, os
import sys
import io
def sco_unpack(input_sco_path, output_folder, skip_mission_objects = False, skip_ai_mesh = False, skip_terrain = False):
    def read_rgltag():
        size = unpack('<I', f.read(4))[0]
        if not size:
            return ''

        str = unpack(f'{size}s', f.read(size))[0].decode('utf-8')
        return str

    if not input_sco_path:
        print('[e] you need to specify some scn_*.sco file to unpack'); exit(1)

    scene_file = input_sco_path.replace('\\', '/').split('/')[-1].split('.')[0]

    if not output_folder:
        output_folder = f'{pathlib.Path(input_sco_path).parent}/{scene_file}/'

    print(f'[i] unpacking «{input_sco_path}» into «{output_folder}»')

    os.makedirs(output_folder, exist_ok=True) # https://stackoverflow.com/a/41959938/674685

    try:
        with open(input_sco_path, mode='rb') as f:
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

                #print(i, object_type[type], str, entry_no)
                mission_objects.append(object)

            if skip_mission_objects:
                print(f'[i] skipping mission objects section')
            else:
                print(f'[>] unpacking {object_count} mission objects into a JSON file')

                js = json.dumps(obj=mission_objects, indent=2, ensure_ascii=False)
                js = re.sub(r'\[\n\s+(.+)\n\s+(.+)\n\s+(.+)\n\s+(.+)\]', r'[\1 \2 \3]', js) # swy: quick and dirty way of making the arrays of numbers how in a single line, for a more compact look

                try:
                    with open(f"{output_folder}/mission_objects.json", mode='w') as fw:
                        fw.write(js)
                except OSError as e:
                    print(f"[e] couldn't open the JSON file: {e}", file=sys.stderr)
                
            # swy: read the AI mesh data structures
            ai_mesh = {'vertices': [], 'edges': [], 'faces': []}

            ai_mesh_section_size = unpack('<I', f.read(4))[0]
            vertex_count = unpack('<I', f.read(4))[0]

            for i in range(vertex_count):
                vertex = unpack('<3f', f.read(4 * 3))
                ai_mesh['vertices'].append(vertex)

            edge_count = unpack('<I', f.read(4))[0]

            for i in range(edge_count):
                edge = unpack('<5i', f.read(4 * 5))
                ai_mesh['edges'].append(edge)

            face_count = unpack('<I', f.read(4))[0]

            for i in range(face_count):
                vtx_and_edge_count = unpack('<I', f.read(4))[0]
                idx_vertices       = unpack(f'<{vtx_and_edge_count}I', f.read(4 * vtx_and_edge_count))
                idx_edges          = unpack(f'<{vtx_and_edge_count}I', f.read(4 * vtx_and_edge_count))
                has_more           = unpack('<I', f.read(4))[0]

                ai_mesh_id = has_more and unpack('<I', f.read(4))[0] or 0

                ai_mesh['faces'].append({'vtx_and_edge_count': vtx_and_edge_count, 'idx_vertices': idx_vertices, 'idx_edges': idx_edges, 'has_more': has_more, 'ai_mesh_id': ai_mesh_id})

            # swy: try to recompute the edge data for debugging purposes to see how well it matches the original values
        #    edgelist = {}
        #    edgelist_idx = {}
        #    facelist = {}
        #    for i, elem in enumerate(ai_mesh['faces']):
        #        face_data = elem['face']
        #        facelist[i] = []
        #        for j, elem in enumerate(face_data):
        #            a = face_data[j]; b = face_data[((j+1) % len(face_data))]
        #            
        #            if f'{a}-{b}' in edgelist:
        #                print(f'{a}-{b} detected non-manifold edge at face index {i} -- between {repr(ai_mesh["vertices"][a])} and {repr(ai_mesh["vertices"][b])}')
        #                exit(4)
        #            if f'{b}-{a}' in edgelist:
        #                print(f'{b}-{a} already exists (r) -- {edgelist[f"{b}-{a}"]} {i}')
        #                edgelist[f'{b}-{a}'].append(i)
        #                facelist[i].append(edgelist_idx[f'{b}-{a}'])
        #                continue
        #
        #            print(f'new {a}-{b} -- {i}')
        #            edgelist_idx[f'{a}-{b}'] = len(edgelist)
        #            edgelist[f'{a}-{b}'] = [i]
        #            facelist[i].append(edgelist_idx[f'{a}-{b}'])
        #
        #    # swy: orig edge count 615
        #    print((len(edgelist))) # len(edgelist) => 938, without dupes: 615
        #    exit()

            if not vertex_count and not edge_count and not face_count:
                print(f'[-] AI mesh section empty; nothing to unpack')
            elif skip_ai_mesh:
                print(f'[i] skipping AI mesh section')
            else:
                print(f'[>] unpacking AI mesh with {vertex_count} vertices, {edge_count} edges and {face_count} faces into a Wavefront OBJ file')

                with open(f"{output_folder}/ai_mesh.obj", mode='w') as fw:
                    fw.write(f'# Mount&Blade AI mesh exported by Swyter\'s SCO unpacker from\n# <{scene_file}.sco> on {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n')
                    for elem in ai_mesh['vertices']:
                        floats_as_text = " ".join([repr(fnum)  for fnum in elem])
                        fw.write(f'v {floats_as_text}\n') # swy: write the text floats with as much precision/decimals as possible to get exact results when parsing them back: https://stackoverflow.com/a/3481575/674685
                    fw.write("\n# edges\n\n")
                    for i, elem in enumerate(ai_mesh['edges']):
                        face_data = [vtx_idx +1 for vtx_idx in elem]
                        # fw.write(f'e{" %i" * len(face_data)} \t\t# {i}\n' % tuple(face_data))
                    fw.write("\n# faces\n\n")
                    for i, elem in enumerate(ai_mesh['faces']):
                        face_data = [vtx_idx + 1 for vtx_idx in elem['idx_vertices']]
                        # fw.write(f'f{" %u" * len(face_data)} \t\t# {i} {repr(elem)}\n' % tuple(face_data))
                        fw.write(f'f{" %u" * len(face_data)}\n' % tuple(face_data))

            # swy: some SCO files end at this point, with the terrain/ground section being
            #      completely optional for interiors, which use a custom entity mesh
            cur_offset = f.tell()
            end_offset = f.seek(0, io.SEEK_END)

            f.seek(cur_offset, io.SEEK_SET)
            
            if cur_offset == end_offset:
                print(f'[-] terrain section not present, this may be an interior scene')
            elif skip_terrain:
                print(f'[i] skipping terrain section')
            else:
                # swy: read the terrain/ground layer data structures
                terrain_magic = unpack('<I', f.read(4))[0]; assert(terrain_magic == 0xFF4AD1A6)
                terrain_section_size = unpack('<I', f.read(4))[0]
                num_layers = unpack('<I', f.read(4))[0]
                scene_width = unpack('<I', f.read(4))[0]
                scene_height = unpack('<I', f.read(4))[0]

                block_count = scene_width * scene_height

                print(f'[>] unpacking {scene_width} x {scene_height} terrain with {num_layers} layers into loose PGM/PPM/PFM images')

                ground = {}

                for i in range(num_layers):
                    index = unpack('<i', f.read(4))[0]
                    layer_str = read_rgltag()
                    enabled = unpack('<I', f.read(4))[0]


                    ground[layer_str] = []

                    print("     ", index, layer_str, enabled)

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
                            try:
                                with open(f"{output_folder}/layer_{layer_str}.pfm", mode='wb') as fw:
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
                            except OSError as e:
                                print(f"[e] couldn't open the pfm file: {e}", file=sys.stderr)

                        # swy: Red/Green/Blue vertex coloring/terrain tinting
                        elif layer_str == 'ground_leveling':
                            try:
                                with open(f"{output_folder}/layer_{layer_str}.ppm", mode='wb') as fw:
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
                            except OSError as e:
                                print(f"[e] couldn't open the ppm file: {e}", file=sys.stderr)

                        # swy: unsigned byte (0-254) grayscale with the amount of paint for this material/layer
                        elif not layer_str == 'ground_leveling':
                            try:
                                with open(f"{output_folder}/layer_{layer_str}.pgm", mode='wb') as fw:
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
                            except OSError as e:
                                print(f"[e] couldn't open the pgm file: {e}", file=sys.stderr)

        print(f'[i] done!')

    except OSError as e:
        print(f"[e] couldn't open the input SCO file: {e}", file=sys.stderr)

if __name__ == "__main__":
    # swy: add some helpful commands and their documentation
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description='Unpacks Mount&Blade SceneObj files into a folder of loose files. Created by Swyter in 2022.',
                                     epilog='''\
| Quick-ish help and how to open extracted terrain images /
\________________________________________________________/

  for a «scn_advcamp_dale.sco» it will unpack the internal data
  into a «scn_advcamp_dale» directory in the same folder as this script
  the folder will contain a mission_objects.json and various layer_* image files
  storing each ground/terrain in their appropriate format.

   - layer_ground_leveling.ppm actually stores the RGB color paint, the name Armagan used is just stupid. ¯\_(ツ)_/¯
   - layer_ground_elevation.pfm stores the heightmap data as unnormalized (i.e. -3.0 is three meters
     underwater) 32-bit floating point numbers. This can be converted to 32-bit .EXR or .TIF using ImageMagick, or opened with GIMP.
       Keep in mind that Photoshop opens these PFM files vertically-flipped by mistake.

       If you can't see the height properly (there are only blotchy black and white spots) try adjusting/lowering the exposure to preview it,
       keep in mind that changing that will mess with the data and the heights it contains.
       You can see the raw height with the eyedropper and by switching the mode in the Info panel to «Actual Color» and its range to «32-bit».

       There's a quick way of previewing the actual range of the image without destroying the underlying data in Photoshop, by clicking
       the triangle in the bottom border of the document window, and selecting «32-bit Exposure», that will show a handy slider:
       https://helpx.adobe.com/photoshop/using/image-information.html

   - the rest are optional PGM files which contain grayscale data for each of the painted ground
     textures for the limited set of hardcoded materials.
''')
    parser.add_argument('input', metavar='<path-to-sco>', help='the source .sco file to extract; for a «scn_advcamp_dale.sco» it would write the unpacked data to a «scn_advcamp_dale» directory in the same folder as this script, if not set manually.')

    parser.add_argument('-o', '--output', metavar='<unpacked-sco-folder>', dest='output', required=False,
                        help='path to the resulting folder where the loose (.json, .pgm, .ppm, .pfm, .obj) files will be stored. it does not need to exist, and will get created automatically as needed.')

    parser.add_argument('--dont-unpack-missionobjects', dest='skip_mission_objects', required=False, action='store_true')
    parser.add_argument('--dont-unpack-aimesh',         dest='skip_ai_mesh',         required=False, action='store_true')
    parser.add_argument('--dont-unpack-terrain',        dest='skip_terrain',         required=False, action='store_true')

    args = parser.parse_args() #' C:\\Users\\Usuario\\Documents\\github\\tldmod\\SceneObj\\scn_mordor_prison.sco '.split())

    sco_unpack(
        args.input, args.output, skip_mission_objects=args.skip_mission_objects,
                                         skip_ai_mesh=args.skip_ai_mesh,
                                         skip_terrain=args.skip_terrain
    )