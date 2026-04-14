# TOTP Authenticator 🔐

A simple TOTP authenticator app with system tray support.

## Features ✨

- 📱 Generate TOTP codes for 2FA
- 💻 System tray support
- 🔒 Encrypted data storage
- 🎯 Easy to use GUI
- 📋 Copy to clipboard
- ➕ Add/Edit/Delete accounts
- 🔄 Auto-refresh codes

## Requirements 📦

- Python 3.6+
- tkinter
- pystray
- pillow
- cryptography

## Installation 🚀

```bash
# Install dependencies
pip install pystray pillow cryptography

# Run the app
python totp_bo.py
```

## Usage 📖

1. Run `python totp_bo.py`
2. Click "+" to add a new account
3. Enter account name and secret key
4. TOTP code will be generated automatically
5. Click on code to copy to clipboard

## Building EXE 🏗️

```bash
pip install pyinstaller
pyinstaller --onefile --windowed totp_bo.py
```

## License 📄

MIT License

## Author 👤

Created with ❤️
