@echo off && color 71 && cls && title swyscotools log-- && chcp 65001 > nul && MODE 1000

setlocal enableextensions
setlocal enabledelayedexpansion

:: swy: fix displaying the «» Unicode characters; otherwise it shows mojibake; force python to use utf-8 encoded output:
::      https://old.reddit.com/r/scripting/comments/oncm5q/python_batch_script_encoding_problem_while_saving/h8e9lfb/
set PYTHONIOENCODING=UTF-8

:: swy: remaps any props in every .sco in this folder, like changing every spr_palisade_longer to spr_palisade_a;
::      just edit mab_sco_mo_remap.txt to set your own. Effectively renaming them mod-wide.
::
::      keep in mind that without a valid scene_props.txt in the right place (i.e. when you run this outside the
::      SceneObj folder it won't know where to find it) the reindexing command will fail.

::      note: if you want to save the script's output into a .log file while still displaying it
::        live you can open a PowerShell window in the same folder and run it like this: «./mab_sco_mo_remap_all.cmd | Set-Content mab_sco_mo_remap_all.log -Passthru 2>&1»
::      A simpler CMD.exe version would be using this, you won't have live output, though: «mab_sco_mo_remap_all.cmd >> _log.txt 2>&1»

if not exist "../scene_props.txt" (
    MODE CON: COLS=91 LINES=7
    echo. 
    echo [e] Make sure you run this from your mod's SceneObj folder, so that the program can find
    echo     both your .SCO files and the «scene_props.txt» that should be in the parent folder.
    echo. 
    pause && goto :eof
)

for /f "tokens=1" %%a IN ('dir "scn_*.sco" /-C/S/A:-D') do @set scn_file_count=!n2!& set n2=%%a
set /a scn_cur_index = 1

for %%f in (scn_*.sco) do (
    set /a percentage=!scn_cur_index! * 100 / !scn_file_count!
    echo. 
    echo  --^> processing %%f ^(!scn_cur_index!/!scn_file_count!^) -- !percentage!%%
    set /a scn_cur_index += 1

    mkdir _tmp_unpack_folder 2>nul && rem :: https://stackoverflow.com/a/44931843/674685

    rem swy: extract our current filename .sco into an empty _tmp_unpack_folder, only extract the mission_objects.json to save time, we don't need to
    rem      extract the terrain or AI mesh, we won't touch it, and if we repack it there can be differences.
    if 1 == 1 (
        echo. && echo ** 1^) unpack &&  mab_sco_unpack            "%%f"  -o _tmp_unpack_folder  --dont-unpack-aimesh  --dont-unpack-terrain
    )

    rem swy: use our very own mab_sco_mo_remap.txt file to search for replacements, use that coupled with the data from ../../scene_props.txt to tweak
    rem      _tmp_unpack_folder/mission_objects.json and do the replacements. You can add --scenepropstxt scene_props.txt to make it look up that
    rem      file somewhere else when we're not in a SceneObj folder. Remove --dont-reindex to make it update the IDs/numbers after the rename.
    if !ERRORLEVEL! == 0 (
        echo. && echo ** 2^) reindx &&  mab_sco_unpacked_reindex  --dont-reindex  --remappingfile mab_sco_mo_remap.txt  _tmp_unpack_folder
    )

    rem swy: use the extracted _tmp_unpack_folder as input, use the original filename .sco as output. only use/read the mission_objects.json from that
    rem      extracted folder, leave the other two .sco terrain/AI mesh sections alone/pristine from the original, just copy them over.
    if !ERRORLEVEL! == 0 (
        echo. && echo ** 3^) repack &&  mab_sco_repack            _tmp_unpack_folder  -o "%%f"  --missionobjects repack  --aimesh keep  --terrain keep
    )

    rem swy: delete the whole temporary folder to make sure it can be recreated and it's empty for any following files that need
    rem      to be extracted afterwards, we don't want leftovers in there
    rmdir _tmp_unpack_folder /S /Q
    echo.
)

echo *** hopefully finished, press any key to exit... && pause