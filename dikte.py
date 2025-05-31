import time
import threading
import keyboard
import pyautogui
import pyperclip
from selenium.webdriver.chrome.service import Service
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import tkinter as tk
from PIL import Image, ImageTk
import os
import sys
from pathlib import Path
import atexit
import signal
import tempfile
from webdriver_manager.chrome import ChromeDriverManager

if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(__file__)

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    return os.path.join(base_path, relative_path)

mic_path = os.path.join(application_path, 'mic.png')
mic_mute_path = os.path.join(application_path, 'mic_Mute.png')
loading_path = os.path.join(application_path, 'loading.png')


driver = None
last_text = ""
monitoring = False
app_running = False
driver_active = False
mic_button = None

def cleanup():
    global driver
    if driver:
        try:
            driver.quit()
            print("Driver kapatıldı.")
        except Exception:
            pass



def create_driver_with_user_profile():
    chrome_options = Options()
    user_profile_path = os.path.join(str(Path.home()), "chromeprofile")
    chrome_options.add_argument(f"--user-data-dir={user_profile_path}")
    chrome_options.add_argument('--headless=new')  # İstersen bunu da ekle
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--no-sandbox')
    prefs = {
        "profile.default_content_setting_values.media_stream_mic": 1,
        "profile.default_content_setting_values.notifications": 1,
    }
    chrome_options.add_experimental_option("prefs", prefs)

    # Otomatik olarak uyumlu sürümü indirir
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=chrome_options)


def monitor_notepad():
    global last_text, monitoring
    print("Dikte izleniyor...")
    while monitoring:
        try:
            paragraphs = driver.find_elements(By.CSS_SELECTOR, "div.notepad p")
            full_text = "\n".join(p.text for p in paragraphs if p.text.strip())
            if full_text != last_text:
                new_text = full_text[len(last_text):]
                INVISIBLE_CHAR = '\u200B'
                keyboard.write(new_text, delay=0.03)
                last_text = full_text
            time.sleep(0.2)
        except Exception as e:
            print(f"İzleme hatası: {e}")
            break

loading_window = None

def show_loading_animation():
    global loading_window
    loading_window = tk.Toplevel()
    loading_window.overrideredirect(True)
    loading_window.attributes("-topmost", True)
    screen_width = loading_window.winfo_screenwidth()
    screen_height = loading_window.winfo_screenheight()
    loading_image = Image.open(resource_path("loading.png"))
    loading_image = loading_image.resize((70, 70), Image.Resampling.LANCZOS)
    loading_icon = ImageTk.PhotoImage(loading_image)
    loading_label = tk.Label(loading_window, image=loading_icon, bg="white")
    loading_label.image = loading_icon
    loading_label.pack()
    x = (screen_width // 2) - 35
    y = (screen_height // 2) - 35
    loading_window.geometry("70x70+{}+{}".format(x, y))
    loading_window.update()

def hide_loading_animation():
    global loading_window
    if loading_window:
        loading_window.destroy()
        loading_window = None

def start_or_stop_dictation():
    global driver, monitoring, last_text, app_running, mic_button
    if not app_running:
        try:
            show_loading_animation()
            driver = create_driver_with_user_profile()
            driver.get("https://dictation.io/speech")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.btn__text.listen"))
            )
            driver.find_element(By.CSS_SELECTOR, "span.btn__text.listen").click()
            print("Start butonuna tıklandı.")
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.notepad"))
            )
            driver.execute_script("""
                const ps = document.querySelectorAll("div.notepad p");
                ps.forEach(p => p.textContent = "");
            """)
            last_text = ""
            monitoring = True
            app_running = True
            threading.Thread(target=monitor_notepad, daemon=True).start()
            img = Image.open(resource_path("mic.png")).resize((32, 32), Image.Resampling.LANCZOS)
            mic_icon = ImageTk.PhotoImage(img)
            mic_button.config(image=mic_icon)
            mic_button.image = mic_icon
            hide_loading_animation()
        except Exception as e:
            print(f"Hata: {e}")
    else:
        monitoring = False
        app_running = False
        if driver:
            driver.quit()
            driver = None
        print("Dikte durduruldu.")
        img = Image.open(resource_path("mic_Mute.png")).resize((32, 32), Image.Resampling.LANCZOS)
        mic_icon = ImageTk.PhotoImage(img)
        mic_button.config(image=mic_icon)
        mic_button.image = mic_icon

def listen_for_shortcut():
    keyboard.add_hotkey("alt+a", start_or_stop_dictation)
    keyboard.wait()

def launch_gui():
    global mic_button
    root = tk.Tk()
    root.resizable(False, False)
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    window_width = 70
    window_height = 85
    x = screen_width - window_width - 10
    y = (screen_height - window_height - (window_height // 2)) // 2
    root.geometry(f"{window_width}x{window_height}+{x}+{y}")
    img = Image.open(resource_path("mic_Mute.png"))
    img = img.resize((32, 32), Image.Resampling.LANCZOS)
    icon = ImageTk.PhotoImage(img)
    mic_button = tk.Button(root, image=icon, command=start_or_stop_dictation, borderwidth=0)
    mic_button.image = icon
    mic_button.pack(pady=(10, 0))
    close_button = tk.Button(root, text="✕", command=root.destroy, borderwidth=0, fg="red", bg="white", font=("Arial", 10))
    close_button.pack(pady=(5, 0))
    threading.Thread(target=listen_for_shortcut, daemon=True).start()
    root.mainloop()

if __name__ == "__main__":
    launch_gui()

atexit.register(cleanup)

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)
