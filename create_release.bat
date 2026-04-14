@echo off
echo Creating GitHub Release v1.0.0...

cd /d "D:\Desktop\totp-bo"

:: Create release
"C:\Program Files\GitHub CLI\gh.exe" release create v1.0.0 --title "TOTP Authenticator v1.0.0" --notes "
## 🎉 First Release!

### Features ✨
- Generate TOTP codes for 2FA
- System tray support
- Encrypted data storage
- Easy to use GUI
- Copy to clipboard
- Add/Edit/Delete accounts
- Auto-refresh codes

### Installation 📦
Download and run TOTP_Authenticator.exe

### Requirements
- Windows 10/11
- No additional dependencies needed

### Known Issues ⚠️
- First run may take a few seconds to start
" dist\TOTP_Authenticator.exe

echo.
echo ==========================================
echo Release created successfully!
echo URL: https://github.com/jiangbo2571/totp-bo/releases/tag/v1.0.0
echo ==========================================
echo.
pause
