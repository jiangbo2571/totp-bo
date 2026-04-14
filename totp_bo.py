import tkinter as tk
from tkinter import messagebox, simpledialog
import hmac
import hashlib
import struct
import time
import base64
import os
import json
import sys
import threading
import subprocess
from cryptography.fernet import Fernet

# --- 自动安装依赖库 ---
try:
    from PIL import Image, ImageDraw
    import pystray
except ImportError:
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "pystray", "pillow", "cryptography", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"], check=True)
        from PIL import Image, ImageDraw
        import pystray
    except:
        pass

APP_NAME = "TOTP Authenticator"

# --- 多语言字典配置 ---
LANG_DATA = {
    'en': {
        'title': 'AUTHENTICATOR',
        'add_new': 'Add New Account...',
        'copy': 'Copy',
        'delete': 'Delete',
        'opacity': 'Opacity',
        'width': 'Width',
        'hide': 'Hide to Tray',
        'quit': 'Quit Completely',
        'right_click_add': 'Right-click to add account',
        'saved': 'SAVED!',
        'confirm_del_title': 'Confirm Delete',
        'confirm_del_msg': "Are you sure you want to delete account '{}'?",
        'add_title': 'Add Account',
        'input_name': 'Account Name:',
        'input_secret': 'Secret (Base32):',
        'lang_select': 'Language',
        'show_ui': 'Show Main Window'
    },
    'zh': {
        'title': '身份验证器',
        'add_new': '添加新账户...',
        'copy': '复制',
        'delete': '删除',
        'opacity': '透明度设置',
        'width': '宽度调整',
        'hide': '隐藏到托盘',
        'quit': '彻底退出',
        'right_click_add': '右键添加账户',
        'saved': '已复制!',
        'confirm_del_title': '确认删除',
        'confirm_del_msg': "确定要删除账户 '{}' 吗？",
        'add_title': '添加账户',
        'input_name': '账户名称:',
        'input_secret': '密钥 (Base32):',
        'lang_select': '语言切换',
        'show_ui': '显示主界面'
    },
    'ru': {
        'title': 'АУТЕНТИФИКАТОР',
        'add_new': 'Добавить аккаунт...',
        'copy': 'Копировать',
        'delete': 'Удалить',
        'opacity': 'Прозрачность',
        'width': 'Ширина',
        'hide': 'Скрыть в трей',
        'quit': 'Выход',
        'right_click_add': 'ПКМ для добавления',
        'saved': 'СКОПИРОВАНО!',
        'confirm_del_title': 'Удаление',
        'confirm_del_msg': "Удалить аккаунт '{}'?",
        'add_title': 'Новый аккаунт',
        'input_name': 'Имя аккаунта:',
        'input_secret': 'Ключ (Base32):',
        'lang_select': 'Язык',
        'show_ui': 'Показать окно'
    },
    'de': {
        'title': 'AUTHENTICATOR',
        'add_new': 'Konto hinzufügen...',
        'copy': 'Kopieren',
        'delete': 'Löschen',
        'opacity': 'Deckkraft',
        'width': 'Breite',
        'hide': 'In Tray minimieren',
        'quit': 'Beenden',
        'right_click_add': 'Rechtsklick zum Hinzufügen',
        'saved': 'KOPIERT!',
        'confirm_del_title': 'Löschen bestätigen',
        'confirm_del_msg': "Konto '{}' wirklich löschen?",
        'add_title': 'Konto hinzufügen',
        'input_name': 'Kontoname:',
        'input_secret': 'Geheimnis (Base32):',
        'lang_select': 'Sprache',
        'show_ui': 'Fenster anzeigen'
    }
}

# --- 路径兼容性处理 ---
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

DATA_FILE = get_resource_path("totp_data.dat")
CONFIG_FILE = get_resource_path("totp_config.json")

