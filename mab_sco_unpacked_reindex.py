import re
from struct import *
import json, os
import sys; from sys import exit
import argparse

def sco_unpacked_reindex(input_folder, opt_scene_props_txt = '', opt_remove_missing = False, opt_remapping_file = '', opt_flora_kinds_txt = '', opt_item_kinds1_txt = '', opt_dont_reindex = False, opt_dont_replace_case = False, opt_dont_change_type = False):
    if not os.path.isdir(input_folder):
        print(f"[e] the unpacked «{input_folder}» SCO folder doesn't seem to exist")
        exit(1)

    print(f'[i] reindexing the scene prop data from the «{input_folder}» folder\n' + \
          f'                                        via «{opt_scene_props_txt}»')

    try:
        with open(f"{input_folder}/mission_objects.json", mode='r', encoding='utf-8') as f_json:
            mission_objects = json.load(f_json)
    except OSError as e:
        print(f"[!] the mission_objects.json file does not seem to exist: {e}", file=sys.stderr)
        exit(1)

    print(f'[-] loading {len(mission_objects):4} used mission objects from the scene JSON file')

    # swy: split the mod's scene_props.txt file into a 2D tokenized array, each line is a row, which has as many columns as whitespace-separated words
    #      that way we can skip ahead quickly when actually reading and understanding the contents in a second step, we only need to do the bare minimum
    scene_props_txt_lines = []

    try:
        with open(f"{opt_scene_props_txt}", mode='r', encoding='utf-8') as f_obj:
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
    mission_obj_remaps  = {}

    print(f'[-] loading {scene_prop_txt_count:4} total scene props from the mod .txt file')

    cur_line = 2 # swy: line 0 is the header magic, line 1 is the prop count, line 2 is where the first prop entry is
    for i in range(scene_prop_txt_count):
        cur_name = scene_props_txt_lines[cur_line][0]; cur_name_key = cur_name

        if not opt_dont_replace_case:
            cur_name_key = cur_name_key.lower()

        scene_prop_txt_entries[cur_name_key] = {'id': i, 'str': cur_name}  # swy: add a new prop entry; its index is its value. doing it as a hashtable makes it easier below
        cur_line += 1 + 2 + int(scene_props_txt_lines[cur_line][5])        # swy: advance the current line (1), plus the two compulsory trailing lines after each prop (2), plus the variable amount of lines; one per extra prop trigger.

    opt_flora_kinds_txt_lines = []
    opt_flora_kinds_txt_entries = {}
    if opt_flora_kinds_txt:
        try:
            with open(f"{opt_flora_kinds_txt}", mode='r', encoding='utf-8') as f_flora:
                for i, line in enumerate(f_flora):
                    line = line.split()
                    line = [token.strip()  for token in line] # swy: make sure get rid of any extra leading/trailing spaces once separated
                    opt_flora_kinds_txt_lines.append(line)

                if len(opt_flora_kinds_txt_lines) < 1:
                    print("[!] bad «flora_kinds.txt header; wrong file?")
                    raise OSError

                opt_flora_kinds_txt_count = int(opt_flora_kinds_txt_lines[0][0]); cur_line = 1
                for i in range(opt_flora_kinds_txt_count):
                    cur_name = opt_flora_kinds_txt_lines[cur_line][0]; cur_name_key = cur_name

                    if not opt_dont_replace_case:
                        cur_name_key = cur_name_key.lower()

                    opt_flora_kinds_txt_entries[cur_name_key] = {'id': i, 'str': cur_name} # swy: see the prop parser above
                    elem_flag          = int(opt_flora_kinds_txt_lines[cur_line][1])
                    elem_num_of_meshes = int(opt_flora_kinds_txt_lines[cur_line][2]) #

                    fkf_tree      = 0x00400000; fkf_speedtree = 0x02000000
                    elem_is_flagged_as_tree = not not (elem_flag & (fkf_tree | fkf_speedtree))

                    # swy: guess what, warband crashes reading the original M&B 1.011 flora_kinds format because it
                    #      expects the extra " 0 0" line after each tree mesh and there's no header with version 
                    #      indication, so to handle both we'll need to look for the two zeros in the first mesh
                    #      entry, if that's there it has to be generated for Warband, otherwise it's not.
                    #      update: it seems like it's not always zeroes, "mb_test1 tree_a" "mb_test1 tree_b" exist, so use something else
                    elem_has_wb_format = 1
                    if elem_is_flagged_as_tree and elem_num_of_meshes >= 1:
                        if (cur_line + elem_num_of_meshes) >= (len(opt_flora_kinds_txt_lines) - 1) or ''' swy: special case for the last entry being a tree, if there are as many remaining lines as meshes, then this isn't a Warband thing, for sure, as they would take twice as many lines, we can't check for the next element, but we don't need to ''' and False or \
                            len(opt_flora_kinds_txt_lines[cur_line + 1 + elem_num_of_meshes]) == 3:     # swy: in the M&B format this should be the first line of the next entry, which should have three elements
                            elem_has_wb_format = 0

                    cur_line += 1 + elem_num_of_meshes * (elem_is_flagged_as_tree and elem_has_wb_format and 2 or 1) # swy: in warband only, trees seem to have two lines per mesh variant, others just one line per mesh

                print(f'[-] loading {opt_flora_kinds_txt_count:4} total flora kinds from the mod .txt file')

        except OSError as e:
            print(f"[!] the «flora_kinds.txt» file does not seem to exist, ignoring: {e}", file=sys.stderr)

    opt_item_kinds1_txt_lines = []
    opt_item_kinds1_txt_entries = {}
    if opt_item_kinds1_txt:
        try:
            with open(f"{opt_item_kinds1_txt}", mode='r', encoding='utf-8') as f_items:
                for i, line in enumerate(f_items):
                    line = line.split()
                    line = [token.strip()  for token in line] # swy: make sure get rid of any extra leading/trailing spaces once separated
                    opt_item_kinds1_txt_lines.append(line)

            if len(opt_item_kinds1_txt_lines) <= 3 or len(opt_item_kinds1_txt_lines[0]) != 3 or ' '.join(opt_item_kinds1_txt_lines[0]) not in ('itemsfile version 2', 'itemsfile version 3'):
                print("[!] bad «item_kinds1.txt header; wrong file?")
                raise OSError

            item_file_version = int(opt_item_kinds1_txt_lines[0][2])
            opt_item_kinds1_txt_count = int(opt_item_kinds1_txt_lines[1][0])
            cur_line = 2
            for i in range(opt_item_kinds1_txt_count):
                cur_name = opt_item_kinds1_txt_lines[cur_line][0]; cur_name_key = cur_name

                if not opt_dont_replace_case:
                    cur_name_key = cur_name_key.lower()

                opt_item_kinds1_txt_entries[cur_name_key] = {'id': i, 'str': cur_name} # swy: see the prop parser above
                if item_file_version == 3: # swy: newer, more complex, Warband item format
                    var_line_list_count = int(opt_item_kinds1_txt_lines[cur_line + 1][0]) # swy: if this isn't zero there's another extra line underneath with X, space-separated elements
                    item_trigger_count  = int(opt_item_kinds1_txt_lines[cur_line + 1 + (var_line_list_count and 1 or 0) + 1][0]) # swy: if this isn't zero there are X extra lines, one with each item trigger
                    cur_line += 1 + (var_line_list_count and 1 or 0) + 1 + item_trigger_count + 2 # swy: the last two count the extra empty line between entries
                elif item_file_version == 2: # swy: TLD uses the older M&B 1.011 item format
                    var_line_list_count = 0
                    item_trigger_count  = int(opt_item_kinds1_txt_lines[cur_line + 1][0])
                    cur_line += 1 + 1 + item_trigger_count + 1

            print(f'[-] loading {opt_item_kinds1_txt_count:4} total  item kinds from the mod .txt file')

        except OSError as e:
            print(f"[!] the «item_kinds1.txt» file does not seem to exist, ignoring: {e}", file=sys.stderr)

    # swy: add a way to let the tool know that a prop changed names; via a plain text file with lines like «spr_old_name_in_sco = spr_new_name_in_mod»
    #      the tool will treat them like they are that new prop, for all intents and purposes. probably saves a lot of work in certain cases
    if opt_remapping_file:
        try:
            with open(f"{opt_remapping_file}", mode='r', encoding='utf-8') as f_remap:
                for i, line in enumerate(f_remap):
                    line = line.split('=')
                    line = [token.strip()  for token in line]

                    if len(line) < 2:
                        continue

                    if line[0].startswith((";", "#", "//", "/*")): # swy: skip potential comments
                        continue

                    for idx, token in enumerate(line):
                        arr = token.split()
                        line[idx] = arr[0] # swy: use the first word in each part of the equals sign, to skip inline comments, IDs can't have spaces anyway

                    old_name = line[0] # swy: find this tag in our SCO, probably obsolete, maybe we want to turn two props into one
                    new_name = line[1] # swy: replace it by this one; doesn't matter if it exists at all in the files or it's a plant; we don't check

                    old_name_key = old_name

                    if not opt_dont_replace_case:
                        old_name_key = old_name_key.lower()

                    mission_obj_remaps[old_name_key] = {'old_str': old_name, 'new_str': new_name}
                    print(f"[+] added {old_name} as an older/mapped/renamed version of {new_name}")

        except OSError as e:
            print(f"[e] the optional remapping file {opt_remapping_file} does not seem to exist, skipping: {e}", file=sys.stderr)


    print(f'[-] successfully loaded all the mod\'s props; starting...\n')

    # swy: go prop by prop in the loaded JSON scene and find if the prop is part of the mod or not,
    #       and if it is, update the old index to the newer one
    prop_already_mentioned = []; mission_obj_remap_already_mentioned = []
    prop_count_fine = 0
    prop_count_changed = 0
    prop_count_renamed = 0
    prop_count_retyped = 0
    prop_count_missing = 0
    objects_to_delete = []

    def gen_prop_tag(prop_tag):
        if not opt_dont_replace_case:
            return prop_tag.lower()
        return prop_tag

    for i, object in enumerate(mission_objects):
        prop_type = 'type' in object and object['type'] or None
        prop_tag  = 'str'  in object and object['str']  or None

        if not prop_type or not prop_tag:
            continue

        # swy: make it lowercase, if needed; this version should be the case-insensitive
        #      always-lowercase, look-up key in the --replace-case mode
        prop_tag = gen_prop_tag(prop_tag)

        # swy: rename our object's tag if it is part of the remapping table: old_name => new_name
        if prop_tag in mission_obj_remaps:
            object_str_old = object['str']; object['str'] = mission_obj_remaps[prop_tag]['new_str']
            prop_tag = gen_prop_tag(object['str'])
            if prop_tag not in mission_obj_remap_already_mentioned:
                print(f"[.] renaming mission object from {object_str_old} to {object['str']}")
                mission_obj_remap_already_mentioned.append(prop_tag)
            prop_count_renamed += 1

        # --
        
        def entries_for_type():
            if   prop_type == 'prop' : return scene_prop_txt_entries
            elif prop_type == 'plant': return opt_flora_kinds_txt_entries
            elif prop_type == 'item' : return opt_item_kinds1_txt_entries

        def search_for_type_in_all_lists(prop_tag):
            for idx, (key, val) in enumerate({'prop' : scene_prop_txt_entries,
                                              'plant': opt_flora_kinds_txt_entries,
                                              'item' : opt_item_kinds1_txt_entries}.items()):
                if len(val) > 0 and prop_tag in val:
                    return key
            return None

        # swy: detect if the object is invalid but not as a different type in a different list, and fix that
        #      (e.g. no plant of that name exists, but there's a scene prop named like that, it was
        #            probably renamed manually by using the search-and-replace functionality)
        if not opt_dont_change_type:
            if prop_tag not in entries_for_type():
                new_prop_type = search_for_type_in_all_lists(prop_tag)
                if new_prop_type:
                    print(f"[¿] «{prop_tag}» does not exist as {prop_type} but is listed in the mod's .txt files as {new_prop_type}; probably renamed, changing type to that")
                    prop_type = new_prop_type; object['type'] = prop_type; prop_count_retyped += 1
        # --

        # swy: skip any unsupported entry/type
        if (len(     scene_prop_txt_entries) <= 0 and prop_type == 'prop' ) or \
           (len(opt_flora_kinds_txt_entries) <= 0 and prop_type == 'plant') or \
           (len(opt_item_kinds1_txt_entries) <= 0 and prop_type == 'item' ):
            continue

        # swy: in case this SCO is obsolete and has older props that are no longer part of the mod
        if prop_tag not in entries_for_type():
            prop_count_missing += 1
            if prop_tag not in prop_already_mentioned:
                print(f"[!] {prop_type} not present in the mod's .txt file; {opt_remove_missing and 'deleting' or 'skipping'}: {prop_tag}")
                prop_already_mentioned.append(prop_tag)
            if opt_remove_missing:
                objects_to_delete.append(object) # swy: defer the deletion for when we finally exit the loop; avoiding side effects of doing it now
            continue

        if not 'id' in object or not 'str' in object:
            print(f"[!] skipping {prop_type} with missing «id» or «str» data")
            continue

        # swy: 'scene_prop_txt_entries' contains the entries that we just parsed
        found_entry = entries_for_type()[prop_tag]


        # swy: this is like a specific version of the manual remapping table functionality that finds matches
        #      between spr_CastleGate and spr_castlegate or vice-versa to save work; it's very-very common
        if not opt_dont_replace_case:
            old_name =      object['str']
            new_name = found_entry['str']
            
            if old_name != new_name:
                object['str'] = new_name
                if prop_tag not in mission_obj_remap_already_mentioned:
                    print(f"[:] renaming mission object with different casing from {old_name} to {new_name}")
                    mission_obj_remap_already_mentioned.append(prop_tag)
                prop_count_renamed += 1


        # swy: now it's our turn to play with the identifiers
        old_id    =      object['id']
        cur_id    = found_entry['id']

        # swy: if the indices match, all is fine; skip the entry
        if old_id == cur_id or opt_dont_reindex:
            prop_count_fine += 1
            continue

        # swy: doesn't match; update it and talk about it if it's the first instance of this prop
        #      in the scene; we don't want to spam the user for each copy
        object['id'] = cur_id; prop_count_changed += 1

        if prop_tag not in prop_already_mentioned:
            print(f"[>] setting id of {prop_type} «{object['str']}» to {cur_id}, it was {old_id}")
            prop_already_mentioned.append(prop_tag)

    # swy: add a nice summary at the end
    prop_count_total = prop_count_fine + prop_count_changed + prop_count_missing
    mission_objects_that_are_not_props = len(mission_objects) - prop_count_total

    print(f"\n[/] finished; {prop_count_fine} mission objects were fine, {prop_count_changed} objects were reindexed, {prop_count_renamed} renamed, {prop_count_retyped} retyped and {prop_count_missing} missing" +
          f"\n    ({prop_count_total} in total, plus {mission_objects_that_are_not_props} asorted mission objects that are not props/plants/items)")

    # swy: we shouldn't pull the rug and delete elements above while we are still looping through indices
    if len(objects_to_delete) > 0:
        for obj in objects_to_delete:
            mission_objects.remove(obj)
    else: # swy: if nothing to delete and no mission objects have been altered then we'll just spit the same thing; skip that
        if prop_count_changed <= 0 and prop_count_renamed <= 0 and prop_count_retyped <= 0:
            print("[i] no need to overwrite the unchanged JSON file, we're done here")
            exit(99) # swy: if we exit with a non-zero ERRORLEVEL code, we can skip running the repacker as the next step in the .cmd batch file

    # swy: save again as an updated JSON file, in-place
    js = json.dumps(obj=mission_objects, indent=2, ensure_ascii=False)
    js = re.sub(r'\[\n\s+(.+)\n\s+(.+)\n\s+(.+)\n\s+(.+)\]', r'[\1 \2 \3]', js) # swy: quick and dirty way of making the arrays of numbers how in a single line, for a more compact look

    print("[i] overwriting, saving the modified JSON file")

    try:
        with open(f"{input_folder}/mission_objects.json", mode='w', encoding='utf-8') as fw:
            fw.write(js)
    except OSError as e:
        print(f"[e] couldn't open the JSON file: {e}", file=sys.stderr)


