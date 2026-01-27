@echo off
setlocal

:: 1. Change drive and navigate to the working directory
M:
cd "M:\Project\ManufTools\LabelPrint"

:: 2. Define the list of serials (separated by spaces)
set "serials=RC-110-333456 RC-110-333457 RC-110-333458"

:: 3. Loop through each serial and run the program
for %%s in (%serials%) do (
    echo Processing serial: %%s
    :: Use /wait if you want the script to wait until one label is printed before starting the next
    start /wait "" "LabelPrinter.exe" --s=%%s
)

echo Done!
pause
exit