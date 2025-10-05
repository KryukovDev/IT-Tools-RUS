"""
PhotoNumberer v2.0
Автоматическая нумерация фотографий

Copyright (c) 2025 Александр Крюков (Kryukov{}Dev)
Лицензия: MIT License

Telegram: https://t.me/it_tools_rus
GitHub: https://github.com/KryukovDev/IT-Tools-RUS
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
import platform
from threading import Thread
from datetime import datetime
import webbrowser
import sys
import tempfile

def resource_path(relative_path):
    """Получает абсолютный путь к ресурсу. Работает для dev и для PyInstaller"""
    try:
        # PyInstaller создает временную папку и хранит путь в _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class PhotoNumbererApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PhotoNumberer v2.0")
        self.root.geometry("800x650")
        self.root.minsize(700, 600)

        self.root.iconbitmap(resource_path("icon.ico"))
        
        # Стиль
        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TLabel', background='#f0f0f0')
        self.style.configure('Header.TLabel', background='#2c3e50', foreground='white', font=('Arial', 12, 'bold'))
        
        # Переменные
        self.source_folder = tk.StringVar()
        self.output_folder = tk.StringVar(value=os.path.join(os.getcwd(), "numbered_photos"))
        self.start_number = tk.IntVar(value=1)
        self.position = tk.StringVar(value="bottom_center")
        self.overwrite = tk.BooleanVar(value=False)
        self.font_size = tk.IntVar(value=50)
        
        self.create_widgets()
        self.setup_fonts()
        
    def setup_fonts(self):
        # Определяем путь к шрифту в зависимости от ОС
        if platform.system() == "Windows":
            self.font_path = "C:/Windows/Fonts/arialbd.ttf"  # Жирный Arial
        elif platform.system() == "Darwin":  # macOS
            self.font_path = "/Library/Fonts/Arial Bold.ttf"
        else:  # Linux
            self.font_path = "/usr/share/fonts/truetype/freefont/FreeMonoBold.ttf"
        
    def create_widgets(self):
        # Главный фрейм
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Заголовок
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(header_frame, text="🖼️ PhotoNumberer", style='Header.TLabel', 
                 anchor='center').pack(fill=tk.X, padx=5, pady=5)
        
        # Фрейм настроек
        settings_frame = ttk.LabelFrame(main_frame, text="Настройки", padding="10")
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Исходная папка
        ttk.Label(settings_frame, text="Исходная папка:").grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(settings_frame, textvariable=self.source_folder, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(settings_frame, text="Обзор...", command=self.browse_source).grid(row=0, column=2)
        
        # Выходная папка
        ttk.Label(settings_frame, text="Выходная папка:").grid(row=1, column=0, sticky=tk.W, pady=2)
        ttk.Entry(settings_frame, textvariable=self.output_folder, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(settings_frame, text="Обзор...", command=self.browse_output).grid(row=1, column=2)
        
        # Дополнительные настройки
        ttk.Label(settings_frame, text="Начальный номер:").grid(row=2, column=0, sticky=tk.W, pady=2)
        ttk.Spinbox(settings_frame, from_=1, to=9999, textvariable=self.start_number, width=10).grid(row=2, column=1, sticky=tk.W, padx=5)
        
        ttk.Label(settings_frame, text="Позиция номера:").grid(row=3, column=0, sticky=tk.W, pady=2)
        position_combo = ttk.Combobox(settings_frame, textvariable=self.position, 
                                     values=["bottom_center", "top_right", "top_left", "bottom_right"], 
                                     state="readonly", width=15)
        position_combo.grid(row=3, column=1, sticky=tk.W, padx=5)
        
        ttk.Checkbutton(settings_frame, text="Перезаписывать существующие файлы", 
                       variable=self.overwrite).grid(row=4, column=1, sticky=tk.W, pady=2)
        
        # Кнопки управления
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.run_button = ttk.Button(button_frame, text="🚀 Начать нумерацию", 
                                   command=self.start_processing, style='Accent.TButton')
        self.run_button.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="🧹 Очистить логи", 
                  command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="📂 Открыть папку с результатами", 
                  command=self.open_output_folder).pack(side=tk.RIGHT, padx=5)
        
        # Область логов
        log_frame = ttk.LabelFrame(main_frame, text="Логи выполнения", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, height=12, state="disabled", wrap=tk.WORD)
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Статус бар
        self.status_var = tk.StringVar(value="Готов к работе")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Прогресс-бар
        self.progress = ttk.Progressbar(self.root, mode='indeterminate')
        self.progress.pack(side=tk.BOTTOM, fill=tk.X)

        self.create_footer()
    
    def create_footer(self):
        footer_frame = ttk.Frame(self.root)
        footer_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Кликабельная ссылка (работает даже без ТГ)
        link_label = ttk.Label(footer_frame, 
                              text="📢 Еще утилиты: t.me/it_tools_rus", 
                              foreground="blue",
                              cursor="hand2")
        link_label.pack(side=tk.RIGHT)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/it_tools_rus"))
        
        ttk.Label(footer_frame, text="Kryukov{}Dev © 2025", 
                 foreground="gray").pack(side=tk.LEFT)
        
    def browse_source(self):
        folder = filedialog.askdirectory(title="Выберите исходную папку с фото")
        if folder:
            self.source_folder.set(folder)
            # Автоматически создаем предложение для выходной папки
            suggested_output = os.path.join(folder, "numbered_photos")
            self.output_folder.set(suggested_output)
            
    def browse_output(self):
        folder = filedialog.askdirectory(title="Выберите папку для сохранения")
        if folder:
            self.output_folder.set(folder)
            
    def log_message(self, message):
        """Вывод сообщения в лог с временной меткой"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        self.log_area.configure(state="normal")
        self.log_area.insert(tk.END, formatted_message + "\n")
        self.log_area.see(tk.END)
        self.log_area.configure(state="disabled")
        
    def clear_logs(self):
        """Очистка логов"""
        self.log_area.configure(state="normal")
        self.log_area.delete(1.0, tk.END)
        self.log_area.configure(state="disabled")
        self.log_message("Логи очищены")
        
    def open_output_folder(self):
        """Открытие папки с результатами в проводнике"""
        output_path = self.output_folder.get()
        if os.path.exists(output_path):
            os.startfile(output_path) if platform.system() == "Windows" else os.system(f'open "{output_path}"' if platform.system() == "Darwin" else f'xdg-open "{output_path}"')
        else:
            messagebox.showwarning("Внимание", "Папка с результатами не существует!")
            
    def start_processing(self):
        """Запуск обработки"""
        if not self.source_folder.get():
            messagebox.showerror("Ошибка", "Выберите исходную папку!")
            return
            
        if not os.path.exists(self.source_folder.get()):
            messagebox.showerror("Ошибка", "Исходная папка не существует!")
            return
            
        # Блокируем интерфейс на время обработки
        self.set_ui_state(False)
        self.progress.start(10)
        self.status_var.set("Обработка...")
        self.log_message("=" * 50)
        self.log_message("🔄 Начинаю обработку фотографий...")
        
        # Запуск в отдельном потоке
        thread = Thread(target=self.process_photos, daemon=True)
        thread.start()
        
    def set_ui_state(self, enabled):
        """Включение/выключение элементов UI"""
        state = "normal" if enabled else "disabled"
        self.run_button.config(state=state)
        
    def process_photos(self):
        """Основной процесс обработки фотографий"""
        try:
            success_count = self.number_photos(
                self.source_folder.get(),
                self.output_folder.get(),
                self.start_number.get(),
                self.position.get(),
                self.overwrite.get()
            )
            
            self.root.after(0, lambda: self.processing_finished(success_count))
            
        except Exception as e:
            self.root.after(0, lambda: self.processing_error(str(e)))
            
    def number_photos(self, folder_path, output_folder, start_number, position, overwrite=False):
        """Модифицированная функция нумерации фото"""
        if not overwrite and not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        images = [f for f in os.listdir(folder_path) 
                 if os.path.splitext(f)[1].lower() in image_extensions]
        images.sort()
        
        self.root.after(0, lambda: self.log_message(f"📁 Найдено {len(images)} фото"))
        
        success_count = 0
        
        for i, image_name in enumerate(images, start_number):
            try:
                image_path = os.path.join(folder_path, image_name)
                with Image.open(image_path) as img:
                    if img.mode != 'RGB':
                        img = img.convert('RGB')
                    
                    draw = ImageDraw.Draw(img)
                    
                    # Адаптивный размер шрифта
                    font_size_actual = min(img.width, img.height) // 20
                    font_size_actual = max(font_size_actual, 30)
                    
                    try:
                        font = ImageFont.truetype(self.font_path, font_size_actual)
                    except:
                        font = ImageFont.load_default()
                    
                    text = str(i)
                    
                    # Получаем размеры текста
                    try:
                        bbox = draw.textbbox((0, 0), text, font=font)
                        text_width = bbox[2] - bbox[0]
                        text_height = bbox[3] - bbox[1]
                    except:
                        text_width, text_height = draw.textsize(text, font=font)
                    
                    margin = min(img.width, img.height) // 30
                    
                    # Определяем позицию
                    if position == "bottom_center":
                        x = (img.width - text_width) // 2
                        y = img.height - text_height - margin
                    elif position == "top_right":
                        x = img.width - text_width - margin
                        y = margin
                    elif position == "top_left":
                        x = margin
                        y = margin
                    elif position == "bottom_right":
                        x = img.width - text_width - margin
                        y = img.height - text_height - margin
                    
                    # Фон для текста
                    bg_padding = margin // 2
                    draw.rectangle([
                        x - bg_padding, 
                        y - bg_padding // 2,
                        x + text_width + bg_padding, 
                        y + text_height + bg_padding // 2
                    ], fill="black")
                    
                    # Текст
                    draw.text((x, y), text, fill="white", font=font)
                    
                    # Сохранение
                    name, ext = os.path.splitext(image_name)
                    output_filename = f"{name}_{i:04d}{ext}" if overwrite else f"{i:04d}{ext}"
                    output_path = os.path.join(output_folder, output_filename)
                    
                    img.save(output_path, quality=95)
                    self.root.after(0, lambda n=image_name, o=output_filename: self.log_message(f"✅ {n} → {o}"))
                    success_count += 1
                    
            except Exception as e:
                self.root.after(0, lambda n=image_name, e=e: self.log_message(f"❌ Ошибка с {n}: {str(e)}"))
        
        return success_count
        
    def processing_finished(self, success_count):
        """Завершение обработки"""
        self.progress.stop()
        self.set_ui_state(True)
        self.status_var.set(f"Готово! Обработано: {success_count} фото")
        self.log_message(f"✅ Готово! Успешно обработано: {success_count} фото")
        self.log_message("=" * 50)
        messagebox.showinfo("Готово", f"Обработка завершена!\nУспешно обработано: {success_count} фото")
        
    def processing_error(self, error_msg):
        """Обработка ошибки"""
        self.progress.stop()
        self.set_ui_state(True)
        self.status_var.set("Ошибка!")
        self.log_message(f"❌ Критическая ошибка: {error_msg}")
        messagebox.showerror("Ошибка", f"Произошла ошибка:\n{error_msg}")

def main():
    root = tk.Tk()
    app = PhotoNumbererApp(root)
    
    # Центрирование окна
    root.update_idletasks()
    x = (root.winfo_screenwidth() - root.winfo_reqwidth()) // 2
    y = (root.winfo_screenheight() - root.winfo_reqheight()) // 2
    root.geometry(f"+{x}+{y}")
    
    root.mainloop()

if __name__ == "__main__":
    main()