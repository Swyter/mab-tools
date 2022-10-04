import re
from struct import *
import json, os
import sys
import argparse

def sco_unpacked_reindex(input_folder, scene_props_txt, opt_remove_missing = False, opt_remapping_file = '', opt_flora = ''):
    if not os.path.isdir(input_folder):
        print(f"[e] the unpacked «{input_folder}» SCO folder doesn't seem to exist")
        exit(1)

    print(f"[i] reindexing the scene prop data from the «{input_folder}» folder via «{scene_props_txt}»")

    try:
        with open(f"{input_folder}/mission_objects.json") as f_json:
            mission_objects = json.load(f_json)
    except OSError as e:
        print(f"[!] the mission_objects.json file does not seem to exist: {e}", file=sys.stderr)
        exit(1)

    print(f'[-] loading {len(mission_objects)} used mission objects from the scene JSON file')

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
        print(f"[e] the scene_props.txt file does not seem to exist: {e}", file=sys.stderr)
        exit(2)

    if len(scene_props_txt_lines) <= 3 or ' '.join(scene_props_txt_lines[0]) != 'scene_propsfile version 1':
        print("[!] bad scene_props.txt header; wrong file?")
        exit(3)

    # swy: actually parse the splitted text lines to get the sorted list of available props in this mod that hold their index, using a hash table
    scene_prop_txt_count = int(scene_props_txt_lines[1][0])
    scene_prop_txt_entries = {}
    scene_prop_txt_remaps  = {}

    print(f'[-] loading {scene_prop_txt_count} total scene props from the mod .txt file')

    cur_line = 2 # swy: line 0 is the header magic, line 1 is the prop count, line 2 is where the first prop entry is
    for i in range(scene_prop_txt_count):
        scene_prop_txt_entries[scene_props_txt_lines[cur_line][0]] = i # swy: add a new prop entry; its index is its value. doing it as a hashtable makes it easier below
        cur_line += 1 + 2 + int(scene_props_txt_lines[cur_line][5]) # swy: advance the current line (1), plus the two compulsory trailing lines after each prop (2), plus the variable amount of lines; one per extra prop trigger.


    # swy: add a way to let the tool know that a prop changed names; via a plain text file with lines like «spr_old_name_in_sco = spr_new_name_in_mod»
    #      the tool will treat them like they are that new prop, for all intents and purposes. probably saves a lot of work in certain cases
    if opt_remapping_file:
        try:
            with open(f"{opt_remapping_file}") as f_remap:
                for i, line in enumerate(f_remap):
                    line = line.split('=')
                    line = [token.strip()  for token in line]

                    if len(line) < 2:
                        continue

                    old_name = line[0]
                    new_name = line[1]

                    if scene_prop_txt_entries[new_name]:
                        scene_prop_txt_entries[old_name] = scene_prop_txt_entries[new_name]
                        scene_prop_txt_remaps[old_name] = new_name
                        print(f"[+] added {old_name} as an older/mapped/renamed version of {new_name}")

        except OSError as e:
            print(f"[e] the optional remapping file {opt_remapping_file} does not seem to exist, skipping: {e}", file=sys.stderr)


    print(f'[-] successfully loaded all the mod\'s props; starting...\n')

    # swy: go prop by prop in the loaded JSON scene and find if the prop is part of the mod or not,
    #       and if it is, update the old index to the newer one
    prop_already_mentioned = []
    prop_count_fine = 0
    prop_count_changed = 0
    prop_count_missing = 0

    for i, object in enumerate(mission_objects):
        prop_type = object['type']
        prop_tag  = object['str']

        if prop_type != 'prop':
            continue

        # swy: rename our prop's tag if it is part of the remapping table: old_name => new_name
        if prop_tag in scene_prop_txt_remaps:
            object['str'] = scene_prop_txt_remaps[object['str']]
            print(f"[.] renaming prop from {prop_tag} to {object['str']}")
            prop_tag = object['str']
        
        if prop_tag not in scene_prop_txt_entries:
            prop_count_missing += 1
            if prop_tag not in prop_already_mentioned:
                print(f"[!] prop not present in the mod's scene_props.txt file; {opt_remove_missing and 'deleting' or 'skipping'}: {prop_tag}")
                prop_already_mentioned.append(prop_tag)
            if opt_remove_missing:
                del mission_objects[i]
            continue

        # swy: scene_prop_txt_entries contains the entries that we just parsed
        old_id    = object['id']
        cur_id    = scene_prop_txt_entries[object['str']]

        # swy: if the indices match, all is fine; skip the entry
        if old_id == cur_id:
            prop_count_fine += 1
            continue
        
        # swy: doesn't match; update it and talk about it if it's the first instance of this prop
        #      in the scene; we don't want to spam the user for each copy
        object['id'] = cur_id; prop_count_changed += 1

        if prop_tag not in prop_already_mentioned:
            print(f"[>] setting id of scene prop «{prop_tag}» to {cur_id}, it was {old_id}")
            prop_already_mentioned.append(prop_tag)

    # swy: add a nice summary at the end
    prop_count_total = prop_count_fine + prop_count_changed + prop_count_missing
    mission_objects_that_are_not_props = len(mission_objects) - prop_count_total

    print(f"\n[/] finished; {prop_count_fine} props were fine, {prop_count_changed} props were reindexed and {prop_count_missing} props were missing" +
          f"\n    ({prop_count_total} in total, plus {mission_objects_that_are_not_props} asorted mission objects that are not props)")

    if prop_count_changed <= 0:
        print("[i] no need to overwrite the unchanged JSON file, we're done here")
        exit(0)

    # swy: save again as an updated JSON file, in-place
    js = json.dumps(obj=mission_objects, indent=2, ensure_ascii=False)
    js = re.sub(r'\[\n\s+(.+)\n\s+(.+)\n\s+(.+)\n\s+(.+)\]', r'[\1 \2 \3]', js) # swy: quick and dirty way of making the arrays of numbers how in a single line, for a more compact look

    try:
        with open(f"{input_folder}/mission_objects.json", mode='w') as fw:
            fw.write(js)
    except OSError as e:
        print(f"[e] couldn't open the JSON file: {e}", file=sys.stderr)


