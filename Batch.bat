@echo off

REM Step 1: Open terminal in kept  D:\__Rohit\Hperspectral\Project\Organization\HYPRIL
cd /d %cd%

REM Step 2: Activate conda environment
CALL conda activate HYPRIL

cls
REM Step 3: Open VS Code in current folder
start code .

REM Step 4: Run Python script
python auto_run.py

REM Keep terminal open
cmd /k
