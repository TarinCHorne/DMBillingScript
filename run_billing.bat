@ECHO off

set "dir=%~dp0"
set "billing_script=Billing.py"
set "csv_file=Billing Sheet.csv"
set "csv_lock=.~lock.%csv_file%#"
set "script_path=%dir%%billing_script%"

IF EXIST "%dir%%csv_lock%" (
    ECHO ERROR %csv_file% file is currently open and locked by another application...
	PAUSE
	EXIT
) ELSE (
	.\python-venv\Scripts\python.exe %script_path% %*
	PAUSE
	EXIT
)