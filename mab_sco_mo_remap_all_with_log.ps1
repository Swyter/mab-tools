# swy: this launches the .cmd while also logging everything to a mab_sco_mo_remap_all.log file
./mab_sco_mo_remap_all.cmd | Set-Content mab_sco_mo_remap_all.log -Passthru 2>&1