import pathlib
import re
from struct import *
import json, os, io
import sys
import argparse

def sco_unpacked_reindex(input_folder, scene_props_txt):

    scene_file = input_folder + '.sco'

    if not os.path.isdir(input_folder):
        print(f"[e] the unpacked «{input_folder}» SCO folder doesn't seem to exist")
        exit(1)

    mission_objects = ""

    try:
        with open(f"{input_folder}/mission_objects.json") as f_json:
            mission_objects = json.load(f_json)
    except OSError as e:
        print(f"[!] the mission_objects.json file does not exist: {e}", file=sys.stderr)
        exit(1)

    print(f"[i] reindexing the scene prop data from the «{input_folder}» folder via «{scene_props_txt}»")

    # swy: split the mod's scene_props.txt file into a 2D tokenized array, each line is a row, which has as many columns as whitespace-separated words
    #      that way we can skip ahead quickly when actually reading and understanding the contents in a second step, we only need to do the bare minimum
    scene_props_txt_lines = []

    try:
        with open(f"{scene_props_txt}") as f_obj:
            for i, line in enumerate(f_obj):
                line = line.split()
                line = [token.strip()  for token in line] # swy: make sure get rid of any extra leading/trailing spaces once separated
                scene_props_txt_lines.append(line)

    except OSError as e:
        print(f"[e] the scene_props.txt file does not exist: {e}", file=sys.stderr)
        exit(2)


    #print(f'[>] unpacking {object_count} mission objects into a JSON file')

    if ' '.join(scene_props_txt_lines[0]) != 'scene_propsfile version 1':
        print(f"[!] bad header")


    # swy: actually parse the splitted text lines to get the sorted list of available props in this mod that hold their index, using a hash table
    scene_prop_txt_count = int(scene_props_txt_lines[1][0])
    scene_prop_txt_entries = {}
    cur_line = 2 # swy: line 0 is the header magic, line 1 is the prop count, line 2 is where the first prop entry is
    for i in range(scene_prop_txt_count):
        scene_prop_txt_entries[scene_props_txt_lines[cur_line][0]] = i
        cur_line += 1 + 2 + int(scene_props_txt_lines[cur_line][5]) # swy: advance the current line (1), plus the two trailing lines (2), plus the variable amount of lines; one per extra prop trigger.

    # swy: go prop by prop in the loaded JSON scene and find if the prop is part of the mod or not,
    #       and if it is, update the old index to the newer one
    prop_already_mentioned = []

    for i, object in enumerate(mission_objects):
        prop_type = object['type']
        prop_tag  = object['str']

        if prop_type != 'prop':
            continue
        
        if prop_tag not in scene_prop_txt_entries:
            if prop_tag not in prop_already_mentioned:
                print(f"[!] prop not present in the mod's scene_props.txt file; skipping: {prop_tag}")
                prop_already_mentioned.append(prop_tag)
            continue

        # swy: scene_prop_txt_entries contains the entries that we just parsed
        old_id    = object['id']
        cur_id    = scene_prop_txt_entries[object['str']]

        # swy: if the indices match, all is fine; skip the entry
        if old_id == cur_id:
            continue
        
        # swy: doesn't match; update it and talk about it if it's the first instance of this prop
        #      in the scene; we don't want to spam the user for each copy
        object['id'] = cur_id

        if prop_tag not in prop_already_mentioned:
            print(f"[>] setting id of scene prop «{prop_tag}» to {cur_id}, it was {old_id}")
            prop_already_mentioned.append(prop_tag)

    # swy: save again as an updated JSON file, in-place
    js = json.dumps(obj=mission_objects, indent=2, ensure_ascii=False)
    js = re.sub(r'\[\n\s+(.+)\n\s+(.+)\n\s+(.+)\n\s+(.+)\]', r'[\1 \2 \3]', js) # swy: quick and dirty way of making the arrays of numbers how in a single line, for a more compact look

    exit()

    try:
        with open(f"{input_folder}/mission_objects.json", mode='w') as fw:
            fw.write(js)
    except OSError as e:
        print(f"[e] couldn't open the JSON file: {e}", file=sys.stderr)
    except OSError as e:
        print(f"[e] couldn't open the target SCO file: {e}", file=sys.stderr)

if __name__ == "__main__":
    # swy: add some helpful commands and their documentation
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description='''Fixes the scene prop indices in Mount&Blade SceneObj files to match the order of a mod's scene_props.txt. Created by Swyter in 2022.''',
                                     epilog='''Why? Even if each mission object entry includes a name for each prop instance, the game only ever uses the numeric index to match it against a mod's scene_props.txt file.''' +
                                            '''So, in case the modder changes the order in which scene props are listed in the module system, either by re-sorting them or deleting an obsolete entry,''' +
                                            '''any previously-edited SCO will be off, spawning the wrong prop. So if spr_fireplace_b was placed in an SCO when it was number 33 in the scene prop list''' +
                                            '''the SCO will save both the spr_fireplace_b tag and the index 32 (indices start at zero). After moving the list around by removing a prop that goes before in your module system, spr_fireplace_b may now be prop number 20 instead, so index 19.''' +
                                            '''But the game still tries to use index 32 in that scene and maybe puts a spr_pillow_c there instead (which is the random prop that ended up in that line).''' + 
                                            '''Thanks to this program we can match the spr_fireplace_b tag in the SCO with a newer scene_props.txt, find that in the updated scene_props.txt our spr_fireplace_b now is 19, and replace the number. We do that for every prop in the scene, if the prop no longer exists we throw a warning for the modder to fix. Easy peasy.''')

    parser.add_argument('input', metavar='<unpacked-sco-folder>', help='the source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data from a «scn_advcamp_dale» directory in the same folder as this script')
    parser.add_argument('-sc', '--scenepropstxt', dest='scene_props_txt', default='', metavar='<path to the updated .txt file>', required=False)

    args = parser.parse_args("C:\\Users\\Usuario\\Documents\\github\\mab-tools\\scn_mont_st_michel --scenepropstxt C:\\Users\\Usuario\\Documents\\github\\tldmod\\scene_props.txt".split())

    # swy: by default we will assume we are in the SceneObj folder and that the parent folder is where the mod's scene_props.txt is
    if not args.scene_props_txt:
        args.scene_props_txt = '../scene_props.txt'

    sco_unpacked_reindex(args.input, args.scene_props_txt)