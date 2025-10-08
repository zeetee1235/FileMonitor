#!/usr/bin/env python3
"""
Simple Interactive File Monitor Menu
Arrow keys and Enter navigation
"""

import os
import sys
import subprocess
from pathlib import Path

import inquirer
from inquirer.themes import GreenPassion
from rich.console import Console

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
                ('View status', 'status'),
                ('View logs', 'logs'),
                ('Configuration', 'config'),
                ('Build program', 'build'),
                ('Performance stats', 'perf'),
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
        """Show status"""
        console.clear()
        console.print("Monitor Status")
        console.print("=" * 15)
        
        stdout, stderr, code = self.run_fmon_command("status")
        
        if stdout:
            console.print(stdout)
        if stderr:
            console.print(f"Error: {stderr}")
            
        input("\nPress Enter to continue...")

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
        """Show performance statistics"""
        console.clear()
        console.print("Performance Statistics")
        console.print("=" * 25)
        
        stdout, stderr, code = self.run_fmon_command("perf")
        
        if stdout:
            console.print(stdout)
        if stderr:
            console.print(f"Error: {stderr}")
            
        input("\nPress Enter to continue...")

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