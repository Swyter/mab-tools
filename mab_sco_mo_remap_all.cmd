@echo off && color 71 && cls && title swyscotools log-- && chcp 65001 > nul && MODE 1000

setlocal enableextensions
setlocal enabledelayedexpansion

:: swy: remaps any props in every .sco in this folder, like changing every pr_palisade_longer to spr_palisade_a;
::      just edit mab_sco_mo_remap.txt to set your own. Effectively renaming them mod-wide.
::
::      keep in mind that without a valid scene_props.txt in the right place (i.e. when you run this outside the
::      SceneObj folder it won't know where to find it) the reindexing command will fail.
for %%f in (scn_*.sco) do (
    mkdir _tmp_unpack_folder
    echo.
    echo -- processing %%f

    :: swy: extract our current filename .sco into an empty _tmp_unpack_folder, only extract the mission_objects.json to save time, we don't need to
    ::      extract the terrain or AI mesh, we won't touch it, and if we repack it there can be differences.
    echo. && echo ** 1^) unpack && mab_sco_unpack.exe            "%%f" -o _tmp_unpack_folder  --dont-unpack-aimesh  --dont-unpack-terrain

    :: swy: use our very own mab_sco_mo_remap.txt file to search for replacements, use that coupled with the data from ../../scene_props.txt to tweak
    ::      _tmp_unpack_folder/mission_objects.json and do the replacements. You can add --scenepropstxt scene_props.txt to make it look up that
    ::      file somewhere else when we're not in a SceneObj folder. Remove --dont-reindex to make it update the IDs/numbers after the rename.
    echo. && echo ** 2^) reindx && mab_sco_unpacked_reindex.exe  --dont-reindex  --remappingfile mab_sco_mo_remap.txt  _tmp_unpack_folder

    :: swy: use the extracted _tmp_unpack_folder as input, use the original filename .sco as output. only use/read the mission_objects.json from that
    :       extracted folder, leave the other two .sco terrain/AI mesh sections alone/pristine from the original, just copy them over.
    echo. && echo ** 3^) repack && mab_sco_repack.exe            _tmp_unpack_folder -o "%%f"  --missionobjects repack  --aimesh keep  --terrain keep

    :: swy: delete the whole temporary folder to make sure it can be recreated and it's empty for any following files that need
    ::      to be extracted afterwards, we don't want leftovers in there
    rmdir _tmp_unpack_folder /S /Q
    echo.
)

pause