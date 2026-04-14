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
        subprocess.run([sys.executable, "-m", "pip", "install", "pystray", "pillow", "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"], check=True)
        from PIL import Image, ImageDraw
        import pystray
    except:
        pass

APP_NAME = "TOTP Authenticator"

# --- 路径兼容性处理：确保访问 EXE 同级目录 ---
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        # 打包环境：指向 EXE 所在的文件夹
        base_path = os.path.dirname(sys.executable)
    else:
        # 开发环境：指向 py 脚本所在的文件夹
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
        msg = struct.pack('>Q', counter)
        secret_bytes = self._decode_base32(self.secret.upper().replace(' ', '').replace('-', ''))
        hmac_result = hmac.new(secret_bytes, msg, hashlib.sha1).digest()
        offset = hmac_result[-1] & 0x0F
        binary = (struct.unpack('>I', hmac_result[offset:offset+4])[0] & 0x7FFFFFFF)
        otp = binary % (10 ** self.digits)
        return str(otp).zfill(self.digits)

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

        self.config = {'x': 100, 'y': 100, 'alpha': 0.92, 'width': 260}
        self.load_config()
        
        self.accounts = {}
        self.copy_feedback = {} 
        self.load_data()
        
        self.setup_widget()
        self.setup_tray()
        
        self.refresh()
        self.window.mainloop()

    def create_tray_icon(self):
        width, height = 64, 64
        image = Image.new('RGB', (width, height), color='#1a1a2e')
        dc = ImageDraw.Draw(image)
        dc.rectangle([10, 10, 54, 54], fill='#8b8bff')
        return image

    def setup_tray(self):
        try:
            icon_image = self.create_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem("显示主界面", self.show_widget),
                pystray.MenuItem("退出程序", self.quit_app)
            )
            self.tray_icon = pystray.Icon("totp_icon", icon_image, APP_NAME, menu)
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except:
            pass

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
            menu.add_command(label=f'复制: {target_account}', command=lambda: self.copy_to_clipboard(target_account))
            menu.add_command(label=f'删除: {target_account}', command=lambda: self.delete_account(target_account))
            menu.add_separator()

        menu.add_command(label='添加新账户...', command=self.add_account)
        
        alpha_menu = tk.Menu(menu, tearoff=0, bg='#2d2d4a', fg='white')
        for a in [100, 90, 80, 70, 60]:
            alpha_menu.add_command(label=f'{a}%', command=lambda v=a/100: self.set_alpha(v))
        menu.add_cascade(label='透明度设置', menu=alpha_menu)

        size_menu = tk.Menu(menu, tearoff=0, bg='#2d2d4a', fg='white')
        for w in [200, 260, 320]:
            size_menu.add_command(label=f'{w}px', command=lambda v=w: self.set_width(v))
        menu.add_cascade(label='宽度调整', menu=size_menu)

        menu.add_separator()
        menu.add_command(label='隐藏到托盘', command=self.hide_widget)
        menu.add_command(label='彻底退出', command=self.quit_app)
        
        menu.post(event.x_root, event.y_root)

    def delete_account(self, name):
        if messagebox.askyesno("确认删除", f"确定要删除账户 '{name}' 吗？"):
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
        self.canvas.create_text(ww//2, 15, text="AUTHENTICATOR", font=('Segoe UI', 7, 'bold'), fill='#5c5c8a')

        if not self.accounts:
            self.canvas.create_text(ww//2, wh//2, text='右键添加账户', font=('Segoe UI', 8), fill='#444466')
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
                code_text = "SAVED!" if is_copied else f'{code[:3]} {code[3:]}'

                self.canvas.create_text(15, y, text=name.upper()[:15], font=('Segoe UI', 7, 'bold'), fill='#7777aa', anchor='w')
                self.canvas.create_text(15, y+18, text=code_text, font=('Consolas', 15, 'bold'), fill=code_color, anchor='w')
                
                # 下一组数字
                self.canvas.create_text(ww - 15, y+4, text=next_code, font=('Consolas', 11, 'bold'), fill='#ffffff', anchor='e')
                
                # 倒计时
                timer_color = '#ff4444' if remaining <= 5 else '#8b8bff'
                self.canvas.create_text(ww - 15, y+21, text=f'{int(remaining)}s', font=('Segoe UI', 9, 'bold'), fill=timer_color, anchor='e')

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
        name = simpledialog.askstring("添加", "账户名称:", parent=self.widget)
        secret = simpledialog.askstring("添加", "密钥 (Base32):", parent=self.widget)
        if name and secret:
            final_name = name
            count = 1
            while final_name in self.accounts:
                final_name = f"{name}_{count}"
                count += 1
            self.accounts[final_name] = (secret.upper().replace(' ', ''), 6, 30)
            self.save_data()
            self.update_window_size()

    def load_data(self):
        if not os.path.exists(DATA_FILE): return
        try:
            key = hashlib.sha256(b'totp_secret_key_v1').digest()
            fernet_key = base64.urlsafe_b64encode(key[:32].ljust(32, b'=')[:32])
            cipher = Fernet(fernet_key)
            self.accounts = json.loads(cipher.decrypt(open(DATA_FILE, 'rb').read()))
        except: self.accounts = {}

    def save_data(self):
        try:
            key = hashlib.sha256(b'totp_secret_key_v1').digest()
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