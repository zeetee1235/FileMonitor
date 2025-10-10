#!/usr/bin/env python3
"""
Simple Interactive File Monitor Menu
Arrow keys and Enter navigation
"""

import os
import sys
import subprocess
import time
import json
import threading
from pathlib import Path

import inquirer
from inquirer.themes import GreenPassion
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich import box

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

console = Console()

class InteractiveFileMonitor:
    def __init__(self):
        self.pid_file = "monitor.pid"
        self.log_file = "monitor.log" 
        self.config_file = "monitor.conf"
        
    def is_monitor_running(self):
        """Check if monitor is running"""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)  # Check if process exists
                return True, pid
            except (ProcessLookupError, ValueError):
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
                return False, None
        return False, None

    def run_fmon_command(self, command):
        """Execute fmon.py command"""
        try:
            # Run src/fmon.py from current directory
            result = subprocess.run([sys.executable, 'src/fmon.py'] + command.split(), 
                                capture_output=True, text=True)
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def main_menu(self):
        """Main menu"""
        while True:
            console.clear()
            
            # Header
            console.print("File Monitor Interactive Menu")
            console.print("=" * 40)
            
            # Status
            is_running, pid = self.is_monitor_running()
            if is_running:
                console.print(f"Status: Running (PID: {pid})")
            else:
                console.print("Status: Stopped")
            
            console.print()
            
            # Menu options
            choices = []
            if not is_running:
                choices.append(('Start monitoring', 'start'))
            else:
                choices.append(('Stop monitoring', 'stop'))
                
            choices.extend([
                ('View status (real-time)', 'status'),
                ('View logs', 'logs'),
                ('Configuration', 'config'),
                ('Build program', 'build'),
                ('Performance stats (real-time)', 'perf'),
                ('Exit', 'exit')
            ])
            
            questions = [
                inquirer.List(
                    'action',
                    message="Select action:",
                    choices=choices,
                    carousel=True
                ),
            ]
            
            try:
                answers = inquirer.prompt(questions, theme=GreenPassion())
                if not answers:  # ESC or Ctrl+C
                    break
                    
                action = answers['action']
                
                if action == 'exit':
                    console.print("\nExiting...")
                    break
                elif action == 'start':
                    self.start_menu()
                elif action == 'stop':
                    self.stop_monitoring()
                elif action == 'status':
                    self.show_status()
                elif action == 'logs':
                    self.logs_menu()
                elif action == 'config':
                    self.config_menu()
                elif action == 'build':
                    self.build_program()
                elif action == 'perf':
                    self.show_performance()
                    
            except KeyboardInterrupt:
                console.print("\nExiting...")
                break

    def start_menu(self):
        """Start monitoring menu"""
        console.clear()
        console.print("Start Monitoring")
        console.print("=" * 20)
        
        choices = [
            ('Current directory', '.'),
            ('Parent directory', 'parent'),
            ('Project root (auto-detect)', 'project-root'),
            ('Choose specific directory', 'choose'),
            ('Advanced monitoring', 'advanced'),
            ('Back to main menu', 'back')
        ]
        
        questions = [
            inquirer.List('option', message="Monitor what?", choices=choices, carousel=True)
        ]
        
        try:
            answers = inquirer.prompt(questions, theme=GreenPassion())
            if not answers:
                return
                
            option = answers['option']
            
            if option == 'back':
                return
            elif option == 'parent':
                # Parent directory options
                level_choices = [
                    ('1 level up (parent)', '1'),
                    ('2 levels up (grandparent)', '2'), 
                    ('3 levels up', '3'),
                    ('Back', 'back')
                ]
                level_q = [inquirer.List('levels', message="How many levels up?", choices=level_choices)]
                level_ans = inquirer.prompt(level_q, theme=GreenPassion())
                if not level_ans or level_ans['levels'] == 'back':
                    return
                
                cmd = f"start . --parent -l {level_ans['levels']} --background"
                
            elif option == 'project-root':
                cmd = "start . --project-root --background"
                
            elif option == 'choose':
                # Simple directory input
                path = input("Enter directory path: ").strip()
                if not path:
                    path = '.'
                cmd = f"start {path} --background"
                
            elif option == 'advanced':
                # Advanced monitoring with options
                adv_choices = [
                    ('Current directory', '.'),
                    ('Parent directory', 'parent'),
                    ('Project root', 'project-root'),
                    ('Back', 'back')
                ]
                adv_q = [inquirer.List('target', message="Advanced monitoring target:", choices=adv_choices)]
                adv_ans = inquirer.prompt(adv_q, theme=GreenPassion())
                if not adv_ans or adv_ans['target'] == 'back':
                    return
                    
                if adv_ans['target'] == 'parent':
                    cmd = "start . --parent --advanced --background"
                elif adv_ans['target'] == 'project-root':
                    cmd = "start . --project-root --advanced --background"
                else:
                    cmd = f"start {adv_ans['target']} --advanced --background"
            else:
                cmd = f"start {option} --background"
                
            console.print(f"\nExecuting: {cmd}")
            
            stdout, stderr, code = self.run_fmon_command(cmd)
            
            if stdout:
                console.print(stdout)
            if stderr:
                console.print(f"Error: {stderr}")
                
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            return

    def stop_monitoring(self):
        """Stop monitoring"""
        console.print("\nStopping monitor...")
        stdout, stderr, code = self.run_fmon_command("stop")
        
        if stdout:
            console.print(stdout)
        if stderr:
            console.print(f"Error: {stderr}")
            
        input("\nPress Enter to continue...")

    def show_status(self):
        """Show real-time status"""
        console.clear()
        console.print("Real-time Monitor Status")
        console.print("Press Ctrl+C to exit or wait for auto-refresh every 2 seconds")
        console.print("=" * 60)
        
        try:
            with Live(self.generate_status_display(), refresh_per_second=2, screen=False) as live:
                start_time = time.time()
                while True:
                    time.sleep(0.5)
                    live.update(self.generate_status_display())
                    
                    # Auto-exit after 30 seconds if no interaction
                    if time.time() - start_time > 30:
                        console.print("\n[dim]Auto-exiting after 30 seconds...[/dim]")
                        break
                        
        except KeyboardInterrupt:
            console.print("\n[dim]Exiting real-time status...[/dim]")
        
        input("\nPress Enter to continue...")
    
    def generate_status_display(self):
        """Generate real-time status display"""
        from rich.columns import Columns
        
        # Get status from fmon command
        stdout, stderr, code = self.run_fmon_command("status")
        
        panels = []
        
        # Main status panel
        status_content = stdout if stdout else "Error getting status"
        panels.append(Panel(status_content, title="Monitor Status", border_style="green"))
        
        # System resources panel (if psutil available)
        if PSUTIL_AVAILABLE:
            panels.append(self.get_system_resources_panel())
        else:
            panels.append(Panel(
                "System resource monitoring unavailable\nInstall psutil: pip install psutil", 
                title="System Resources", 
                border_style="dim"
            ))
        
        # Enhanced stats panel
        enhanced_panel = self.get_enhanced_stats_panel()
        if enhanced_panel:
            panels.append(enhanced_panel)
        
        return Columns(panels, equal=True, expand=True)
    
    def get_system_resources_panel(self):
        """Get system resources panel"""
        if not PSUTIL_AVAILABLE:
            return None
            
        # CPU and Memory
        cpu_percent = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory()
        
        # Monitor process resources
        monitor_info = ""
        is_running, pid = self.is_monitor_running()
        if is_running:
            try:
                process = psutil.Process(pid)
                cpu_usage = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024
                monitor_info = f"Monitor CPU: {cpu_usage:.1f}%\nMonitor RAM: {memory_mb:.1f}MB"
            except:
                monitor_info = "Monitor process info unavailable"
        else:
            monitor_info = "No monitor running"
        
        content = f"""System CPU: {cpu_percent:.1f}%
System RAM: {memory.percent:.1f}% ({memory.used/1024/1024/1024:.1f}GB used)

{monitor_info}

Updated: {time.strftime('%H:%M:%S')}"""
        
        return Panel(content, title="System Resources", border_style="blue")
    
    def get_enhanced_stats_panel(self):
        """Get enhanced monitor statistics panel"""
        stats_file = "enhanced_stats.json"
        if not os.path.exists(stats_file):
            return None
            
        try:
            with open(stats_file, 'r') as f:
                stats = json.load(f)
            
            uptime = stats.get('uptime_seconds', 0)
            hours = uptime // 3600
            minutes = (uptime % 3600) // 60
            seconds = uptime % 60
            
            content = f"""Total Events: {stats.get('total_events', 0):,}
Active Watches: {stats.get('active_watches', 0):,}
Memory Usage: {stats.get('memory_usage_kb', 0):,} KB
Watch Capacity: {stats.get('watch_capacity', 0):,}
Watch Limit Hits: {stats.get('watch_limit_hits', 0)}
Memory Reallocations: {stats.get('memory_reallocations', 0)}

Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"""
            
            return Panel(content, title="Enhanced Monitor Stats", border_style="yellow")
        except:
            return Panel("Error reading enhanced stats", title="Enhanced Monitor Stats", border_style="red")

    def logs_menu(self):
        """Logs menu"""
        console.clear()
        console.print("Log Viewer")
        console.print("=" * 12)
        
        choices = [
            ('Recent logs', 'recent'),
            ('Real-time logs', 'tail'),
            ('Search logs', 'search'),
            ('Back', 'back')
        ]
        
        questions = [
            inquirer.List('option', message="Log action:", choices=choices, carousel=True)
        ]
        
        try:
            answers = inquirer.prompt(questions, theme=GreenPassion())
            if not answers or answers['option'] == 'back':
                return
                
            option = answers['option']
            
            if option == 'recent':
                stdout, stderr, code = self.run_fmon_command("logs show")
            elif option == 'tail':
                console.print("Starting real-time log view (Press Ctrl+C to stop)")
                stdout, stderr, code = self.run_fmon_command("logs tail")
            elif option == 'search':
                query = input("Search query: ").strip()
                if query:
                    stdout, stderr, code = self.run_fmon_command(f"logs search '{query}'")
                else:
                    return
            
            if stdout:
                console.print(stdout)
            if stderr:
                console.print(f"Error: {stderr}")
                
            if option != 'tail':
                input("\nPress Enter to continue...")
                
        except KeyboardInterrupt:
            return

    def config_menu(self):
        """Configuration menu"""
        console.clear()
        console.print("Configuration")
        console.print("=" * 15)
        
        choices = [
            ('View config', 'show'),
            ('Edit config', 'edit'),
            ('Back', 'back')
        ]
        
        questions = [
            inquirer.List('option', message="Config action:", choices=choices, carousel=True)
        ]
        
        try:
            answers = inquirer.prompt(questions, theme=GreenPassion())
            if not answers or answers['option'] == 'back':
                return
                
            option = answers['option']
            
            if option == 'show':
                stdout, stderr, code = self.run_fmon_command("config show")
            elif option == 'edit':
                console.print("Current configuration will be replaced.")
                recursive = input("Recursive monitoring? (y/n): ").strip().lower() == 'y'
                extensions = input("File extensions (comma-separated, empty for all): ").strip()
                
                cmd = f"config set {'--recursive' if recursive else '--no-recursive'}"
                if extensions:
                    for ext in extensions.split(','):
                        ext = ext.strip()
                        if ext:
                            cmd += f" -e {ext}"
                
                stdout, stderr, code = self.run_fmon_command(cmd)
            
            if stdout:
                console.print(stdout)
            if stderr:
                console.print(f"Error: {stderr}")
                
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            return

    def build_program(self):
        """Build program"""
        console.clear()
        console.print("Build Program")
        console.print("=" * 15)
        
        choices = [
            ('Build all', 'all'),
            ('Build basic only', 'main'),
            ('Build advanced only', 'advanced'),
            ('Back', 'back')
        ]
        
        questions = [
            inquirer.List('target', message="Build target:", choices=choices, carousel=True)
        ]
        
        try:
            answers = inquirer.prompt(questions, theme=GreenPassion())
            if not answers or answers['target'] == 'back':
                return
                
            target = answers['target']
            console.print(f"\nBuilding {target}...")
            
            stdout, stderr, code = self.run_fmon_command(f"build -t {target}")
            
            if stdout:
                console.print(stdout)
            if stderr:
                console.print(f"Error: {stderr}")
                
            input("\nPress Enter to continue...")
            
        except KeyboardInterrupt:
            return

    def show_performance(self):
        """Show real-time performance statistics"""
        console.clear()
        console.print("Real-time Performance Statistics")
        console.print("Press Ctrl+C to exit or wait for auto-refresh every 2 seconds")
        console.print("=" * 60)
        
        try:
            with Live(self.generate_performance_display(), refresh_per_second=2, screen=False) as live:
                start_time = time.time()
                while True:
                    time.sleep(0.5)
                    live.update(self.generate_performance_display())
                    
                    # Auto-exit after 30 seconds if no interaction
                    if time.time() - start_time > 30:
                        console.print("\n[dim]Auto-exiting after 30 seconds...[/dim]")
                        break
                        
        except KeyboardInterrupt:
            console.print("\n[dim]Exiting real-time performance...[/dim]")
        
        input("\nPress Enter to continue...")
    
    def generate_performance_display(self):
        """Generate real-time performance display"""
        from rich.columns import Columns
        
        panels = []
        
        # Get performance stats from fmon command
        stdout, stderr, code = self.run_fmon_command("perf")
        
        # Main performance panel
        perf_content = stdout if stdout else "No performance data available"
        panels.append(Panel(perf_content, title="Performance Statistics", border_style="green"))
        
        # Real-time system metrics
        if PSUTIL_AVAILABLE:
            panels.append(self.get_realtime_metrics_panel())
        
        # File system activity
        panels.append(self.get_file_activity_panel())
        
        return Columns(panels, equal=True, expand=True)
    
    def get_realtime_metrics_panel(self):
        """Get real-time system metrics"""
        if not PSUTIL_AVAILABLE:
            return Panel("psutil not available", title="System Metrics", border_style="red")
        
        # CPU and Memory details
        cpu_percent = psutil.cpu_percent(interval=None, percpu=True)
        cpu_avg = sum(cpu_percent) / len(cpu_percent)
        memory = psutil.virtual_memory()
        
        # Disk I/O
        try:
            disk_io = psutil.disk_io_counters()
            disk_info = f"Disk Read: {disk_io.read_bytes/1024/1024:.1f}MB\nDisk Write: {disk_io.write_bytes/1024/1024:.1f}MB"
        except:
            disk_info = "Disk I/O: Unavailable"
        
        # Network I/O
        try:
            net_io = psutil.net_io_counters()
            net_info = f"Net Sent: {net_io.bytes_sent/1024/1024:.1f}MB\nNet Recv: {net_io.bytes_recv/1024/1024:.1f}MB"
        except:
            net_info = "Network I/O: Unavailable"
        
        # Process count
        try:
            process_count = len(psutil.pids())
        except:
            process_count = "Unknown"
        
        content = f"""CPU Average: {cpu_avg:.1f}%
CPU Cores: {', '.join([f'{c:.0f}%' for c in cpu_percent[:4]])}{'...' if len(cpu_percent) > 4 else ''}

Memory: {memory.percent:.1f}%
Available: {memory.available/1024/1024/1024:.1f}GB
Used: {memory.used/1024/1024/1024:.1f}GB

{disk_info}

{net_info}

Processes: {process_count}
Timestamp: {time.strftime('%H:%M:%S')}"""
        
        return Panel(content, title="System Metrics", border_style="blue")
    
    def get_file_activity_panel(self):
        """Get file monitoring activity info"""
        content = ""
        
        # Check monitor processes
        is_running, pid = self.is_monitor_running()
        if is_running and PSUTIL_AVAILABLE:
            try:
                process = psutil.Process(pid)
                cpu_percent = process.cpu_percent()
                memory_mb = process.memory_info().rss / 1024 / 1024
                num_fds = process.num_fds() if hasattr(process, 'num_fds') else "N/A"
                
                content += f"Monitor Process:\n"
                content += f"  PID: {pid}\n"
                content += f"  CPU: {cpu_percent:.1f}%\n"
                content += f"  Memory: {memory_mb:.1f}MB\n"
                content += f"  File Descriptors: {num_fds}\n\n"
            except:
                content += "Monitor Process: Error getting info\n\n"
        else:
            content += "Monitor Process: Not running\n\n"
        
        # Enhanced monitor stats
        if os.path.exists("enhanced_stats.json"):
            try:
                with open("enhanced_stats.json", 'r') as f:
                    stats = json.load(f)
                
                content += "Enhanced Monitor:\n"
                content += f"  Events: {stats.get('total_events', 0):,}\n"
                content += f"  Watches: {stats.get('active_watches', 0):,}\n"
                content += f"  Memory: {stats.get('memory_usage_kb', 0):,}KB\n"
                content += f"  Expansions: {stats.get('memory_reallocations', 0)}\n"
                
                # Events per second calculation
                uptime = stats.get('uptime_seconds', 1)
                events_per_sec = stats.get('total_events', 0) / max(uptime, 1)
                content += f"  Events/sec: {events_per_sec:.2f}\n"
                
            except:
                content += "Enhanced Monitor: Error reading stats\n"
        else:
            content += "Enhanced Monitor: Not running\n"
        
        # Log file info
        if os.path.exists(self.log_file):
            try:
                stat_info = os.stat(self.log_file)
                size_mb = stat_info.st_size / 1024 / 1024
                mod_time = time.strftime('%H:%M:%S', time.localtime(stat_info.st_mtime))
                content += f"\nLog File:\n"
                content += f"  Size: {size_mb:.2f}MB\n"
                content += f"  Modified: {mod_time}\n"
            except:
                content += "\nLog File: Error accessing\n"
        
        if not content.strip():
            content = "No file monitoring activity detected"
        
        return Panel(content, title="File Activity", border_style="yellow")

def main():
    """Main function"""
    try:
        monitor = InteractiveFileMonitor()
        monitor.main_menu()
    except KeyboardInterrupt:
        console.print("\nExiting...")
    except Exception as e:
        console.print(f"Error: {e}")

if __name__ == "__main__":
    main()