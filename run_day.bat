@echo off
rem run_day.bat -- weekly routine in one double-click.
rem
rem DRIVE points at the personal Google Drive mount (bpe0390@gmail.com = H:).
rem PAGES is this tool's own GitHub Pages working copy. It is deliberately NOT the
rem keiba-race repo: another project (C:\keiba-site) publishes there, and two working
rem copies pushing the same branch reject each other's pushes.
rem It is a PUBLIC site: anyone with the URL can read it.
rem   https://bunsekitool.github.io/race-view/
rem The company account stays mounted on G: and is not touched.
rem
rem EveryDB3's own import is NOT automated: its RACE FromTime advances to the run time
rem after every update, so this week's entries get skipped when it sits after the
rem Thursday/Friday delivery. Import in EveryDB3 first; if the data is missing this
rem script stops and tells you exactly what to change.

chcp 65001 > nul
cd /d "%~dp0"

set "DRIVE=H:\マイドライブ\keiba"
set "ECORE=C:\Users\fi394\AppData\Local\EveryDB3\ecore.db"
set "PAGES=C:\keiba-view"

python run_day.py --ecore "%ECORE%" --drive "%DRIVE%" --publish --pages "%PAGES%" %*

echo.
pause
