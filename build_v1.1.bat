@echo off
echo Building TOTP Authenticator v1.1 with multi-language support...

cd /d "D:\Desktop\totp-bo"

:: Build with icon
pyinstaller --onefile --windowed --name "TOTP_Authenticator_v1.1" --icon=icon.ico --add-data "icon.png;." totp_bo.py

echo.
echo Build complete!
pause