class TOTPGenerator:
    def __init__(self, secret: str, digits: int = 6, interval: int = 30):
        self.secret = secret
        self.digits = digits
        self.interval = interval

    def get_totp(self, timestamp: float = None) -> str:
        if timestamp is None: timestamp = time.time()
        counter = int(timestamp) // self.interval
        return self._generate_totp(counter)

    def _generate_totp(self, counter: int) -> str:
        try:
            msg = struct.pack('>Q', counter)
            secret_bytes = self._decode_base32(self.secret.upper().replace(' ', '').replace('-', ''))
            hmac_result = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
            offset = hmac_result[-1] & 0x0F
            binary = (struct.unpack('>I', hmac_result[offset:offset+4])[0] & 0x7FFFFFFF)
            otp = binary % (10 ** self.digits)
            return str(otp).zfill(self.digits)
        except:
            return "ERR!"

    def _decode_base32(self, secret: str) -> bytes:
        alphabet = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
        secret = secret.upper().strip()
        bits = ''
        for char in secret:
            if char == '=': continue
            try:
                val = alphabet.index(char)
                bits += format(val, '05b')
            except ValueError: continue
        result = []
        for i in range(0, len(bits) - 7, 8):
            result.append(chr(int(bits[i:i+8], 2)))
        return ''.join(result).encode()

    def get_remaining_seconds(self) -> float:
        return self.interval - (time.time() % self.interval)

    def get_progress(self) -> float:
        return self.get_remaining_seconds() / self.interval

