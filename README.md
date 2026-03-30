# mab-tools
[*010 Editor*](https://www.sweetscape.com/010editor/) binary templates for the *Mount&amp;Blade 1.011* and *Warband* game file formats; they are useful to inspect, understand and manually edit or alter structured data fields from binary files, visually.

## What works
The currently available `.bt` files are:
* `*.brf`: BRF stands for *Binary Resource File*.
* `*.sco`: SCO stands for *Scene Object*.
* `options.dat`: Only used in the original game.
   * Famously used for changing the battle size beyond what is possible in-game, it stores most of the gameplay and graphics settings.
   * The template supports all fields and directly converts the internal floating-point representation of the battlesizer to the in-game number, and can be used to change it.
* `controls.dat`: Stores the keymapping/button assignment on both 1.011 and WB; it internally supports two assignable key slots per action/gamekey, not one.
   * Some configurable gamekeys (like crouching or two extra order panel buttons) don't appear in the in-game options dialog, which also only lets you change the first slot.
   * The gamepad button bindings appear in the hidden, second one by default. But can be replaced without affecting the keyboard ones.
   * By editing through the template you can assign two different keys to the same action. You can also bind multiple actions to the same key, as well as remap most of the gamepad keys (unfortunately some of them are hardcoded).
* `sg*.sav`: Savegame files. Storing a full snapshot of the game state.
   * With player data, date and time, map cloud/haze, random seed, global variables, trigger timing and firing state, party records, factions, troops, quests, game text log, info-pages, slot values for items/parties/troops and more, map tracks, map events like battle encounters and statistics like the kill or wounded counts.
   * Heavily based on the 1.143 save format documentation by @*cmpxchg8b* [here](https://mbmodwiki.github.io/Savegame).
   * Warband-only, for now.


Personally, I think it is a great way of seeing how the sausage is made, aiding in making other programs that read or write them. As well as a nifty way of making small, quick changes. ¯\\\_(ツ)_/¯

Interoperability is important.

<table><tr>
  <td><img src='https://github.com/user-attachments/assets/e57d6a71-993e-4e00-8dd0-080c79e5da4d' /> </td>
  <td><img src='https://github.com/user-attachments/assets/67747c53-3c5f-4956-9f93-8cff27994d45' /> </td>
  <td><img src='https://github.com/user-attachments/assets/8eacaf4f-8503-49c9-8ee4-1ce273832db7' /> </td>
  <td><img src='https://github.com/user-attachments/assets/13ed4f13-919f-4fa4-af80-2e56e51c3feb' /> </td>
</tr>
</table>

## Future improvements

* ~~Add a small tool to generate and reimport 16-bit linear PGM (grayscale) heightmap images from SCOs.~~
* Maybe export the props in a scene as a Wavefront OBJ, by parsing the mods' `.brf` and `.txt` files.
* Make a external scene editor, a bit late, but never say never.
