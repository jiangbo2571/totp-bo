@echo off
echo Creating GitHub repository and uploading totp_bo.py...

cd /d "D:\Desktop\totp-bo"

:: Initialize git repo
git init
git add totp_bo.py
git add .gitignore
git commit -m "Initial commit: TOTP Authenticator"

:: Create GitHub repo and push
gh repo create totp-bo --public --description "TOTP Authenticator - A simple TOTP authenticator app with system tray support" --push

echo Done!
pause
