# mab-tools
[*010 Editor*](https://www.sweetscape.com/010editor/) binary templates for the *Mount&amp;Blade 1.011* and *Warband* game file formats.

Useful to inspect and manually edit or alter structured data fields from binary files visually. The currently available `.bt` files are:
* `*.brf`: BRF stands for *Binary Resource File*.
* `*.sco`: SCO stands for *Scene Object*.
* `options.dat`: Only used in the original game.
   * Famously used for changing the battle size beyond what is possible in-game, it stores most of the gameplay and graphics settings.
   * The template supports all fields and directly converts the internal floating-point representation of the battlesizer to the in-game number, and can be used to change it.
* `controls.dat`: Stores the keymapping/button assignment on both 1.011 and WB; it internally supports two assignable key slots per action/gamekey, not one.
   * Some configurable gamekeys (like crouching or two extra order panel buttons) don't appear in the in-game options dialog, which also only lets you change the first slot.
   * The gamepad button bindings appear in the hidden, second one by default. But can be replaced without affecting the keyboard ones.
   * By editing through the template you can assign two different keys to the same action. You can also bind multiple actions to the same key, as well as remap most of the gamepad keys (unfortunately some of them are hardcoded).


Personally, I think it is a great way of seeing how the sausage is made, aiding in making other programs that read or write them. As well as a nifty way of making small, quick changes.

Interoperability is important.

## Future improvements

* Add a small tool to generate and reimport 16-bit linear PGM (grayscale) heightmap images from SCOs.
* Maybe export the props in a scene as a Wavefront OBJ, by parsing the mods' `.brf` and `.txt` files.
* Make a external scene editor, a bit late, but never say never.
