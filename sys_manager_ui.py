import sys
import os
import psutil
import win32api
import wmi
import time
import subprocess
import difflib
import winreg
import win32evtlog
import GPUtil
from pySMART import Device
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from sentence_transformers import SentenceTransformer, util
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QComboBox, QLabel, QHBoxLayout)
from PyQt5.QtCore import QTimer
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import QInputDialog

class AISysManagerUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AI Sys Manager")
        self.setGeometry(100, 100, 1000, 700)

        # Initialize sentence transformer for intent classification
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.intents = {
            "check_disk": ["check disk space", "how much space is left", "disk usage"],
            "check_cpu": ["check cpu", "cpu usage", "how’s my processor"],
            "kill_process": ["kill process", "stop a program", "end task"],
            "system_info": ["system info", "tell me about my pc", "what’s my setup"],
            "check_memory": ["check memory", "ram usage", "how much ram is free"],
            "check_network": ["check network", "internet status", "network usage"],
            "check_temp": ["check temperature", "cpu temp", "is my pc hot"],
            "check_startup": ["check startup", "startup programs", "what runs at boot"],
            "check_battery": ["check battery", "battery health", "how’s my battery"],
            "check_logs": ["check logs", "event logs", "system warnings"],
            "set_priority": ["set priority", "change process priority", "boost process"],
            "check_gpu": ["check gpu", "gpu usage", "graphics card status"],
            "check_disk_health": ["check disk health", "smart data", "disk status"],
            "run_benchmark": ["run benchmark", "test system", "performance check"],
            "set_power_plan": ["set power plan", "change power mode", "power settings"]
        }
        self.intent_embeddings = {
            intent: self.model.encode(examples, convert_to_tensor=True)
            for intent, examples in self.intents.items()
        }
        self.drive_types = self.detect_drive_types()
        if not os.path.exists("reports"):
            os.makedirs("reports")

        # UI Setup
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        self.init_tabs()

        # Real-time data
        self.cpu_data = []
        self.gpu_data = []
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_graphs)
        self.timer.start(1000)  # Update every second

    def detect_drive_types(self):
        drives = {}
        for partition in psutil.disk_partitions():
            drive = partition.device
            try:
                disk_io = psutil.disk_io_counters(perdisk=True).get(drive.split("\\")[0], None)
                if disk_io:
                    is_ssd = disk_io.read_time < 100 and disk_io.write_time < 100
                    drives[drive] = "SSD" if is_ssd else "HDD"
                else:
                    drives[drive] = "Unknown"
            except Exception:
                drives[drive] = "Unknown"
        return drives

    def execute_command(self, command):
        return os.popen(command).read()

    def init_tabs(self):
        # Disk Tab
        disk_tab = QWidget()
        disk_layout = QVBoxLayout()
        disk_btn = QPushButton("Check Disk Space")
        disk_btn.clicked.connect(lambda: self.disk_output.setText(self.check_disk_space()))
        self.disk_output = QTextEdit()
        self.disk_output.setReadOnly(True)
        disk_health_btn = QPushButton("Check Disk Health")
        disk_health_btn.clicked.connect(lambda: self.disk_output.setText(self.check_disk_health()))
        disk_layout.addWidget(disk_btn)
        disk_layout.addWidget(disk_health_btn)
        disk_layout.addWidget(self.disk_output)
        disk_tab.setLayout(disk_layout)
        self.tabs.addTab(disk_tab, "Disk")

        # CPU Tab
        cpu_tab = QWidget()
        cpu_layout = QVBoxLayout()
        cpu_btn = QPushButton("Check CPU Usage")
        cpu_btn.clicked.connect(lambda: self.cpu_output.setText(self.check_cpu_usage()))
        self.cpu_output = QTextEdit()
        self.cpu_output.setReadOnly(True)
        self.cpu_fig, self.cpu_ax = plt.subplots()
        self.cpu_canvas = FigureCanvas(self.cpu_fig)
        cpu_layout.addWidget(self.cpu_canvas)
        cpu_layout.addWidget(cpu_btn)
        cpu_layout.addWidget(self.cpu_output)
        cpu_tab.setLayout(cpu_layout)
        self.tabs.addTab(cpu_tab, "CPU")

        # Memory Tab
        memory_tab = QWidget()
        memory_layout = QVBoxLayout()
        memory_btn = QPushButton("Check Memory Usage")
        memory_btn.clicked.connect(lambda: self.memory_output.setText(self.check_memory_usage()))
        self.memory_output = QTextEdit()
        self.memory_output.setReadOnly(True)
        memory_layout.addWidget(memory_btn)
        memory_layout.addWidget(self.memory_output)
        memory_tab.setLayout(memory_layout)
        self.tabs.addTab(memory_tab, "Memory")

        # GPU Tab
        gpu_tab = QWidget()
        gpu_layout = QVBoxLayout()
        gpu_btn = QPushButton("Check GPU")
        gpu_btn.clicked.connect(lambda: self.gpu_output.setText(self.check_gpu()))
        self.gpu_output = QTextEdit()
        self.gpu_output.setReadOnly(True)
        self.gpu_fig, self.gpu_ax = plt.subplots()
        self.gpu_canvas = FigureCanvas(self.gpu_fig)
        gpu_layout.addWidget(self.gpu_canvas)
        gpu_layout.addWidget(gpu_btn)
        gpu_layout.addWidget(self.gpu_output)
        gpu_tab.setLayout(gpu_layout)
        self.tabs.addTab(gpu_tab, "GPU")

        # Network Tab
        network_tab = QWidget()
        network_layout = QVBoxLayout()
        network_btn = QPushButton("Check Network")
        network_btn.clicked.connect(lambda: self.network_output.setText(self.check_network_status()))
        self.network_output = QTextEdit()
        self.network_output.setReadOnly(True)
        network_layout.addWidget(network_btn)
        network_layout.addWidget(self.network_output)
        network_tab.setLayout(network_layout)
        self.tabs.addTab(network_tab, "Network")

        # Temp Tab
        temp_tab = QWidget()
        temp_layout = QVBoxLayout()
        temp_btn = QPushButton("Check Temperature")
        temp_btn.clicked.connect(lambda: self.temp_output.setText(self.check_system_temp()))
        self.temp_output = QTextEdit()
        self.temp_output.setReadOnly(True)
        temp_layout.addWidget(temp_btn)
        temp_layout.addWidget(self.temp_output)
        temp_tab.setLayout(temp_layout)
        self.tabs.addTab(temp_tab, "Temp")

        # Startup Tab
        startup_tab = QWidget()
        startup_layout = QVBoxLayout()
        startup_btn = QPushButton("Check Startup Programs")
        startup_btn.clicked.connect(lambda: self.startup_output.setText(self.check_startup()))
        self.startup_output = QTextEdit()
        self.startup_output.setReadOnly(True)
        startup_layout.addWidget(startup_btn)
        startup_layout.addWidget(self.startup_output)
        startup_tab.setLayout(startup_layout)
        self.tabs.addTab(startup_tab, "Startup")

        # Battery Tab
        battery_tab = QWidget()
        battery_layout = QVBoxLayout()
        battery_btn = QPushButton("Check Battery")
        battery_btn.clicked.connect(lambda: self.battery_output.setText(self.check_battery()))
        self.battery_output = QTextEdit()
        self.battery_output.setReadOnly(True)
        battery_layout.addWidget(battery_btn)
        battery_layout.addWidget(self.battery_output)
        battery_tab.setLayout(battery_layout)
        self.tabs.addTab(battery_tab, "Battery")

        # Logs Tab
        logs_tab = QWidget()
        logs_layout = QVBoxLayout()
        logs_btn = QPushButton("Check Logs")
        logs_btn.clicked.connect(self.check_logs_ui)
        self.logs_output = QTextEdit()
        self.logs_output.setReadOnly(True)
        logs_layout.addWidget(logs_btn)
        logs_layout.addWidget(self.logs_output)
        logs_tab.setLayout(logs_layout)
        self.tabs.addTab(logs_tab, "Logs")

        # Priority Tab
        priority_tab = QWidget()
        priority_layout = QVBoxLayout()
        self.process_table = QTableWidget()
        self.process_table.setColumnCount(4)
        self.process_table.setHorizontalHeaderLabels(["Name", "PID", "Memory (MB)", "Priority"])
        self.process_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.update_process_table()
        refresh_btn = QPushButton("Refresh Process List")
        refresh_btn.clicked.connect(self.update_process_table)
        kill_btn = QPushButton("Kill Selected")
        kill_btn.clicked.connect(self.kill_selected_process)
        priority_combo = QComboBox()
        priority_combo.addItems(["Low", "Normal", "High", "Realtime"])
        set_priority_btn = QPushButton("Set Priority")
        set_priority_btn.clicked.connect(lambda: self.set_priority(priority_combo.currentText()))
        priority_layout.addWidget(self.process_table)
        priority_layout.addWidget(refresh_btn)
        priority_layout.addWidget(kill_btn)
        priority_layout.addWidget(QLabel("Set Priority:"))
        priority_layout.addWidget(priority_combo)
        priority_layout.addWidget(set_priority_btn)
        priority_tab.setLayout(priority_layout)
        self.tabs.addTab(priority_tab, "Priority")

        # Disk Health Tab (already in Disk tab, but separate for clarity)
        # Already handled above

        # Benchmark Tab
        benchmark_tab = QWidget()
        benchmark_layout = QVBoxLayout()
        benchmark_btn = QPushButton("Run Benchmark")
        benchmark_btn.clicked.connect(lambda: self.benchmark_output.setText(self.run_benchmark()))
        self.benchmark_output = QTextEdit()
        self.benchmark_output.setReadOnly(True)
        benchmark_layout.addWidget(benchmark_btn)
        benchmark_layout.addWidget(self.benchmark_output)
        benchmark_tab.setLayout(benchmark_layout)
        self.tabs.addTab(benchmark_tab, "Benchmark")

        # Power Plan Tab
        power_tab = QWidget()
        power_layout = QVBoxLayout()
        self.power_combo = QComboBox()
        self.update_power_plans()
        power_btn = QPushButton("Set Power Plan")
        power_btn.clicked.connect(self.set_power_plan_ui)
        self.power_output = QTextEdit()
        self.power_output.setReadOnly(True)
        power_layout.addWidget(QLabel("Select Power Plan:"))
        power_layout.addWidget(self.power_combo)
        power_layout.addWidget(power_btn)
        power_layout.addWidget(self.power_output)
        power_tab.setLayout(power_layout)
        self.tabs.addTab(power_tab, "Power Plan")

    def check_disk_space(self):
        drive = "C:\\"
        free_bytes = win32api.GetDiskFreeSpaceEx(drive)[0]
        drive_type = self.drive_types.get(drive, "Unknown")
        advice = "Plenty of space left!" if free_bytes > 10 * (1024**3) else "Running low—might want to clean up."
        if drive_type == "SSD":
            advice += " No need to defrag this SSD."
        elif drive_type == "HDD":
            advice += " Consider defragmenting this HDD if it’s slow."
        return f"Free space on {drive} ({drive_type}): {free_bytes / (1024**3):.2f} GB. {advice}"

    def check_cpu_usage(self):
        cpu_percent = psutil.cpu_percent(interval=1)
        advice = "All good here." if cpu_percent < 70 else "CPU’s working hard—check Task Manager."
        return f"CPU usage: {cpu_percent}%. {advice}"

    def check_memory_usage(self):
        memory = psutil.virtual_memory()
        used = memory.used / (1024**3)
        total = memory.total / (1024**3)
        percent = memory.percent
        advice = "Memory looks fine." if percent < 80 else "RAM’s almost maxed out—close some apps."
        processes = [(p.info['memory_info'].rss, p.info['name']) for p in psutil.process_iter(['name', 'memory_info'])]
        top_hogs = sorted(processes, reverse=True)[:5]
        hog_list = "\n".join([f"- {name}: {size / (1024**3):.2f} GB" for size, name in top_hogs])
        return f"Memory: {used:.2f}/{total:.2f} GB used ({percent}%). {advice}\nTop memory users:\n{hog_list}"

    def check_gpu(self):
        try:
            gpus = GPUtil.getGPUs()
            if not gpus:
                return "No GPU detected or GPUtil failed to initialize."
            output = []
            for gpu in gpus:
                output.append(
                    f"GPU {gpu.id}: {gpu.name}\n"
                    f"- Usage: {gpu.load * 100:.1f}%\n"
                    f"- Temperature: {gpu.temperature}°C\n"
                    f"- Memory: {gpu.memoryUsed:.1f}/{gpu.memoryTotal:.1f} MB ({gpu.memoryUtil * 100:.1f}% used)"
                )
                if gpu.temperature > 85:
                    output.append("Warning: GPU is running hot—check cooling!")
            return "\n".join(output)
        except Exception as e:
            return f"Error checking GPU: {str(e)}. Ensure GPU drivers are installed."

    def check_network_status(self):
        self.network_output.setText("Running network test—this will take about 5 seconds...")
        QApplication.processEvents()
        net_io_start = psutil.net_io_counters()
        time.sleep(5)
        net_io_end = psutil.net_io_counters()
        sent_rate = (net_io_end.bytes_sent - net_io_start.bytes_sent) / 5 / (1024**2)
        recv_rate = (net_io_end.bytes_recv - net_io_start.bytes_recv) / 5 / (1024**2)
        try:
            ping_output = subprocess.run(["ping", "-n", "4", "google.com"], capture_output=True, text=True)
            ping_result = ping_output.stdout
            ping_advice = "Internet looks good." if "time=" in ping_result else "Couldn’t reach Google—check your connection."
        except Exception:
            ping_result = "Ping failed."
            ping_advice = "Network issue detected—modem or router might be down."
        return f"Network Bandwidth (5s sample): Sent {sent_rate:.2f} MB/s, Received {recv_rate:.2f} MB/s\nPing to Google:\n{ping_result}\n{ping_advice}"

    def check_system_temp(self):
        try:
            w = wmi.WMI(namespace="root\\OpenHardwareMonitor")
            sensors = w.Sensor()
            cpu_temp = None
            for sensor in sensors:
                if sensor.SensorType == "Temperature" and "CPU" in sensor.Name:
                    cpu_temp = sensor.Value
                    break
            if cpu_temp:
                advice = "Temp looks normal." if cpu_temp < 80 else "CPU’s hot—check cooling or reduce load."
                return f"CPU Temperature: {cpu_temp}°C. {advice}"
            else:
                return "No CPU temp found. Download OpenHardwareMonitor from openhardwaremonitor.org, run it, then try again."
        except Exception:
            return "Temperature check failed. Ensure OpenHardwareMonitor is installed and running (get it from openhardwaremonitor.org)."

    def check_startup(self):
        startup_items = []
        reg_paths = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
        ]
        for hive, path in reg_paths:
            try:
                key = winreg.OpenKey(hive, path, 0, winreg.KEY_READ)
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, value, _ = winreg.EnumValue(key, i)
                    startup_items.append(f"- {name}: {value}")
                winreg.CloseKey(key)
            except WindowsError:
                continue
        if not startup_items:
            return "No startup programs found in common registry locations."
        return "Startup Programs:\n" + "\n".join(startup_items) + "\n\nThese run automatically at boot. Too many can slow startup—check Task Manager’s Startup tab to disable."

    def check_battery(self):
        report_path = os.path.join("reports", "battery_report.html")
        os.system(f"powercfg /batteryreport /output \"{report_path}\"")
        time.sleep(2)
        if not os.path.exists(report_path):
            return "Battery report generation failed. Are you on a laptop with a battery?"
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                soup = BeautifulSoup(f, "html.parser")
            design_capacity = None
            full_charge_capacity = None
            for tr in soup.find_all("tr"):
                tds = tr.find_all("td")
                if len(tds) >= 2:
                    if "DESIGN CAPACITY" in tds[0].text:
                        capacity_text = tds[1].text.strip().replace(',', '')
                        design_capacity = int("".join(filter(str.isdigit, capacity_text))) if capacity_text else None
                    elif "FULL CHARGE CAPACITY" in tds[0].text:
                        capacity_text = tds[1].text.strip().replace(',', '')
                        full_charge_capacity = int("".join(filter(str.isdigit, capacity_text))) if capacity_text else None
            if design_capacity and full_charge_capacity:
                health_percent = (full_charge_capacity / design_capacity) * 100
                advice = "Battery’s in good shape." if health_percent > 80 else "Battery health is degrading—consider replacing it soon."
                return f"Battery Health:\n- Design Capacity: {design_capacity} mWh\n- Full Charge Capacity: {full_charge_capacity} mWh\n- Health: {health_percent:.1f}%\n{advice}"
            else:
                return "Couldn’t find battery capacity data in report. Check 'reports/battery_report.html' manually."
        except Exception as e:
            return f"Error parsing battery report: {str(e)}"

    def check_logs_ui(self):
        days = input("How many days back to search (1-30, default 7)? ") or "7"
        try:
            days = min(max(int(days), 1), 30)
        except ValueError:
            days = 7
        level_input = input("Filter by level (1=Critical, 2=Error, 4=Warning, e.g., '1,2', default 0=Unsure)? ") or "0"
        level_map = {"1": 1, "2": 2, "4": 4}
        levels = set()
        if level_input:
            for part in level_input.split(','):
                if part.strip() in level_map:
                    levels.add(level_map[part.strip()])
        if not levels:
            levels = {1, 2, 4}
        keyword = input("Enter a keyword to search (e.g., 'dll', optional): ").strip().lower()
        error_code = input("Enter an error code (e.g., '0x80070491', optional): ").strip().lower()
        
        self.logs_output.setText(f"Searching logs from last {days} days—this may take a moment...")
        QApplication.processEvents()
        cutoff = datetime.now() - timedelta(days=days)
        logs = {"Application": [], "System": []}
        
        for log_type in logs.keys():
            try:
                hand = win32evtlog.OpenEventLog(None, log_type)
                flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ
                events = win32evtlog.ReadEventLog(hand, flags, 0)
                while events:
                    for event in events:
                        event_time = event.TimeGenerated
                        if event_time < cutoff:
                            break
                        level_num = event.EventType
                        if level_num not in levels:
                            continue
                        level_str = {1: "Critical", 2: "Error", 4: "Warning"}.get(level_num, "Other")
                        source = event.SourceName
                        desc = str(event.StringInserts) if event.StringInserts else "No description."
                        details = f"Event ID: {event.EventID & 0xFFFF} | Category: {event.EventCategory}"
                        text = (desc + " " + details).lower()
                        if (not keyword or difflib.SequenceMatcher(None, keyword, text).ratio() > 0.625 or keyword in text) and \
                           (not error_code or error_code in text):
                            friendly_desc = self._synthesize_log(source, desc, details)
                            logs[log_type].append((event_time, level_str, source, friendly_desc, details))
                    events = win32evtlog.ReadEventLog(hand, flags, 0)
                win32evtlog.CloseEventLog(hand)
            except Exception as e:
                self.logs_output.setText(f"Error reading {log_type} log: {str(e)}")
                return
        
        output = []
        error_count = sum(1 for log in logs.values() for _, level, _, _, _ in log if level in ["Critical", "Error"])
        warning_count = sum(1 for log in logs.values() for _, level, _, _, _ in log if level == "Warning")
        for log_type, events in logs.items():
            if events:
                output.append(f"\n{log_type} Log (Last {days} Days):")
                for time, level, source, friendly_desc, details in sorted(events, key=lambda x: x[0], reverse=True)[:5]:
                    output.append(f"- {time} | {level} | {source}: {friendly_desc} ({details})")
        if not any(logs.values()):
            self.logs_output.setText(f"No matching events found in the last {days} days.")
            return
        analysis = [
            f"\nSummary (Last {days} Days):",
            f"- Total Errors/Critical: {error_count}",
            f"- Total Warnings: {warning_count}"
        ]
        if error_count > 5:
            analysis.append("Several serious issues detected—check hardware or software problems.")
        elif warning_count > 10:
            analysis.append("Lots of warnings—your system might be unstable; look into frequent issues.")
        else:
            analysis.append("Things look mostly stable.")
        self.logs_output.setText("\n".join(output + analysis))

    def _synthesize_log(self, source, desc, details):
        known_issues = {
            "Application Error": lambda d: f"An app ({d.split('Event ID')[0].strip()}) crashed unexpectedly." if "crashed" not in d.lower() else d,
            "Windows Update": lambda d: "Windows Update hit a snag—might need a restart or manual update.",
            "Service Control Manager": lambda d: "A background service failed to start properly.",
            "DLL": lambda d: "A system file (DLL) didn’t load right—could be a missing or corrupt file."
        }
        for key, fn in known_issues.items():
            if key.lower() in source.lower() or key.lower() in desc.lower():
                return fn(desc)
        if "failed" in desc.lower():
            return f"Something ({source}) didn’t work as expected."
        elif "warning" in desc.lower():
            return f"System flagged a potential issue with {source}."
        return desc

    def update_process_table(self):
        self.process_table.setRowCount(0)
        for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
            try:
                row = self.process_table.rowCount()
                self.process_table.insertRow(row)
                self.process_table.setItem(row, 0, QTableWidgetItem(proc.info['name']))
                self.process_table.setItem(row, 1, QTableWidgetItem(str(proc.info['pid'])))
                self.process_table.setItem(row, 2, QTableWidgetItem(f"{proc.info['memory_info'].rss / (1024**2):.2f}"))
                priority = {psutil.BELOW_NORMAL_PRIORITY_CLASS: "Low", psutil.NORMAL_PRIORITY_CLASS: "Normal",
                            psutil.ABOVE_NORMAL_PRIORITY_CLASS: "High", psutil.REALTIME_PRIORITY_CLASS: "Realtime"}.get(
                            proc.nice(), "Unknown")
                self.process_table.setItem(row, 3, QTableWidgetItem(priority))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def kill_selected_process(self):
        selected = self.process_table.currentRow()
        if selected == -1:
            return
        pid = int(self.process_table.item(selected, 1).text())
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            self.update_process_table()
        except psutil.NoSuchProcess:
            self.update_process_table()

    def set_priority(self, priority_str):
        selected = self.process_table.currentRow()
        if selected == -1:
            return
        pid = int(self.process_table.item(selected, 1).text())
        priority_map = {"Low": psutil.BELOW_NORMAL_PRIORITY_CLASS, "Normal": psutil.NORMAL_PRIORITY_CLASS,
                        "High": psutil.ABOVE_NORMAL_PRIORITY_CLASS, "Realtime": psutil.REALTIME_PRIORITY_CLASS}
        try:
            proc = psutil.Process(pid)
            proc.nice(priority_map[priority_str])
            self.update_process_table()
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.process_table.setItem(selected, 3, QTableWidgetItem(f"Error: {str(e)}"))

    def check_disk_health(self):
        try:
            output = []
            for partition in psutil.disk_partitions():
                drive = partition.device.split("\\")[0]
                disk = Device(drive)
                if disk.smart_enabled:
                    health = disk.assessment if disk.assessment else "Unknown"
                    temp = disk.attributes[194].raw if 194 in disk.attributes else "N/A"
                    output.append(
                        f"Drive {drive} ({disk.model}):\n"
                        f"- Health: {health}\n"
                        f"- Temperature: {temp}°C\n"
                        f"- Type: {disk.interface}"
                    )
                else:
                    output.append(f"Drive {drive}: SMART not supported.")
            return "\n".join(output) if output else "No SMART-capable drives found."
        except Exception as e:
            return f"Error checking disk health: {str(e)}. Ensure smartctl is installed and run as admin."

    def run_benchmark(self):
        self.benchmark_output.setText("Running benchmark—this will take about 10 seconds...")
        QApplication.processEvents()
        start = time.time()
        for _ in range(1000000):
            _ = 12345 * 67890
        cpu_time = time.time() - start
        cpu_score = 1000000 / cpu_time / 1000
        data = bytearray(1024 * 1024 * 100)
        start = time.time()
        _ = data[:]
        mem_time = time.time() - start
        mem_score = 100 / mem_time
        test_file = "reports/benchmark_test.bin"
        with open(test_file, "wb") as f:
            start = time.time()
            f.write(data)
        disk_write_time = time.time() - start
        with open(test_file, "rb") as f:
            start = time.time()
            _ = f.read()
        disk_read_time = time.time() - start
        disk_score = 100 / (disk_write_time + disk_read_time)
        os.remove(test_file)
        return f"Benchmark Results:\n- CPU: {cpu_score:.1f} kOps/s\n- Memory: {mem_score:.1f} MB/s\n- Disk: {disk_score:.1f} MB/s (write + read)"

    def update_power_plans(self):
        self.power_combo.clear()
        result = subprocess.run("powercfg /list", capture_output=True, text=True)
        plans = {}
        for line in result.stdout.splitlines():
            if "GUID" in line:
                guid = line.split()[3]
                name = " ".join(line.split()[4:]).strip("*")
                plans[name] = guid
        for name in plans.keys():
            self.power_combo.addItem(name, plans[name])

    def set_power_plan_ui(self):
        selected_guid = self.power_combo.currentData()
        if selected_guid:
            subprocess.run(f"powercfg /setactive {selected_guid}", shell=True)
            self.power_output.setText(f"Activated power plan: {self.power_combo.currentText()}")
        else:
            self.power_output.setText("No power plan selected.")

    def update_graphs(self):
        cpu_percent = psutil.cpu_percent(interval=None)
        self.cpu_data.append(cpu_percent)
        if len(self.cpu_data) > 20:
            self.cpu_data.pop(0)
        self.cpu_ax.clear()
        self.cpu_ax.plot(self.cpu_data, label="CPU Usage (%)", color="blue")
        self.cpu_ax.set_ylim(0, 100)
        self.cpu_ax.set_title("CPU Usage Over Time")
        self.cpu_ax.legend()
        self.cpu_canvas.draw()

        try:
            gpus = GPUtil.getGPUs()
            gpu_usage = gpus[0].load * 100 if gpus else 0
        except:
            gpu_usage = 0
        self.gpu_data.append(gpu_usage)
        if len(self.gpu_data) > 20:
            self.gpu_data.pop(0)
        self.gpu_ax.clear()
        self.gpu_ax.plot(self.gpu_data, label="GPU Usage (%)", color="green")
        self.gpu_ax.set_ylim(0, 100)
        self.gpu_ax.set_title("GPU Usage Over Time")
        self.gpu_ax.legend()
        self.gpu_canvas.draw()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  
    window = AISysManagerUI()
    window.show()
    sys.exit(app.exec_())
