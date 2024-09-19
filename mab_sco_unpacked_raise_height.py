import re
from struct import *
import json, os
import sys; from sys import exit
import argparse
import io

def sco_unpacked_raise_height(input_folder, height):
    if not os.path.isdir(input_folder):
        print(f"[e] the unpacked «{input_folder}» SCO folder doesn't seem to exist")
        exit(1)

    print(f'[i] raising the height of the scene data in the «{input_folder}» folder to {height}')

    # swy: /part a/ raise the scene props, items and flora level in the scene objects JSON file
    try:
        with open(f"{input_folder}/mission_objects.json", mode='r', encoding='utf-8') as f_json:
            mission_objects = json.load(f_json)
            print(f'[-] loading {len(mission_objects):4} used mission objects from the scene JSON file')

            # swy: go prop by prop in the loaded JSON scene and find if the prop is part of the mod or not,
            #       and if it is, update the old index to the newer one
            for i, object in enumerate(mission_objects):
                prop_pos = 'pos' in object and object['pos'] or None

                if not prop_pos or len(prop_pos) > 3:
                    continue

                # swy: raise the Z coordinate of the scene object position by the provided number
                object['pos'][2] += height

            # swy: save again as an updated JSON file, in-place
            js = json.dumps(obj=mission_objects, indent=2, ensure_ascii=False)
            js = re.sub(r'\[\n\s+(.+)\n\s+(.+)\n\s+(.+)\n\s+(.+)\]', r'[\1 \2 \3]', js) # swy: quick and dirty way of making the arrays of numbers how in a single line, for a more compact look

            # swy: add a nice summary at the end
            print(f"[/] finished; adjusted the height of {len(mission_objects)} mission objects")
            print( "    saving the modified JSON file")

            try:
                with open(f"{input_folder}/mission_objects.json", mode='w', encoding='utf-8') as fw:
                    fw.write(js)
            except OSError as e:
                print(f"[e] couldn't open the JSON file: {e}", file=sys.stderr)

    except OSError as e:
        print(f"[!] the mission_objects.json file does not seem to exist: {e}", file=sys.stderr)
        exit(1)

    # swy: /part b/ raise the AI mesh polygons in the Wavefront OBJ file
    def getleftpart(line, token):
            pos = line.find(token)
            if pos != -1:
                return line[:pos]
            else:
                return line

    lines = []
    try:
        with open(f"{input_folder}/ai_mesh.obj", encoding='utf-8-sig') as f_obj:
            for i, line in enumerate(f_obj):
                lines.append(line)
                # swy: strip anything to the right of a line comment marker
                line = getleftpart(line, '#' )
                line = line.split()
    
                if not line or len(line) < 4:
                    continue
    
                if line[0] == 'v':
                    elem = [float(token)  for token in line[1:]]
                    # swy: raise the Z coordinate of this AI mesh vertex by the provided number
                    elem[2] += height

                    floats_as_text = " ".join([repr(fnum)  for fnum in elem])
                    lines[i] = f'v {floats_as_text}\n'

            print(f"[/] adjusted the height of the AI mesh vertices; saving updated OBJ file")
            try:
                with open(f"{input_folder}/ai_mesh.obj", mode='w', encoding='utf-8') as fw:
                    fw.write(''.join(lines))
            except OSError as e:
                print(f"[e] couldn't open the JSON file: {e}", file=sys.stderr)

    except OSError as e:
        print(f"[!] skipping AI mesh: {e}", file=sys.stderr)

    # swy: /part c/ elevate the heightmap vertices/pixels in the NetPBM portable float map (PFM) file
    ground = {}
    ground_layer = 'ground_elevation.pfm'
    layer_name = ground_layer.split('.')[0].lower()
    ext        = ground_layer.split('.')[1].lower()
    last_scene_width = None; last_scene_height = None
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
                exit(2)

            magic  =       ascii_header_flattened[0]  # line 1, magic value
            width  =   int(ascii_header_flattened[1]) # line 2, width and height
            height =   int(ascii_header_flattened[2])
            maxval = float(ascii_header_flattened[3]) # line 3, extra thing

            # swy: grab how far away we are from the start after reading the ASCII part, use it to compute how many bytes the rest of the data takes
            f_image.seek(0, io.SEEK_END); bytes_remain = f_image.tell() - header_end_byte_offset; f_image.seek(header_end_byte_offset)

            # swy: actually read and interpret the binary data after the header, depending on the format/sub-variant
            print(f'[i] found layer_{ground_layer}; type {magic}, {width} x {height}')

            if magic == 'Pf' and ext == 'pfm':
                assert maxval in [-1.0, 1.0]
                cells_to_read = width * height
                bytes_to_read = cells_to_read * 4; assert bytes_to_read == bytes_remain
                contents_orig = []; contents_orig = unpack(f'{maxval < 0.0 and "<" or ">"}{cells_to_read}f', f_image.read(bytes_to_read)) # swy: handle both big (1.0, '>f') and little-endian (-1.0, '<f') floats; just in case

                # swy: reverse the row ordering because the PFM format is from bottom to top, unlike every other NetPBM one, of course :)
                for i in reversed(range(last_scene_height)):
                    contents += contents_orig[i*last_scene_width : (i*last_scene_width) + last_scene_width][::-1] # swy: grab one "line" worth of data from the farthest point, and add it first; sort them backwards
                
                ground[layer_name] = contents
            else:
                print(f'[e] Unknown NetPBM format, {magic}: use Pf.'); exit(1)

            exit(0)
            # swy: write it
            scene_width   = last_scene_width
            scene_height  = last_scene_height
            output_folder = input_folder
            layer_str     = layer_name
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


    except FileNotFoundError:
        print(f'[!]    no layer_{ground_layer} here, skipping...')




if __name__ == "__main__":
    # swy: add some helpful commands and their documentation
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description='''Updates mission object indices in Mount&Blade SceneObj files using mod .txt data. Detects and removes obsolete objects, and allows easy prop swapping. Created by Swyter in 2022.''',
                                     epilog='''\

''')

    parser.add_argument('input',  metavar='<unpacked-sco-folder>',       help='the source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data from a «scn_advcamp_dale» directory in the same folder as this script')
    parser.add_argument('height', metavar='<height-offset>', type=float, help='by default it will guess that we are under <mod folder>/SceneObj/scn_... and use the parent folder, which should be where the mod .txt files are')

    #args = parser.parse_args(['C:\\Program Files (x86)\\Mount&Blade\\Modules\\Native - copia\\SceneObj\\scn_castle_1_exterior'])
    args = parser.parse_args(['C:/Users/Usuario/Documents/github/tldmod/_wb/SceneObj/scn_advcamp_gondor_siege', '120'])

    sco_unpacked_raise_height(
        args.input, args.height
    )
