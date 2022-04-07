# mab-tools
[*010 Editor*](https://www.sweetscape.com/010editor/) binary templates for the *Mount&amp;Blade 1.011* and *Warband* game file formats.

Useful to inspect and manually edit or alter structured data fields from binary files visually. The currently available `.bt` files are:
* `*.brf`: BRF stands for *Binary Resource File*.
* `*.sco`: SCO stands for *Scene Object*.
* `options.dat`: Only used in the original game.
* `config.dat`: Stores the key-mapping on both 1.011 and WB; internally supports two assignable key slots per action/gamekey.
   * Some configurable gamekeys don't appear in the options dialog, which only lets you change the first slot, the gamepad bindings appear in the hidden, second one by default.


Personally, I think it is a great way of seeing how the sausage is made, aiding in making other programs that read or write them.

Interoperability is important.

# Future improvements

* Add a small tool to generate and reimport 16-bit linear PGM (grayscale) heightmap images.
