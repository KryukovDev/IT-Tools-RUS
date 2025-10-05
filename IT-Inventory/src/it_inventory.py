# -*- coding: utf-8 -*-
"""
IT-INVENTORY v2.0
Инструмент точечной инвентаризации IT-инфраструктуры

Автор идеи и руководитель проекта: Александр Крюков (Kryukov{}Dev)
При поддержке команды нейросетевых архитекторов
Лицензия: MIT License

Telegram: https://t.me/it_tools_rus
GitHub: https://github.com/KryukovDev/IT-Tools-RUS
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import wmi
import os
import platform
from datetime import datetime
import glob
import json
import csv
import webbrowser

# =============================================================================
# КОНСТАНТЫ СТИЛЯ
# =============================================================================

class AppStyle:
    """Стиль оформления для IT-утилит"""
    
    # Цветовая схема
    COLORS = {
        'bg_main': '#1a1a2e',
        'bg_secondary': '#162447',  
        'bg_tertiary': '#0f3460',
        'accent_primary': '#e94560',
        'accent_secondary': '#533483',
        'text_primary': '#ffffff',
        'text_secondary': '#b8b8b8',
        'success': '#4ec9b0',
        'warning': '#ffcc00',
        'error': '#f44747'
    }
    
    # Шрифты
    FONTS = {
        'title': ('Segoe UI', 12, 'bold'),
        'heading': ('Segoe UI', 10, 'bold'),
        'main': ('Segoe UI', 9),
        'mono': ('Consolas', 9),
        'small': ('Segoe UI', 8)
    }
    
    # Иконки
    ICONS = {
        'pc': '🖥️',
        'scan': '🔍',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'users': '👥',
        'monitor': '🖥️',
        'disk': '💾',
        'ram': '🧠',
        'cpu': '⚡',
        'batch': '📊',
        'export': '📁',
        'clear': '🗑️'
    }

# =============================================================================
# ОСНОВНЫЕ ФУНКЦИИ ИНВЕНТАРИЗАЦИИ
# =============================================================================

def check_pc_online(computer_name):
    """Проверяет доступность ПК через ping"""
    try:
        import subprocess
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "1000", computer_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except Exception as e:
        return False

def get_system_info(computer_name):
    """Собирает информацию о системе через WMI"""
    try:
        conn = wmi.WMI(computer=computer_name)
        
        # Процессор
        cpu_info = conn.Win32_Processor()[0]  
        cpu_name = cpu_info.Name.strip()
        
        # Память
        physical_memory = conn.Win32_PhysicalMemory()
        total_ram_gb = 0
        memory_modules = []
        
        if physical_memory:
            total_ram_gb = sum(int(mem.Capacity) for mem in physical_memory) // (1024**3)
            for mem in physical_memory:
                mem_size = int(mem.Capacity) // (1024**3)
                mem_type = mem.MemoryType
                if mem_type == 24: mem_type_str = "DDR3"
                elif mem_type == 26: mem_type_str = "DDR4"
                elif mem_type == 0: mem_type_str = "Unknown"
                else: mem_type_str = f"DDR({mem_type})"
                memory_modules.append(f"{mem_size}GB {mem_type_str}")
        else:
            memory_info = conn.Win32_ComputerSystem()[0]
            total_ram_bytes = int(memory_info.TotalPhysicalMemory)
            total_ram_gb = round(total_ram_bytes / (1024**3))
            memory_modules = ["Тип памяти: неизвестен"]

        # Диски
        disks = []
        for disk in conn.Win32_LogicalDisk():
            if disk.DriveType == 3:
                size_gb = int(disk.Size) // (1024**3) if disk.Size else 0
                free_gb = int(disk.FreeSpace) // (1024**3) if disk.FreeSpace else 0
                disks.append(f"{disk.DeviceID} ({size_gb} GB, свободно {free_gb} GB)")

        # ОС
        os_info = conn.Win32_OperatingSystem()[0]
        os_name = os_info.Caption
        os_install_date = os_info.InstallDate
        if os_install_date:
            try:
                date_str = os_install_date.split('.')[0]
                install_date = datetime.strptime(date_str, "%Y%m%d%H%M%S")
                install_date_str = install_date.strftime("%d.%m.%Y")
            except:
                install_date_str = "Дата неизвестна"
        else:
            install_date_str = "Дата неизвестна"

        # Материнская плата
        motherboard = conn.Win32_BaseBoard()[0]
        mobo_model = motherboard.Product
        mobo_manufacturer = motherboard.Manufacturer

        return {
            "computer_name": computer_name,
            "cpu": cpu_name,
            "ram_gb": total_ram_gb,
            "memory_modules": memory_modules,
            "disks": disks,
            "os_name": os_name,
            "os_install_date": install_date_str,
            "motherboard": f"{mobo_manufacturer} {mobo_model}",
        }
        
    except Exception as e:
        return {"error": f"Ошибка WMI: {e}"}

def get_users_info(computer_name):
    """Сканирует папку C:\\Users"""
    try:
        import subprocess
        users = []
        network_path = f"\\\\{computer_name}\\c$\\Users"
        
        result = subprocess.run(
            ["cmd", "/c", "dir", network_path], 
            capture_output=True, 
            text=True,
            encoding='cp866'
        )
        
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if '<DIR>' in line and not line.startswith('.'):
                    parts = line.split()
                    if len(parts) >= 4:
                        date_str = f"{parts[0]} {parts[1]}"
                        folder_name = parts[-1]
                        
                        system_folders = [".", "..", "Public", "Default", "All Users", "DefaultAppPool"]
                        if folder_name in system_folders:
                            continue
                        
                        try:
                            date_obj = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
                        except:
                            date_obj = datetime.now()
                            
                        users.append({
                            "name": folder_name,
                            "last_modified": date_str,
                            "raw_date": date_obj
                        })
        
        users.sort(key=lambda x: x["raw_date"], reverse=True)
        recent_users = users[:5]
        return recent_users
        
    except Exception as e:
        return [{"name": f"Ошибка: {e}", "last_modified": "N/A"}]

def get_monitors_info(computer_name):
    """Получает информацию о мониторах"""
    try:
        conn = wmi.WMI(computer=computer_name, namespace="root\\wmi")
        monitors = []
        
        try:
            for monitor in conn.WmiMonitorID():
                manufacturer = ""
                product = ""
                serial = ""
                
                if monitor.ManufacturerName:
                    manufacturer_bytes = bytearray()
                    for byte in monitor.ManufacturerName:
                        if byte > 0:
                            manufacturer_bytes.append(byte)
                    if manufacturer_bytes:
                        manufacturer = manufacturer_bytes.decode('utf-8', errors='ignore').strip()
                
                if monitor.ProductCodeID:
                    product_bytes = bytearray()
                    for byte in monitor.ProductCodeID:
                        if byte > 0:
                            product_bytes.append(byte)
                    if product_bytes:
                        product = product_bytes.decode('utf-8', errors='ignore').strip()
                
                diagonal = ""
                try:
                    for mon_info in conn.WmiMonitorBasicDisplayParams():
                        if hasattr(mon_info, 'MaxHorizontalImageSize') and mon_info.MaxHorizontalImageSize:
                            hor_cm = mon_info.MaxHorizontalImageSize
                            ver_cm = mon_info.MaxVerticalImageSize if hasattr(mon_info, 'MaxVerticalImageSize') else hor_cm * 9/16
                            diagonal_cm = (hor_cm**2 + ver_cm**2)**0.5
                            diagonal_inch = round(diagonal_cm / 2.54)
                            diagonal = f"{diagonal_inch}\""
                            break
                except:
                    pass
                
                monitor_name = manufacturer if manufacturer else "Неизвестный"
                if product:
                    monitor_name += f" {product}"
                if diagonal:
                    monitor_name += f" ({diagonal})"
                elif serial:
                    monitor_name += f" [SN: {serial}]"
                
                monitors.append(monitor_name)
                
        except Exception as e:
            print(f"      WmiMonitorID не сработал: {e}")
        
        if not monitors:
            try:
                conn_standard = wmi.WMI(computer=computer_name)
                for monitor in conn_standard.Win32_PnPEntity(Description='Monitor'):
                    if monitor.Name:
                        monitors.append(monitor.Name)
            except Exception as e:
                print(f"      Win32_PnPEntity не сработал: {e}")
        
        unique_monitors = list(set(monitors))
        return unique_monitors if unique_monitors else ["Мониторы: информация недоступна"]
        
    except Exception as e:
        return [f"Ошибка: {e}"]

# =============================================================================
# GUI ОСНОВНОЕ ОКНО
# =============================================================================

class ITInventoryGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("IT-Inventory v2.0")
        self.root.geometry("900x700")
        
        # Применяем стиль
        self.style = AppStyle()
        self.root.configure(bg=self.style.COLORS['bg_main'])
        
        # Устанавливаем иконку
        self.setup_icon()
        
        # Настройка стилей ttk
        self.setup_styles()
        
        # Создание интерфейса
        self.create_widgets()
        
        # Загружаем историю
        self.load_history()

        # Для хранения результатов пакетного сканирования
        self.batch_results = []

    def setup_icon(self):
        """Устанавливаем свою иконку приложения"""
        try:
            # Пробуем загрузить нашу иконку
            import os
            import sys
            
            # Определяем путь к иконке
            if hasattr(sys, '_MEIPASS'):
                # Если запущено как exe (PyInstaller)
                icon_path = os.path.join(sys._MEIPASS, 'desktop.ico')
            else:
                # Если запущено как скрипт
                icon_path = 'desktop.ico'
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                print(f"✅ Иконка загружена: {icon_path}")
            else:
                # Если иконки нет - убираем стандартную питоновскую
                self.root.iconbitmap('')
                print("⚠️ Иконка desktop.ico не найдена")
                
        except Exception as e:
            print(f"❌ Ошибка загрузки иконки: {e}")
            # fallback - убираем стандартную иконку
            try:
                self.root.iconbitmap('')
            except:
                pass

    def setup_styles(self):
        """Настройка ttk стилей"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Конфигурация Notebook (вкладок)
        style.configure('TNotebook', background=self.style.COLORS['bg_main'])
        style.configure('TNotebook.Tab', 
                       background=self.style.COLORS['bg_secondary'],
                       foreground=self.style.COLORS['text_secondary'],
                       padding=[15, 5],
                       font=self.style.FONTS['main'])
        style.map('TNotebook.Tab',
                 background=[('selected', self.style.COLORS['accent_primary'])],
                 foreground=[('selected', self.style.COLORS['text_primary'])])
        
    def create_custom_button(self, parent, text, command, accent_color=None):
        """Создает кнопку в стиле приложения"""
        if accent_color is None:
            accent_color = self.style.COLORS['accent_primary']
            
        btn = tk.Button(parent,
                       text=text,
                       command=command,
                       bg=self.style.COLORS['bg_tertiary'],
                       fg=self.style.COLORS['text_primary'],
                       activebackground=accent_color,
                       activeforeground=self.style.COLORS['text_primary'],
                       font=self.style.FONTS['main'],
                       relief='flat',
                       bd=0,
                       padx=15,
                       pady=6,
                       cursor='hand2')
        return btn

    def create_widgets(self):
        """Создание всего интерфейса"""
        # Главный контейнер
        main_frame = tk.Frame(self.root, bg=self.style.COLORS['bg_main'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        # Заголовок
        title_frame = tk.Frame(main_frame, bg=self.style.COLORS['bg_main'])
        title_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(title_frame,
                              text=f"{self.style.ICONS['pc']} IT-Inventory v2.0",
                              font=self.style.FONTS['title'],
                              fg=self.style.COLORS['accent_primary'],
                              bg=self.style.COLORS['bg_main'])
        title_label.pack()
        
        subtitle_label = tk.Label(title_frame,
                                 text="Инструмент точечной инвентаризации IT-инфраструктуры",
                                 font=self.style.FONTS['small'],
                                 fg=self.style.COLORS['text_secondary'],
                                 bg=self.style.COLORS['bg_main'])
        subtitle_label.pack()
        
        # Вкладки
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Создание вкладок
        self.create_single_tab()
        self.create_batch_tab()
        self.create_about_tab()
        
        # Статус бар
        self.create_status_bar()
        
    def create_single_tab(self):
        """Вкладка одиночного сканирования"""
        single_frame = ttk.Frame(self.notebook)
        self.notebook.add(single_frame, text=f"{self.style.ICONS['scan']} Одиночный ПК")
        
        # Поле ввода с историей
        input_frame = tk.Frame(single_frame, bg=self.style.COLORS['bg_main'])
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, text="Имя компьютера:", 
                bg=self.style.COLORS['bg_main'], 
                fg=self.style.COLORS['text_primary'],
                font=self.style.FONTS['main']).pack(side=tk.LEFT, padx=(0, 10))
        
        self.single_pc_entry = ttk.Combobox(input_frame, 
                                          width=30, 
                                          font=self.style.FONTS['main'],
                                          values=[])
        self.single_pc_entry.pack(side=tk.LEFT, padx=(0, 10))
        self.single_pc_entry.bind('<Return>', lambda e: self.scan_single_pc())
        
        scan_btn = self.create_custom_button(input_frame,
                                           f"{self.style.ICONS['scan']} Сканировать",
                                           self.scan_single_pc)
        scan_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_btn = self.create_custom_button(input_frame,
                                             f"{self.style.ICONS['export']} Экспорт в TXT",
                                             self.export_single_report,
                                             self.style.COLORS['success'])
        export_btn.pack(side=tk.LEFT)
        
        # Область вывода результатов
        result_frame = tk.Frame(single_frame, bg=self.style.COLORS['bg_main'])
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.single_result_text = scrolledtext.ScrolledText(result_frame,
                                                          height=20,
                                                          font=self.style.FONTS['mono'],
                                                          bg=self.style.COLORS['bg_secondary'],
                                                          fg=self.style.COLORS['text_primary'],
                                                          insertbackground=self.style.COLORS['accent_primary'],
                                                          selectbackground=self.style.COLORS['accent_secondary'],
                                                          relief='flat',
                                                          padx=10,
                                                          pady=10)
        self.single_result_text.pack(fill=tk.BOTH, expand=True)
        
    def create_batch_tab(self):
        """Вкладка пакетного сканирования"""
        batch_frame = ttk.Frame(self.notebook)
        self.notebook.add(batch_frame, text=f"{self.style.ICONS['batch']} Пакетный режим")
        
        # Область ввода списка ПК
        input_frame = tk.Frame(batch_frame, bg=self.style.COLORS['bg_main'])
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(input_frame, 
                text="Список компьютеров (через запятую или с новой строки):",
                bg=self.style.COLORS['bg_main'],
                fg=self.style.COLORS['text_primary'],
                font=self.style.FONTS['main']).pack(anchor=tk.W)
        
        self.batch_pc_text = scrolledtext.ScrolledText(input_frame,
                                                     height=6,
                                                     font=self.style.FONTS['mono'],
                                                     bg=self.style.COLORS['bg_secondary'],
                                                     fg=self.style.COLORS['text_primary'],
                                                     insertbackground=self.style.COLORS['accent_primary'])
        self.batch_pc_text.pack(fill=tk.X, pady=5)
        
        # Кнопки
        btn_frame = tk.Frame(input_frame, bg=self.style.COLORS['bg_main'])
        btn_frame.pack(fill=tk.X)
        
        scan_batch_btn = self.create_custom_button(btn_frame,
                                                  f"{self.style.ICONS['scan']} Запуск сканирования",
                                                  self.scan_batch_pcs)
        scan_batch_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        export_batch_btn = self.create_custom_button(btn_frame,
                                                    f"{self.style.ICONS['export']} Экспорт в CSV",
                                                    self.export_batch_csv,
                                                    self.style.COLORS['success'])
        export_batch_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        clear_btn = self.create_custom_button(btn_frame,
                                             f"{self.style.ICONS['clear']} Очистить",
                                             self.clear_batch_text,
                                             self.style.COLORS['error'])
        clear_btn.pack(side=tk.LEFT)
        
        # Прогресс-бар
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(btn_frame, 
                                          variable=self.progress_var,
                                          maximum=100)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(20, 0))
        
        # Область результатов
        self.batch_result_text = scrolledtext.ScrolledText(batch_frame,
                                                         height=15,
                                                         font=self.style.FONTS['mono'],
                                                         bg=self.style.COLORS['bg_secondary'],
                                                         fg=self.style.COLORS['text_primary'])
        self.batch_result_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    def create_about_tab(self):
        """Вкладка 'О программе'"""
        about_frame = ttk.Frame(self.notebook)
        self.notebook.add(about_frame, text=f"{self.style.ICONS['pc']} О программе")
        
        about_text = f"""
{self.style.ICONS['pc']} IT-Inventory v2.0

Инструмент для точечной инвентаризации известных компьютеров 
в корпоративной сети. Не является сканером сети - требуется 
знание имен целевых ПК.

{self.style.ICONS['success']} ВОЗМОЖНОСТИ:
• Точечный сбор данных по известным именам ПК
• Информация о системе ({self.style.ICONS['cpu']}процессор, {self.style.ICONS['ram']}память, {self.style.ICONS['disk']}диски)
• Сведения о мониторах и их диагоналях
• Список пользователей компьютера
• Пакетная обработка множества ПК
• Экспорт отчетов в TXT и CSV

{self.style.ICONS['scan']} ТЕХНОЛОГИИ:
• Python 3.x + WMI + tkinter
• Работа с сетевыми компьютерами  
• Совместимость с Windows 7/8/10/11

{self.style.ICONS['users']} АВТОРСТВО:
Автор идеи и руководитель проекта: Александр Крюков (Kryukov{{}}Dev)
При поддержке команды нейросетевых архитекторов

Версия: 2.0
Год: 2025

{self.style.ICONS['warning']} ИНСТРУКЦИЯ:
1. Для сканирования одиночного ПК введите его имя в первой вкладке
2. Для массовой проверки введите список ПК через запятую
3. Программа автоматически определит доступность и соберет данные

{self.style.ICONS['error']} ТРЕБОВАНИЯ:
• Доступ к целевым компьютерам по сети
• Права администратора
• Разблокированный WMI на целевых ПК
"""
        
        about_text_widget = scrolledtext.ScrolledText(about_frame,
                                                    font=self.style.FONTS['main'],
                                                    bg=self.style.COLORS['bg_secondary'],
                                                    fg=self.style.COLORS['text_primary'],
                                                    padx=15,
                                                    pady=15)
        about_text_widget.pack(fill=tk.BOTH, expand=True)
        about_text_widget.insert(tk.END, about_text)
        about_text_widget.configure(state='disabled')
        
    def create_status_bar(self):
        """Создание статусной строки"""
        status_frame = tk.Frame(self.root, 
                               bg=self.style.COLORS['bg_tertiary'], 
                               relief=tk.FLAT, 
                               height=22)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        status_frame.pack_propagate(False)
        
        # Авторство слева
        author_label = tk.Label(status_frame, 
                               text="Александр Крюков, 2025 | IT-Tools-RUS",
                               bg=self.style.COLORS['bg_tertiary'],
                               fg=self.style.COLORS['text_secondary'],
                               font=self.style.FONTS['small'])
        author_label.pack(side=tk.LEFT, padx=10, pady=2)
        
        # Кликабельная ссылка справа
        link_label = tk.Label(status_frame, 
                             text="📢 t.me/it_tools_rus", 
                             bg=self.style.COLORS['bg_tertiary'],
                             fg=self.style.COLORS['accent_primary'],
                             font=self.style.FONTS['small'],
                             cursor="hand2")
        link_label.pack(side=tk.RIGHT, padx=10, pady=2)
        link_label.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/it_tools_rus"))
        
    def load_history(self):
        """Загрузка истории сканирований"""
        try:
            if os.path.exists('scan_history.json'):
                with open('scan_history.json', 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    self.single_pc_entry['values'] = history
        except:
            pass
            
    def save_to_history(self, pc_name):
        """Сохранение в историю"""
        try:
            history = list(self.single_pc_entry['values'])
            if pc_name not in history:
                history.insert(0, pc_name)
                history = history[:20]  # Последние 20 записей
                
            with open('scan_history.json', 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False)
                
            self.single_pc_entry['values'] = history
        except:
            pass

    def scan_single_pc(self):
        """Сканирование одиночного ПК"""
        pc_name = self.single_pc_entry.get().strip()
        if not pc_name:
            messagebox.showerror("Ошибка", "Введите имя компьютера")
            return
        
        self.single_result_text.delete(1.0, tk.END)
        self.single_result_text.insert(tk.END, f"{self.style.ICONS['scan']} Сканирование {pc_name}...\n\n")
        self.root.update()
        
        try:
            # Проверка доступности
            if not check_pc_online(pc_name):
                self.single_result_text.insert(tk.END, f"{self.style.ICONS['error']} Компьютер {pc_name} не в сети!\n")
                return
            
            # Сбор информации
            system_info = get_system_info(pc_name)
            users_info = get_users_info(pc_name)
            monitors_info = get_monitors_info(pc_name)
            
            # Сохраняем в историю
            self.save_to_history(pc_name)
            
            # Вывод результатов
            self.display_single_results(system_info, users_info, monitors_info)
            
        except Exception as e:
            self.single_result_text.insert(tk.END, f"{self.style.ICONS['error']} Ошибка: {e}\n")

    def display_single_results(self, system, users, monitors):
        """Отображение результатов одиночного сканирования"""
        self.single_result_text.delete(1.0, tk.END)
        
        # Системная информация
        if 'error' in system:
            self.single_result_text.insert(tk.END, f"{self.style.ICONS['error']} ОШИБКА: {system['error']}\n\n")
            return
        
        self.single_result_text.insert(tk.END, f"{self.style.ICONS['success']} ОТЧЕТ IT-ИНВЕНТАРИЗАЦИИ\n")
        self.single_result_text.insert(tk.END, "="*50 + "\n\n")
        
        self.single_result_text.insert(tk.END, f"{self.style.ICONS['pc']} СИСТЕМНАЯ ИНФОРМАЦИЯ:\n")
        self.single_result_text.insert(tk.END, f"   Компьютер: {system.get('computer_name', 'N/A')}\n")
        self.single_result_text.insert(tk.END, f"   Мат.плата: {system.get('motherboard', 'N/A')}\n")
        self.single_result_text.insert(tk.END, f"   {self.style.ICONS['cpu']} Процессор: {system.get('cpu', 'N/A')}\n")
        self.single_result_text.insert(tk.END, f"   {self.style.ICONS['ram']} Память: {system.get('ram_gb', 'N/A')} GB\n")
        
        self.single_result_text.insert(tk.END, "   Модули памяти:\n")
        for module in system.get('memory_modules', []):
            self.single_result_text.insert(tk.END, f"     • {module}\n")
            
        self.single_result_text.insert(tk.END, f"   ОС: {system.get('os_name', 'N/A')}\n")
        self.single_result_text.insert(tk.END, f"   Установлена: {system.get('os_install_date', 'N/A')}\n")
        
        self.single_result_text.insert(tk.END, f"   {self.style.ICONS['disk']} Диски:\n")
        for disk in system.get('disks', []):
            self.single_result_text.insert(tk.END, f"     • {disk}\n")
        
        # Пользователи
        self.single_result_text.insert(tk.END, f"\n{self.style.ICONS['users']} ПОСЛЕДНИЕ ПОЛЬЗОВАТЕЛИ (топ-5):\n")
        if users and isinstance(users, list):
            for i, user in enumerate(users[:5], 1):
                if isinstance(user, dict) and 'name' in user:
                    self.single_result_text.insert(tk.END, f"   {i}. {user['name']} - {user.get('last_modified', 'N/A')}\n")
        
        # Мониторы
        self.single_result_text.insert(tk.END, f"\n{self.style.ICONS['monitor']} МОНИТОРЫ:\n")
        for i, monitor in enumerate(monitors, 1):
            self.single_result_text.insert(tk.END, f"   {i}. {monitor}\n")
        
        self.single_result_text.insert(tk.END, f"\n{self.style.ICONS['success']} Сканирование завершено успешно!\n")

    def scan_batch_pcs(self):
        """Пакетное сканирование компьютеров"""
        pc_text = self.batch_pc_text.get(1.0, tk.END).strip()
        if not pc_text:
            messagebox.showerror("Ошибка", "Введите список компьютеров")
            return
        
        # Парсинг списка ПК
        pc_list = []
        for line in pc_text.split('\n'):
            pcs = [pc.strip() for pc in line.split(',') if pc.strip()]
            pc_list.extend(pcs)
        
        if not pc_list:
            messagebox.showerror("Ошибка", "Не найдено валидных имен компьютеров")
            return
        
        self.batch_result_text.delete(1.0, tk.END)
        self.batch_result_text.insert(tk.END, f"{self.style.ICONS['scan']} Запуск пакетного сканирования для {len(pc_list)} ПК...\n\n")
        self.root.update()
        
        # Очищаем предыдущие результаты
        self.batch_results = []
        
        # Сканирование каждого ПК
        success_count = 0
        self.progress_var.set(0)
        
        for i, pc_name in enumerate(pc_list, 1):
            self.batch_result_text.insert(tk.END, f"📋 [{i}/{len(pc_list)}] {pc_name}... ")
            self.root.update()
            
            try:
                # Обновляем прогресс-бар
                progress = (i / len(pc_list)) * 100
                self.progress_var.set(progress)
                
                if not check_pc_online(pc_name):
                    self.batch_result_text.insert(tk.END, f"{self.style.ICONS['error']} не в сети\n")
                    self.batch_results.append({
                        'computer_name': pc_name,
                        'status': 'offline',
                        'cpu': 'N/A',
                        'ram_gb': 'N/A',
                        'monitors': 'N/A'
                    })
                    continue
                
                system_info = get_system_info(pc_name)
                monitors_info = get_monitors_info(pc_name)
                
                if 'error' not in system_info:
                    monitors_str = ", ".join(monitors_info) if monitors_info else "нет данных"
                    self.batch_result_text.insert(tk.END, f"{self.style.ICONS['success']} {system_info.get('cpu', 'N/A')}, {system_info.get('ram_gb', 'N/A')}GB RAM | Мониторы: {monitors_str}\n")
                    success_count += 1
                    
                    # Сохраняем результат для экспорта
                    self.batch_results.append({
                        'computer_name': pc_name,
                        'status': 'success',
                        'cpu': system_info.get('cpu', 'N/A'),
                        'ram_gb': system_info.get('ram_gb', 'N/A'),
                        'os_name': system_info.get('os_name', 'N/A'),
                        'monitors': monitors_str,
                        'motherboard': system_info.get('motherboard', 'N/A')
                    })
                else:
                    self.batch_result_text.insert(tk.END, f"{self.style.ICONS['error']} ошибка\n")
                    self.batch_results.append({
                        'computer_name': pc_name,
                        'status': 'error',
                        'cpu': 'N/A',
                        'ram_gb': 'N/A',
                        'monitors': 'N/A'
                    })
                    
            except Exception as e:
                self.batch_result_text.insert(tk.END, f"{self.style.ICONS['error']} ошибка: {e}\n")
                self.batch_results.append({
                    'computer_name': pc_name,
                    'status': 'error',
                    'cpu': 'N/A', 
                    'ram_gb': 'N/A',
                    'monitors': 'N/A'
                })
        
        # Итоговый отчет
        self.batch_result_text.insert(tk.END, f"\n{self.style.ICONS['success']} ИТОГ: Успешно {success_count}/{len(pc_list)} ПК\n")
        self.progress_var.set(100)

    def export_single_report(self):
        """Экспорт одиночного отчета в TXT"""
        content = self.single_result_text.get(1.0, tk.END)
        if not content.strip():
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта")
            return
            
        try:
            filename = f"inventory_single_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            messagebox.showinfo("Успех", f"Отчет сохранен в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    def export_batch_csv(self):
        """Экспорт пакетного сканирования в CSV"""
        if not self.batch_results:
            messagebox.showwarning("Предупреждение", "Нет данных для экспорта. Сначала выполните сканирование.")
            return
            
        try:
            filename = f"inventory_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
                fieldnames = ['computer_name', 'status', 'cpu', 'ram_gb', 'os_name', 'motherboard', 'monitors']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                
                writer.writeheader()
                for result in self.batch_results:
                    writer.writerow(result)
                    
            messagebox.showinfo("Успех", f"CSV отчет сохранен в {filename}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить CSV файл: {e}")

    def clear_batch_text(self):
        """Очистка текстовых полей"""
        self.batch_pc_text.delete(1.0, tk.END)
        self.batch_result_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.batch_results = []

# =============================================================================
# ЗАПУСК ПРИЛОЖЕНИЯ
# =============================================================================

if __name__ == "__main__":
    try:
        root = tk.Tk()
        app = ITInventoryGUI(root)
        root.mainloop()
    except Exception as e:
        print(f"Ошибка запуска GUI: {e}")
        input("Нажмите Enter для выхода...")