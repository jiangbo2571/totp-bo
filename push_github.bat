@echo off
echo Creating GitHub repository...

cd /d "D:\Desktop\totp-bo"

:: Add totp_bo.py if exists
if exist totp_bo.py (
    git add totp_bo.py
    git commit -m "Add totp_bo.py"
)

:: Create repo and push
"C:\Program Files\GitHub CLI\gh.exe" repo create totp-bo --public --description "TOTP Authenticator - A simple TOTP authenticator app with system tray support" --push

echo.
echo ==========================================
echo Done! Repository created successfully!
echo URL: https://github.com/yourusername/totp-bo
echo ==========================================
echo.
pause
