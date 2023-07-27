# swy: this launches the .cmd while also logging everything to a mab_sco_mo_remap_all.log file.
#      run it via powershell; right-click this .ps1 file and click on 'Run with PowerShell'.

#      PS: the log file will get overwritten every time you run this, so make sure to rename the file if
#      you want to see the warnings, missing scene objects and other problems that may have been found.

# swy: fix displaying the «» Unicode characters; otherwise it shows mojibake
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'; $OutputEncoding = [System.Console]::OutputEncoding = [System.Console]::InputEncoding = [System.Text.Encoding]::UTF8

./mab_sco_mo_remap_all.cmd 2>&1 | Tee-Object mab_sco_mo_remap_all.log
