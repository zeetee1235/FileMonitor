#!/usr/bin/env python3
"""
인터랙티브 파일 모니터 메뉴
방향키와 엔터로 조작 가능한 TUI 인터페이스
"""

import os
import sys
import time
import subprocess
from pathlib import Path

import inquirer
from inquirer.themes import GreenPassion
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

class InteractiveFileMonitor:
    def __init__(self):
        self.pid_file = "monitor.pid"
        self.log_file = "monitor.log" 
        self.config_file = "monitor.conf"
        
    def is_monitor_running(self):
        """모니터가 실행 중인지 확인"""
        if os.path.exists(self.pid_file):
            try:
                with open(self.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                os.kill(pid, 0)  # 프로세스 존재 확인
                return True, pid
            except (ProcessLookupError, ValueError):
                if os.path.exists(self.pid_file):
                    os.remove(self.pid_file)
                return False, None
        return False, None

    def run_fmon_command(command):
        """fmon.py 명령 실행"""
        try:
            # 상위 디렉토리에서 src/fmon.py를 실행
            result = subprocess.run([sys.executable, 'src/fmon.py'] + command.split(), 
                                capture_output=True, text=True, cwd='..')
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return "", str(e), 1

    def show_welcome(self):
        """환영 메시지 표시"""
        console.clear()
        
        welcome_text = """[bold cyan]🔍 File Monitor Interactive CLI[/bold cyan]

[dim]A modern file system monitoring tool with interactive interface[/dim]

[yellow]How to use:[/yellow]
• Use [bold]↑↓ arrow keys[/bold] to navigate
• Press [bold]Enter[/bold] to select
• Press [bold]Ctrl+C[/bold] to exit anytime
"""
        
        welcome_panel = Panel(
            welcome_text,
            title="Welcome",
            border_style="cyan",
            padding=(1, 2)
        )
        console.print(welcome_panel)
        console.print()

    def show_status_info(self):
        """현재 상태 정보 표시"""
        is_running, pid = self.is_monitor_running()
        
        # 상태 테이블 생성
        status_table = Table(box=box.ROUNDED, show_header=False, padding=(0, 1))
        status_table.add_column("Item", style="cyan")
        status_table.add_column("Value")
        
        if is_running:
            status_table.add_row("Status", "[green]🟢 Running[/green]")
            status_table.add_row("PID", str(pid))
        else:
            status_table.add_row("Status", "[red]🔴 Stopped[/red]")
            
        # 로그 파일 정보
        if os.path.exists(self.log_file):
            size = os.path.getsize(self.log_file)
            status_table.add_row("Log Size", f"{size:,} bytes")
        else:
            status_table.add_row("Log File", "[dim]Not found[/dim]")
            
        return status_table

    def main_menu(self):
        """메인 메뉴 표시"""
        while True:
            self.show_welcome()
            
            # 상태 정보 표시
            status_table = self.show_status_info()
            console.print(Panel(status_table, title="📊 Current Status", border_style="blue"))
            console.print()
            
            # 메뉴 옵션
            is_running, _ = self.is_monitor_running()
            
            choices = []
            if not is_running:
                choices.append(('🚀 Start monitoring', 'start'))
            else:
                choices.append(('⏹️  Stop monitoring', 'stop'))
                
            choices.extend([
                ('📊 View detailed status', 'status'),
                ('📄 View logs', 'logs'),
                ('⚙️  Configuration', 'config'),
                ('🔨 Build C program', 'build'),
                ('📺 Real-time dashboard', 'dashboard'),
                ('❌ Exit', 'exit')
            ])
            
            questions = [
                inquirer.List(
                    'action',
                    message="What would you like to do?",
                    choices=choices,
                    carousel=True
                ),
            ]
            
            try:
                answers = inquirer.prompt(questions, theme=GreenPassion())
                if not answers:  # ESC 또는 Ctrl+C
                    break
                    
                action = answers['action']
                
                if action == 'exit':
                    console.print("\n[yellow]👋 Goodbye![/yellow]")
                    break
                elif action == 'start':
                    self.start_menu()
                elif action == 'stop':
                    self.stop_monitoring()
                elif action == 'status':
                    self.show_detailed_status()
                elif action == 'logs':
                    self.logs_menu()
                elif action == 'config':
                    self.config_menu()
                elif action == 'build':
                    self.build_program()
                elif action == 'dashboard':
                    self.show_dashboard()
                    
            except KeyboardInterrupt:
                console.print("\n[yellow]👋 Goodbye![/yellow]")
                break

    def start_menu(self):
        """모니터링 시작 메뉴"""
        console.clear()
        console.print(Panel("🚀 Start File Monitoring", border_style="green"))
        console.print()
        
        questions = [
            inquirer.Path(
                'path',
                message="Select directory to monitor",
                path_type=inquirer.Path.DIRECTORY,
                default='.',
                exists=True
            ),
            inquirer.Confirm(
                'background',
                message="Run in background?",
                default=True
            ),
            inquirer.Confirm(
                'recursive',
                message="Monitor subdirectories recursively?", 
                default=True
            )
        ]
        
        answers = inquirer.prompt(questions, theme=GreenPassion())
        if answers:
            args = [answers['path']]
            if answers['background']:
                args.append('--background')
                
            console.print(f"\n[yellow]Starting monitoring on: {answers['path']}[/yellow]")
            stdout, stderr, code = self.run_fmon_command(['start'] + args)
            
            if code == 0:
                console.print(stdout)
            else:
                console.print(f"[red]Error: {stderr}[/red]")
                
        self.wait_for_key()

    def stop_monitoring(self):
        """모니터링 중지"""
        console.clear()
        console.print(Panel("⏹️ Stop File Monitoring", border_style="red"))
        console.print()
        
        stdout, stderr, code = self.run_fmon_command(['stop'])
        if code == 0:
            console.print(stdout)
        else:
            console.print(f"[red]Error: {stderr}[/red]")
            
        self.wait_for_key()

    def show_detailed_status(self):
        """상세 상태 보기"""
        console.clear()
        console.print(Panel("📊 Detailed Status", border_style="blue"))
        console.print()
        
        stdout, stderr, code = self.run_fmon_command(['status'])
        if code == 0:
            console.print(stdout)
        else:
            console.print(f"[red]Error: {stderr}[/red]")
            
        self.wait_for_key()

    def logs_menu(self):
        """로그 메뉴"""
        console.clear()
        console.print(Panel("📄 Log Management", border_style="yellow"))
        console.print()
        
        questions = [
            inquirer.List(
                'log_action',
                message="Select log action:",
                choices=[
                    ('📄 Show recent logs', 'show'),
                    ('📺 Tail logs (real-time)', 'tail'),
                    ('📊 Log statistics', 'stats'),
                    ('🔍 Search logs', 'search'),
                    ('🧹 Clean logs', 'clean'),
                    ('⬅️ Back to main menu', 'back')
                ],
                carousel=True
            ),
        ]
        
        answers = inquirer.prompt(questions, theme=GreenPassion())
        if answers and answers['log_action'] != 'back':
            action = answers['log_action']
            
            if action == 'show':
                lines_question = [
                    inquirer.Text('lines', message="Number of lines to show", default="20")
                ]
                lines_answer = inquirer.prompt(lines_question, theme=GreenPassion())
                if lines_answer:
                    stdout, stderr, code = self.run_fmon_command(['logs', 'show', '-n', lines_answer['lines']])
                    
            elif action == 'search':
                search_question = [
                    inquirer.Text('query', message="Enter search query:")
                ]
                search_answer = inquirer.prompt(search_question, theme=GreenPassion())
                if search_answer:
                    stdout, stderr, code = self.run_fmon_command(['logs', 'search', search_answer['query']])
                    
            elif action == 'tail':
                console.print("[yellow]Starting real-time log monitoring...[/yellow]")
                console.print("[dim]Press Ctrl+C to stop[/dim]")
                time.sleep(1)
                # tail은 별도 처리 (실시간이므로)
                try:
                    subprocess.run([sys.executable, 'fmon.py', 'logs', 'tail'])
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopped log monitoring[/yellow]")
                self.wait_for_key()
                return
                
            else:
                stdout, stderr, code = self.run_fmon_command(['logs', action])
            
            if code == 0:
                console.print(stdout)
            else:
                console.print(f"[red]Error: {stderr}[/red]")
                
            self.wait_for_key()

    def config_menu(self):
        """설정 메뉴"""
        console.clear()
        console.print(Panel("⚙️ Configuration Management", border_style="magenta"))
        console.print()
        
        questions = [
            inquirer.List(
                'config_action',
                message="Select configuration action:",
                choices=[
                    ('👁️ Show current config', 'show'),
                    ('⚙️ Change settings', 'set'),
                    ('📦 Apply preset', 'preset'),
                    ('⬅️ Back to main menu', 'back')
                ],
                carousel=True
            ),
        ]
        
        answers = inquirer.prompt(questions, theme=GreenPassion())
        if answers and answers['config_action'] != 'back':
            action = answers['config_action']
            
            if action == 'show':
                stdout, stderr, code = self.run_fmon_command(['config', 'show'])
                
            elif action == 'preset':
                preset_question = [
                    inquirer.List(
                        'preset_type',
                        message="Select preset:",
                        choices=[
                            ('Developer (py, js, html, etc.)', 'dev'),
                            ('Log files (log, err, out, etc.)', 'log'),
                            ('All files', 'all'),
                            ('Web development (html, css, js, etc.)', 'web')
                        ]
                    )
                ]
                preset_answer = inquirer.prompt(preset_question, theme=GreenPassion())
                if preset_answer:
                    preset_map = {
                        'Developer (py, js, html, etc.)': 'dev',
                        'Log files (log, err, out, etc.)': 'log', 
                        'All files': 'all',
                        'Web development (html, css, js, etc.)': 'web'
                    }
                    stdout, stderr, code = self.run_fmon_command(['config', 'preset', preset_map[preset_answer['preset_type']]])
                    
            elif action == 'set':
                set_questions = [
                    inquirer.Confirm('recursive', message="Enable recursive monitoring?", default=True),
                    inquirer.Text('extensions', message="File extensions (comma-separated, e.g., py,js,html):", default="")
                ]
                set_answers = inquirer.prompt(set_questions, theme=GreenPassion())
                if set_answers:
                    args = ['config', 'set']
                    if set_answers['recursive']:
                        args.append('--recursive')
                    else:
                        args.append('--no-recursive')
                        
                    if set_answers['extensions']:
                        extensions = [ext.strip() for ext in set_answers['extensions'].split(',')]
                        for ext in extensions:
                            args.extend(['--extensions', ext])
                            
                    stdout, stderr, code = self.run_fmon_command(args)
            
            if code == 0:
                console.print(stdout)
            else:
                console.print(f"[red]Error: {stderr}[/red]")
                
            self.wait_for_key()

    def build_program(self):
        """C 프로그램 빌드"""
        console.clear()
        console.print(Panel("🔨 Build C Program", border_style="cyan"))
        console.print()
        
        stdout, stderr, code = self.run_fmon_command(['build'])
        if code == 0:
            console.print(stdout)
        else:
            console.print(f"[red]Error: {stderr}[/red]")
            
        self.wait_for_key()

    def show_dashboard(self):
        """대시보드 표시"""
        console.clear()
        console.print(Panel("📺 Real-time Dashboard", border_style="green"))
        console.print()
        console.print("[yellow]Starting dashboard... Press Q to quit[/yellow]")
        time.sleep(1)
        
        try:
            subprocess.run([sys.executable, 'fmon.py', 'dashboard'])
        except KeyboardInterrupt:
            console.print("\n[yellow]Dashboard stopped[/yellow]")
            
        self.wait_for_key()

    def wait_for_key(self):
        """키 입력 대기"""
        console.print("\n[dim]Press Enter to continue...[/dim]")
        input()

def main():
    """메인 함수"""
    try:
        monitor = InteractiveFileMonitor()
        monitor.main_menu()
    except KeyboardInterrupt:
        console.print("\n[yellow]👋 Goodbye![/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

if __name__ == "__main__":
    main()