class AuthenticatorApp:
    def __init__(self):
        self.window = tk.Tk()
        self.window.withdraw()

        # 默认配置
        self.config = {'x': 100, 'y': 100, 'alpha': 0.92, 'width': 260, 'lang': 'en'}
        self.load_config()
        
        self.accounts = {}
        self.copy_feedback = {} 
        self.load_data()
        
        self.setup_widget()
        self.setup_tray()
        
        self.refresh()
        self.window.mainloop()

    @property
    def txt(self):
        """动态获取当前语言文本包"""
        return LANG_DATA.get(self.config.get('lang', 'en'), LANG_DATA['en'])

    def create_tray_icon(self):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color='#1a1a2e')
        dc = ImageDraw.Draw(image)
        dc.rectangle([10, 10, 54, 54], fill='#8b8bff')
        return image

    def setup_tray(self):
        try:
            icon_image = self.create_tray_icon()
            self.tray_icon = pystray.Icon("totp_icon", icon_image, APP_NAME)
            self.update_tray_menu()
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except:
            pass

    def update_tray_menu(self):
        """刷新托盘菜单语言"""
        menu = pystray.Menu(
            pystray.MenuItem(self.txt['show_ui'], self.show_widget),
            pystray.MenuItem(self.txt['quit'], self.quit_app)
        )
        self.tray_icon.menu = menu

    def setup_widget(self):
        self.widget = tk.Toplevel()
        self.widget.overrideredirect(True)
        self.widget.attributes('-topmost', True)
        self.widget.attributes('-alpha', self.config.get('alpha', 0.92))
        self.widget.configure(bg='#1a1a2e')

        self.update_window_size()

        self.canvas = tk.Canvas(self.widget, bg='#1a1a2e', highlightthickness=0, bd=0)
        self.canvas.pack(fill='both', expand=True)

        self.drag_data = {'x': 0, 'y': 0}
        self.widget.bind('<Button-1>', self.on_click_handler)
        self.widget.bind('<B1-Motion>', self.on_drag_motion)
        self.canvas.bind('<Button-3>', self.show_context_menu)
        
        self.canvas.bind('<Enter>', lambda e: self.widget.attributes('-alpha', 1.0))
        self.canvas.bind('<Leave>', lambda e: self.widget.attributes('-alpha', self.config.get('alpha', 0.92)))

        self.refresh_canvas()

    def show_widget(self):
        self.widget.deiconify()
        self.widget.attributes('-topmost', True)

    def hide_widget(self):
        self.widget.withdraw()

    def show_context_menu(self, event):
        menu = tk.Menu(self.widget, tearoff=0, bg='#2d2d4a', fg='white', font=('Segoe UI', 9), activebackground='#4a4a8a')
        
        target_account = None
        if 40 <= event.y <= self.widget.winfo_height():
            idx = (event.y - 40) // 60
            account_names = list(self.accounts.keys())
            if 0 <= idx < len(account_names):
                target_account = account_names[idx]

        if target_account:
            menu.add_command(label=f"{self.txt['copy']}: {target_account}", command=lambda: self.copy_to_clipboard(target_account))
            menu.add_command(label=f"{self.txt['delete']}: {target_account}", command=lambda: self.delete_account(target_account))
            menu.add_separator()

        menu.add_command(label=self.txt['add_new'], command=self.add_account)
        
        # 语言子菜单
        lang_menu = tk.Menu(menu, tearoff=0, bg='#2d2d4a', fg='white')
        lang_menu.add_command(label="English", command=lambda: self.set_language('en'))
        lang_menu.add_command(label="简体中文", command=lambda: self.set_language('zh'))
        lang_menu.add_command(label="Deutsch", command=lambda: self.set_language('de'))
        lang_menu.add_command(label="Русский", command=lambda: self.set_language('ru'))
        menu.add_cascade(label=self.txt['lang_select'], menu=lang_menu)

        alpha_menu = tk.Menu(menu, tearoff=0, bg='#2d2d4a', fg='white')
        for a in [100, 90, 80, 70, 60]:
            alpha_menu.add_command(label=f'{a}%', command=lambda v=a/100: self.set_alpha(v))
        menu.add_cascade(label=self.txt['opacity'], menu=alpha_menu)

        size_menu = tk.Menu(menu, tearoff=0, bg='#2d2d4a', fg='white')
        for w in [200, 260, 320]:
            size_menu.add_command(label=f'{w}px', command=lambda v=w: self.set_width(v))
        menu.add_cascade(label=self.txt['width'], menu=size_menu)

        menu.add_separator()
        menu.add_command(label=self.txt['hide'], command=self.hide_widget)
        menu.add_command(label=self.txt['quit'], command=self.quit_app)
        
        menu.post(event.x_root, event.y_root)

    def set_language(self, lang_code):
        self.config['lang'] = lang_code
        self.save_config()
        self.update_tray_menu()
        self.refresh_canvas()

    def delete_account(self, name):
        if messagebox.askyesno(self.txt['confirm_del_title'], self.txt['confirm_del_msg'].format(name)):
            if name in self.accounts:
                del self.accounts[name]
                self.save_data()
                self.update_window_size()

    def on_click_handler(self, event):
        self.drag_data['x'], self.drag_data['y'] = event.x, event.y
        if 40 <= event.y <= self.widget.winfo_height():
            idx = (event.y - 40) // 60
            account_names = list(self.accounts.keys())
            if 0 <= idx < len(account_names):
                self.copy_to_clipboard(account_names[idx])

    def copy_to_clipboard(self, name):
        if name not in self.accounts: return
        secret, digits, interval = self.accounts[name]
        code = TOTPGenerator(secret, digits, interval).get_totp()
        self.window.clipboard_clear()
        self.window.clipboard_append(code)
        self.copy_feedback[name] = time.time()
        self.refresh_canvas()

    def set_alpha(self, value):
        self.config['alpha'] = value
        self.widget.attributes('-alpha', value)
        self.save_config()

    def set_width(self, value):
        self.config['width'] = value
        self.update_window_size()
        self.save_config()

    def update_window_size(self):
        w = self.config.get('width', 260)
        h = 45 + len(self.accounts) * 60 
        screen_h = self.widget.winfo_screenheight()
        h = max(80, min(h, screen_h - 100))
        
        x = self.config.get('x', self.widget.winfo_x())
        y = self.config.get('y', self.widget.winfo_y())
        self.widget.geometry(f'{w}x{int(h)}+{x}+{y}')

    def on_drag_motion(self, event):
        dx, dy = event.x - self.drag_data['x'], event.y - self.drag_data['y']
        x, y = self.widget.winfo_x() + dx, self.widget.winfo_y() + dy
        self.widget.geometry(f'+{x}+{y}')
        self.config['x'], self.config['y'] = x, y

    def refresh_canvas(self):
        self.canvas.delete('all')
        ww, wh = self.widget.winfo_width(), self.widget.winfo_height()

        self.canvas.create_rectangle(0, 0, ww, wh, fill='#1a1a2e', outline='#3d3d6b', width=1)
        self.canvas.create_text(ww//2, 15, text=self.txt['title'], font=('Segoe UI', 7, 'bold'), fill='#5c5c8a')

        if not self.accounts:
            self.canvas.create_text(ww//2, wh//2, text=self.txt['right_click_add'], font=('Segoe UI', 8), fill='#444466')
            return

        y = 40
        now = time.time()
        for name, (secret, digits, interval) in self.accounts.items():
            try:
                totp = TOTPGenerator(secret, digits, interval)
                code = totp.get_totp()
                next_code = totp.get_totp(now + interval)
                remaining = totp.get_remaining_seconds()
                progress = totp.get_progress()

                is_copied = name in self.copy_feedback and (now - self.copy_feedback[name] < 1.0)
                code_color = '#00ff88' if is_copied else '#ffffff'
                code_text = self.txt['saved'] if is_copied else f'{code[:3]} {code[3:]}'

                # 账户名（俄语和德语较长，限制显示长度）
                self.canvas.create_text(15, y, text=name.upper()[:18], font=('Segoe UI', 7, 'bold'), fill='#7777aa', anchor='w')
                self.canvas.create_text(15, y+18, text=code_text, font=('Consolas', 15, 'bold'), fill=code_color, anchor='w')
                
                # 下一组预览
                self.canvas.create_text(ww - 15, y+4, text=next_code, font=('Consolas', 10, 'bold'), fill='#ffffff', anchor='e')
                
                # 剩余时间
                timer_color = '#ff4444' if remaining <= 5 else '#8b8bff'
                self.canvas.create_text(ww - 15, y+21, text=f'{int(remaining)}s', font=('Segoe UI', 9, 'bold'), fill=timer_color, anchor='e')

                # 进度条
                bar_w = ww - 30
                self.canvas.create_rectangle(15, y+34, 15+bar_w, y+36, fill='#2d2d4a', outline='')
                color = '#4a4a8a' if remaining > 5 else '#ff4444'
                self.canvas.create_rectangle(15, y+34, 15+(bar_w * progress), y+36, fill=color, outline='')
                
                y += 60 
            except:
                y += 30

    def refresh(self):
        if hasattr(self, 'canvas'): self.refresh_canvas()
        self.window.after(500, self.refresh)

    def add_account(self):
        name = simpledialog.askstring(self.txt['add_title'], self.txt['input_name'], parent=self.widget)
        secret = simpledialog.askstring(self.txt['add_title'], self.txt['input_secret'], parent=self.widget)
        if name and secret:
            final_name = name
            count = 1
            while final_name in self.accounts:
                final_name = f"{name}_{count}"
                count += 1
            # 默认 6位/30秒
            self.accounts[final_name] = (secret.upper().replace(' ', ''), 6, 30)
            self.save_data()
            self.update_window_size()

    def load_data(self):
        if not os.path.exists(DATA_FILE): return
        try:
            # 派生加密密钥
            key = hashlib.sha256(b'totp_secret_key_v1_github').digest()
            fernet_key = base64.urlsafe_b64encode(key[:32].ljust(32, b'=')[:32])
            cipher = Fernet(fernet_key)
            self.accounts = json.loads(cipher.decrypt(open(DATA_FILE, 'rb').read()))
        except: self.accounts = {}

    def save_data(self):
        try:
            key = hashlib.sha256(b'totp_secret_key_v1_github').digest()
            fernet_key = base64.urlsafe_b64encode(key[:32].ljust(32, b'=')[:32])
            cipher = Fernet(fernet_key)
            open(DATA_FILE, 'wb').write(cipher.encrypt(json.dumps(self.accounts).encode()))
        except: pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config.update(json.load(f))
            except: pass

    def save_config(self):
        try:
            if hasattr(self, 'widget'):
                self.config['x'] = self.widget.winfo_x()
                self.config['y'] = self.widget.winfo_y()
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except: pass

    def quit_app(self, icon=None, item=None):
        self.save_config()
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.window.quit()
        sys.exit(0)

if __name__ == '__main__':
    AuthenticatorApp()