if __name__ == "__main__":
    # swy: add some helpful commands and their documentation
    parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                     description='''Updates mission object indices in Mount&Blade SceneObj files using mod .txt data. Detects and removes obsolete objects, and allows easy prop swapping. Created by Swyter in 2022.''',
                                     epilog=r'''
| Quick-ish help, explain what it does and how to use it /
\_______________________________________________________/

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
    parser.add_argument('-sc', '--scenepropstxt',      dest='opt_scene_props_txt',    default='', metavar='<path-to-the-updated-scene_props.txt-file>', required=False, help='by default it will guess that we are under <mod folder>/SceneObj/scn_... and use the parent folder, which should be where the mod .txt files are')
    parser.add_argument('-rm', '--removemissing',      dest='opt_remove_missing',     action='store_true', required=False, help='automatically delete any props in the scene not part of the provided scene_props.txt, instead of skipping them')
    parser.add_argument('-re', '--remappingfile',      dest='opt_remapping_file',     default='', metavar='<path-to-the-_mab_sco_mo_remap.txt-file>', help='provide the tool with a plain text file with lines like «spr_old_name_in_sco = spr_new_name_in_mod», the tool will rename each mission object name acording to your rules. also useful to potentially swap props in batch')
    parser.add_argument('-fl', '--florakindstxt',      dest='opt_flora_kinds_txt',    default='', metavar='<path-to-the-updated-flora_kinds.txt-file>', required=False, help='also reindexes mission objects of type «plant» via a provided flora_kinds.txt, by default «../Data/flora_kinds.txt»')
    parser.add_argument('-it', '--itemkinds1txt',      dest='opt_item_kinds1_txt',    default='', metavar='<path-to-the-updated-item_kinds.txt-file>', required=False, help='also reindexes mission objects of type «item» via a provided item_kinds1.txt, by default «../item_kinds1.txt»')
    parser.add_argument('-nx', '--dont-reindex',       dest='opt_dont_reindex',       action='store_true', required=False, help='this can be useful when you only want to delete obsolete objects or use the replacement functionality without changing anything else, reindexing can be noisy and modify too many files that otherwise work fine')
    parser.add_argument('-nc', '--dont-replace-case',  dest='opt_dont_replace_case',  action='store_true', required=False, help='disable the new auto-renaming feature that is toggled on by default; if your prop was originally called e.g. spr_CastleGate when you added it to the scene, but now is spr_castlegate in your msys, the feature will still detect it and fix the name in the .SCO (and ID) to match, making the (case-sensitive) game load the props correctly. this is the most common mode of replacement, and now it can be automatic, no manual replacements. but you can disable it to avoid polluting the files with unwanted changes.')
    parser.add_argument('-nt', '--dont-change-type',   dest='opt_dont_change_type',   action='store_true', required=False, help='disable the new feature (that is toggled on by default) that finds if the name exists for a different kind of object and fixes it; so if you used the replace functionality (to e.g. turn a plant into a scene prop) it would only change its name but internally the object would still be tagged as a plant type and be broken. this auto-finds and fixes that by setting and updating it into the right kind, as long as it exists in the current .txt files, otherwise it cannot be validated. if this whole functionality is undesirable you can avoid it by using the option. Keep in mind that no effort is made to convert any of the secondary parameter fields that have special uses depending on the type of the object, so be careful about that.')

    args = parser.parse_args()

    # swy: by default we will assume we are in an «scn_something» directory under the SceneObj folder and that the parent folder is where the mod's scene_props.txt is
    if not args.opt_scene_props_txt:
        args.opt_scene_props_txt = args.input + '/../' + '../scene_props.txt'

    if not args.opt_flora_kinds_txt:
        args.opt_flora_kinds_txt = args.input + '/../' + '../Data/flora_kinds.txt'

        # swy: some mods don't really have a per-module «Data» folder and fall back to the common one in the root folder
        if not os.path.exists(args.opt_flora_kinds_txt):
            args.opt_flora_kinds_txt = args.input + '/../' + '../../../Data/flora_kinds.txt'

    if not args.opt_item_kinds1_txt:
        args.opt_item_kinds1_txt = args.input + '/../' + '../item_kinds1.txt'

    sco_unpacked_reindex(
        args.input, opt_scene_props_txt=args.opt_scene_props_txt,
                    opt_remove_missing=args.opt_remove_missing,
                    opt_remapping_file=args.opt_remapping_file,
                    opt_flora_kinds_txt=args.opt_flora_kinds_txt,
                    opt_item_kinds1_txt=args.opt_item_kinds1_txt,
                    opt_dont_reindex=args.opt_dont_reindex,
                    opt_dont_replace_case=args.opt_dont_replace_case,
                    opt_dont_change_type=args.opt_dont_change_type
    )
