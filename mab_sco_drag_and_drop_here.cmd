@echo off && color 71 && cls && title swyscotools log-- && chcp 65001 > nul

setlocal enableextensions
setlocal enabledelayedexpansion
set PATH=!PATH!;%CD%

if "%~1"=="" (
    :show_help
    MODE CON: COLS=91 LINES=7
    echo  ┌───────────────────────────────────────────────────────────────────────────────────────┐
    echo  │ Drag and drop your .sco file, mission_objects.json or unpacked scn_ folder over       │
    echo  │ the icon or shortcut and this will call the right program and let you see the output  │
    echo  └───────────────────────────────────────────────────────────────────────────────────────┘
    echo. 
    pause
    goto :eof
)

MODE CON: COLS=180
if exist "%1/"                   goto :repack
if %~x1  ==                .sco  goto :unpack
if %~nx1 == mission_objects.json goto :unpacked_reindex

goto :show_help

:unpack
    echo.[/] calling «mab_sco_unpack» %~1 && echo.    -- && title sco_unpack %~1
    "%~dp0/mab_sco_unpack" "%~1"
    goto :end

:unpacked_reindex
    echo.[/] calling «mab_sco_unpacked_reindex» %~dp1 && echo.    -- && title sco_unpacked_reindex %~dp1
    "%~dp0/mab_sco_unpacked_reindex" "%~dp1"
    goto :end

:repack
    echo.[/] calling «mab_sco_repack» %~1 && echo.    -- && title sco_repack %~1
    "%~dp0/mab_sco_repack" "%~1"
    goto :end

:end
    pause
    goto :eof