if __name__ == "__main__":
    # swy: add some helpful commands and their documentation
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description='''Fixes the scene prop indices in Mount&Blade SceneObj files to match the order of a mod's scene_props.txt. Created by Swyter in 2022.''',
                                     epilog='''\
Q: What is this for? I don't get it. :(
A: Are your props suddenly all messed up? Even if each mission object entry includes a name for each prop
   instance, the game only ever uses the numeric index to match it against a mod's scene_props.txt file.

   So, in case the modder changes the order in which scene props are listed in the module system, either
   by re-sorting them or deleting an obsolete entry, any previously-edited SCO will be off; spawning the
   wrong prop. So if spr_fireplace_b was placed in an SCO when it was number 33 in the scene prop list,
   the SCO will store both the spr_fireplace_b tag and the index 32 (indices start at zero). After
   moving the list around by removing a bunch of props that go before in your module system,
   spr_fireplace_b may now be prop number 20 instead, so index 19.

   But the game still tries to use index 32 in that scene and maybe puts a spr_pillow_c there
   instead (which is the random prop that ended up in that line).

   Thanks to this program we can match the spr_fireplace_b name/tag in the SCO with a newer
   scene_props.txt, then find that in the updated scene_props.txt our spr_fireplace_b
   should now be 19 instead of 32, and replace the number. We do that for every prop
   in the scene, if the prop no longer exists we throw a warning for the
   modder to fix. Easy peasy.

Q: Doing it manually sounds cumbersome. Any way to automate all this for many files?
A: You can probably quickly chain or combine the small tools into small scripts
   to do this for you, something along these lines, in Bash (i.e. Linux/macOS):
    for file in ./scn_*.sco; do
      mkdir _tmp_unpack_folder
      echo -ne "\n -- processing $file\n"
      python mab_sco_unpack.py "$file" -o _tmp_unpack_folder --dont-unpack-aimesh --dont-unpack-terrain
      python mab_sco_unpacked_reindex.py _tmp_unpack_folder
      python mab_sco_repack.py _tmp_unpack_folder -o "$file" --missionobjects repack --aimesh keep --terrain keep
      rm -rf _tmp_unpack_folder
    done

   This is how it's done in Batch (i.e. Windows):
    @echo off
    for %%file in (scn_*.sco) do (
      mkdir _tmp_unpack_folder
      echo. 
      echo -- processing %%file
      echo.
      mab_sco_unpack.exe "%%file" -o _tmp_unpack_folder --dont-unpack-aimesh --dont-unpack-terrain
      mab_sco_unpacked_reindex.exe _tmp_unpack_folder
      mab_sco_repack.exe _tmp_unpack_folder -o "%%file" --missionobjects repack --aimesh keep --terrain keep
      rmdir _tmp_unpack_folder /S /Q
    )
''')

    parser.add_argument('input', metavar='<unpacked-sco-folder>', help='the source folder; for a «scn_advcamp_dale.sco» it will read the unpacked data from a «scn_advcamp_dale» directory in the same folder as this script')
    parser.add_argument('-sc', '--scenepropstxt', dest='scene_props_txt', default='', metavar='<path-to-the-updated-scene_props.txt-file>', required=False, help='by default it will guess that we are under <mod folder>/SceneObj/scn_... and use the parent folder, which should be where the mod .txt files are')
    parser.add_argument('-rm', '--removemissing', dest='opt_remove_missing', action='store_true', required=False, help='automatically delete any props in the scene not part of the provided scene_props.txt, instead of skipping them')
    parser.add_argument('-re', '--remappingfile', dest='opt_remapping_file', action='store_true', required=False, help='automatically delete any props in the scene not part of the provided scene_props.txt, instead of skipping them')
    parser.add_argument('-fl', '--reindexflora',  dest='opt_flora',          action='store_true', required=False, help='also reindexes mission objects of type «plant» via a provided flora_kinds.txt')

    args = parser.parse_args()

    # swy: by default we will assume we are in the SceneObj folder and that the parent folder is where the mod's scene_props.txt is
    if not args.scene_props_txt:
        args.scene_props_txt = '../scene_props.txt'

    sco_unpacked_reindex(args.input, args.scene_props_txt, opt_remove_missing=args.opt_remove_missing, opt_remapping_file=args.opt_remapping_file, opt_flora=args.opt_flora)