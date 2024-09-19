import re
from struct import *
import json, os
import sys; from sys import exit
import argparse

def sco_unpacked_raise_height(input_folder, height):
    if not os.path.isdir(input_folder):
        print(f"[e] the unpacked «{input_folder}» SCO folder doesn't seem to exist")
        exit(1)

    print(f'[i] raising the height of the scene data in the «{input_folder}» folder to {height}')

    try:
        with open(f"{input_folder}/mission_objects.json", mode='r', encoding='utf-8') as f_json:
            mission_objects = json.load(f_json)
    except OSError as e:
        print(f"[!] the mission_objects.json file does not seem to exist: {e}", file=sys.stderr)
        exit(1)

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
