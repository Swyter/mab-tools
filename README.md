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
  <td><img src='https://web.archive.org/web/20231207010822if_/https://camo.githubusercontent.com/cdfde511d6820d71d60038a8a9c5691a4e95cdba5c126f518b309b5f4ef7028f/68747470733a2f2f63646e2e646973636f72646170702e636f6d2f6174746163686d656e74732f3431313238363132393331373234393033382f3734353334383830323738303835363435302f756e6b6e6f776e2e706e67' /> </td>
  <td><img src='https://web.archive.org/web/20231206213957if_/https://camo.githubusercontent.com/d4286b79372763e185d368f60482545901ecd0479cef3d48435d5f56bdf01448/68747470733a2f2f63646e2e646973636f72646170702e636f6d2f6174746163686d656e74732f3431313238363132393331373234393033382f3734353334393436373135343431353733372f756e6b6e6f776e2e706e67' /> </td>
  <td><img src='https://web.archive.org/web/20231206203209if_/https://camo.githubusercontent.com/1b80966d45bc66ca313c6e8d9302e3ac1d73602cf6779cd5585d13aaa868594e/68747470733a2f2f63646e2e646973636f72646170702e636f6d2f6174746163686d656e74732f3431313238363132393331373234393033382f3734353334393834333733353637343932342f756e6b6e6f776e2e706e67' /> </td>
  <td><img src='http://web.archive.org/web/20231206224407if_/https://camo.githubusercontent.com/7d62f8fda48c8c9461f1059548fd2433a6f7159296c5919738599bb6bc32c3c7/68747470733a2f2f63646e2e646973636f72646170702e636f6d2f6174746163686d656e74732f3431313239313035333730323737343738342f3935353631383630303737313831333434362f756e6b6e6f776e2e706e67' /> </td>
</tr>
</table>

## Future improvements

* ~~Add a small tool to generate and reimport 16-bit linear PGM (grayscale) heightmap images from SCOs.~~
* Maybe export the props in a scene as a Wavefront OBJ, by parsing the mods' `.brf` and `.txt` files.
* Make a external scene editor, a bit late, but never say never.
