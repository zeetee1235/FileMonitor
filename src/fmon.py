#!/usr/bin/env python3
"""
파일 모니터 CLI 도구
Rich를 사용한 현대적인 터미널 인터페이스
"""

import os
import sys
import time
import signal
import socket
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich.tree import Tree
from rich import box
import inquirer
from inquirer.themes import GreenPassion


console = Console()

# 상수 정의
IPC_SOCKET_PATH = "/tmp/file_monitor.sock"
PID_FILE = "monitor.pid"
LOG_FILE = "monitor.log"
CONFIG_FILE = "monitor.conf"

class MonitorIPC:
    """모니터 프로세스와 IPC 통신을 담당하는 클래스"""
    
    def __init__(self):
        self.socket_path = IPC_SOCKET_PATH
        
    def send_command(self, command: str, data: dict = None) -> dict:
        """모니터 프로세스에 명령 전송"""
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(self.socket_path)
            
            message = {
                "command": command,
                "data": data or {}
            }
            
            sock.send(json.dumps(message).encode())
            response = sock.recv(4096).decode()
            sock.close()
            
            return json.loads(response)
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def is_monitor_running(self) -> bool:
        """모니터가 실행 중인지 확인"""
        return os.path.exists(self.socket_path)

class ConfigManager:
    """설정 파일 관리 클래스"""
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        
    def load_config(self) -> dict:
        """설정 파일 로드"""
        config = {
            "recursive": True,
            "extensions": []
        }
        
        if not os.path.exists(self.config_path):
            return config
            
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('#') or not line:
                        continue
                        
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        
                        if key == "recursive":
                            config["recursive"] = value.lower() == "true"
                        elif key == "extension":
                            config["extensions"].append(value)
        except Exception as e:
            console.print(f"[red]Failed to load configuration file: {e}[/red]")
            
        return config
    
    def save_config(self, config: dict):
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write("# 파일 모니터 설정 파일\n")
                f.write("# 주석은 '#'으로 시작합니다\n\n")
                
                f.write(f"# 재귀적 디렉토리 모니터링\n")
                f.write(f"recursive={'true' if config['recursive'] else 'false'}\n\n")
                
                if config.get('extensions'):
                    f.write("# 모니터링할 파일 확장자\n")
                    for ext in config['extensions']:
                        f.write(f"extension={ext}\n")
                        
            console.print("[green]✓[/green] Configuration saved.")
        except Exception as e:
            console.print(f"[red]✗ Failed to save configuration: {e}[/red]")

class LogAnalyzer:
    """로그 분석 클래스"""
    
    def __init__(self, log_path: str = LOG_FILE):
        self.log_path = log_path
        
    def get_stats(self) -> dict:
        """로그 통계 분석"""
        stats = {
            "total_events": 0,
            "event_types": {},
            "daily_stats": {},
            "file_size": 0,
            "last_modified": None
        }
        
        if not os.path.exists(self.log_path):
            return stats
            
        try:
            file_stat = os.stat(self.log_path)
            stats["file_size"] = file_stat.st_size
            stats["last_modified"] = datetime.fromtimestamp(file_stat.st_mtime)
            
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    stats["total_events"] += 1
                    
                    # 이벤트 타입 분석
                    if "Created:" in line:
                        stats["event_types"]["created"] = stats["event_types"].get("created", 0) + 1
                    elif "Deleted:" in line:
                        stats["event_types"]["deleted"] = stats["event_types"].get("deleted", 0) + 1
                    elif "Modified:" in line:
                        stats["event_types"]["modified"] = stats["event_types"].get("modified", 0) + 1
                    elif "Moved" in line:
                        stats["event_types"]["moved"] = stats["event_types"].get("moved", 0) + 1
                    elif "Attribute changed:" in line:
                        stats["event_types"]["attribute"] = stats["event_types"].get("attribute", 0) + 1
                    elif "Opened:" in line:
                        stats["event_types"]["opened"] = stats["event_types"].get("opened", 0) + 1
                    elif "Closed:" in line:
                        stats["event_types"]["closed"] = stats["event_types"].get("closed", 0) + 1
                    
                    # 일별 통계
                    if line.startswith('['):
                        try:
                            date_str = line[1:11]  # YYYY-MM-DD
                            stats["daily_stats"][date_str] = stats["daily_stats"].get(date_str, 0) + 1
                        except:
                            pass
                            
        except Exception as e:
            console.print(f"[red]Log analysis failed: {e}[/red]")
            
        return stats
    
    def search_logs(self, query: str, limit: int = 50) -> list:
        """로그에서 검색"""
        results = []
        
        if not os.path.exists(self.log_path):
            return results
            
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if query.lower() in line.lower():
                        results.append(line.strip())
                        if len(results) >= limit:
                            break
        except Exception as e:
            console.print(f"[red]Log search failed: {e}[/red]")
            
        return results

def format_file_size(size_bytes: int) -> str:
    """파일 크기를 사람이 읽기 쉬운 형태로 변환"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"

@click.group(invoke_without_command=True)
@click.version_option(version="2.0.0")
@click.option('--interactive', '-i', is_flag=True, help='Start interactive mode')
@click.pass_context
def cli(ctx, interactive):
    """File Monitor CLI Tool v2.0.0
    
    A modern file system monitoring tool using Rich for beautiful terminal interface.
    """
    if interactive:
        # 인터랙티브 모드 실행
        try:
            import subprocess
            subprocess.run([sys.executable, 'src/interactive_menu.py'], cwd='..')
        except FileNotFoundError:
            console.print("[red]src/interactive_menu.py not found. Please ensure it's in the src directory.[/red]")
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 Goodbye![/yellow]")
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        # 명령어 없이 실행되면 help 표시
        console.print(ctx.get_help())

@cli.command()
@click.argument('path', default='.')
@click.option('--background', '-b', is_flag=True, help='Run in background')
@click.option('--config', '-c', default=CONFIG_FILE, help='Configuration file path')
def start(path: str, background: bool, config: str):
    """Start file monitoring"""
    
    # 경로 검증
    if not os.path.exists(path):
        console.print(f"[red]✗ Path not found: {path}[/red]")
        sys.exit(1)
    
    # 절대 경로로 변환
    abs_path = os.path.abspath(path)
    
    # 이미 실행 중인지 확인
    ipc = MonitorIPC()
    if ipc.is_monitor_running():
        console.print("[yellow]⚠ Monitor is already running.[/yellow]")
        if not Confirm.ask("Stop existing monitor and start new one?"):
            return
        else:
            # 기존 모니터 중지
            stop_monitor()
    
    # 설정 로드
    config_manager = ConfigManager(config)
    monitor_config = config_manager.load_config()
    
    # 패널로 시작 정보 표시
    panel_content = f"""[bold cyan]File Monitoring Started[/bold cyan]

[bold]Watch Directory:[/bold] {abs_path}
[bold]Recursive Mode:[/bold] {'Yes' if monitor_config['recursive'] else 'No'}
[bold]Execution Mode:[/bold] {'Background' if background else 'Foreground'}
[bold]Config File:[/bold] {config}
"""
    
    if monitor_config['extensions']:
        ext_text = ", ".join(monitor_config['extensions'][:10])
        if len(monitor_config['extensions']) > 10:
            ext_text += f" and {len(monitor_config['extensions']) - 10} more"
        panel_content += f"[bold]Filter Extensions:[/bold] {ext_text}\n"
    else:
        panel_content += "[bold]Filter:[/bold] All files\n"
    
    console.print(Panel(panel_content, title="🚀 Monitor Start", border_style="green"))
    
    # C 프로그램 실행
    try:
        if background:
            # 백그라운드에서 실행
            process = subprocess.Popen(
                ['./monitor', abs_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # PID 파일에 저장
            with open(PID_FILE, 'w') as f:
                f.write(str(process.pid))
            
            console.print(f"[green]✓ Monitor started in background. (PID: {process.pid})[/green]")
            console.print(f"[dim]Check logs: [bold]fmon logs --tail[/bold][/dim]")
            console.print(f"[dim]Check status: [bold]fmon status[/bold][/dim]")
            console.print(f"[dim]Stop monitor: [bold]fmon stop[/bold][/dim]")
        else:
            # 포그라운드에서 실행
            console.print("[dim]Press Ctrl+C to stop monitoring.[/dim]\n")
            
            process = subprocess.Popen(['./monitor', abs_path])
            
            try:
                process.wait()
            except KeyboardInterrupt:
                console.print("\n[yellow]⚠ Interrupted by user.[/yellow]")
                process.terminate()
                process.wait()
                
    except FileNotFoundError:
        console.print("[red]✗ monitor executable not found.[/red]")
        console.print("[dim]Build first: [bold]fmon build[/bold][/dim]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]✗ Failed to start monitor: {e}[/red]")
        sys.exit(1)

def stop_monitor():
    """실행 중인 모니터 중지"""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # 프로세스 종료
            os.kill(pid, signal.SIGTERM)
            
            # PID 파일 삭제
            os.remove(PID_FILE)
            
            console.print("[green]✓ Monitor stopped.[/green]")
            return True
            
        except (FileNotFoundError, ProcessLookupError):
            console.print("[yellow]⚠ PID file exists but process is not running.[/yellow]")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            return False
        except Exception as e:
            console.print(f"[red]✗ Failed to stop monitor: {e}[/red]")
            return False
    else:
        console.print("[yellow]⚠ No running monitor found.[/yellow]")
        return False

@cli.command()
def stop():
    """Stop file monitoring"""
    console.print("[bold]Stopping monitor...[/bold]")
    stop_monitor()

@cli.command()
def status():
    """Check monitor status"""
    
    # 테이블 생성
    table = Table(title="📊 File Monitor Status", box=box.ROUNDED)
    table.add_column("Item", style="cyan", no_wrap=True)
    table.add_column("Value", style="white")
    
    # 실행 상태 확인
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # 프로세스 존재 확인
            try:
                os.kill(pid, 0)
                table.add_row("Status", "[green]🟢 Running[/green]")
                table.add_row("PID", str(pid))
                
                # 프로세스 정보
                try:
                    import psutil
                    process = psutil.Process(pid)
                    start_time = datetime.fromtimestamp(process.create_time()).strftime("%Y-%m-%d %H:%M:%S")
                    table.add_row("Start Time", start_time)
                    table.add_row("Memory Usage", f"{process.memory_info().rss // 1024 // 1024} MB")
                except ImportError:
                    pass
                    
            except ProcessLookupError:
                table.add_row("Status", "[red]🔴 Stopped (PID file exists but no process)[/red]")
                os.remove(PID_FILE)
                
        except Exception as e:
            table.add_row("Status", f"[red]🔴 Error: {e}[/red]")
    else:
        table.add_row("Status", "[red]🔴 Stopped[/red]")
    
    # 로그 파일 정보
    if os.path.exists(LOG_FILE):
        stat = os.stat(LOG_FILE)
        table.add_row("Log File", LOG_FILE)
        table.add_row("Log Size", format_file_size(stat.st_size))
        table.add_row("Last Modified", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
        
        # 라인 수 계산
        try:
            with open(LOG_FILE, 'r') as f:
                line_count = sum(1 for _ in f)
            table.add_row("Log Lines", f"{line_count:,}")
        except:
            pass
    else:
        table.add_row("Log File", "[dim]None[/dim]")
    
    # 설정 파일 정보
    if os.path.exists(CONFIG_FILE):
        table.add_row("Config File", CONFIG_FILE)
        config_manager = ConfigManager()
        config = config_manager.load_config()
        table.add_row("Recursive Mode", "Yes" if config['recursive'] else "No")
        if config['extensions']:
            ext_text = ", ".join(config['extensions'][:5])
            if len(config['extensions']) > 5:
                ext_text += f" and {len(config['extensions']) - 5} more"
            table.add_row("Filter Extensions", ext_text)
        else:
            table.add_row("Filter", "All files")
    else:
        table.add_row("Config File", "[dim]None[/dim]")
    
    console.print(table)

@cli.group()
def logs():
    """Log management commands"""
    pass

@logs.command()
@click.option('--lines', '-n', default=20, help='Number of lines to display')
def show(lines: int):
    """View recent logs"""
    
    if not os.path.exists(LOG_FILE):
        console.print("[yellow]⚠ Log file not found.[/yellow]")
        return
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        console.print(Panel(
            f"Recent {len(recent_lines)} lines",
            title="📄 Log File",
            border_style="blue"
        ))
        
        for line in recent_lines:
            line = line.strip()
            if line:
                # 색상 적용
                if "Created:" in line:
                    console.print(f"[green]{line}[/green]")
                elif "Deleted:" in line:
                    console.print(f"[red]{line}[/red]")
                elif "Modified:" in line:
                    console.print(f"[yellow]{line}[/yellow]")
                elif "Moved" in line:
                    console.print(f"[blue]{line}[/blue]")
                elif "Error" in line or "Failed" in line:
                    console.print(f"[red]{line}[/red]")
                else:
                    console.print(line)
                    
    except Exception as e:
        console.print(f"[red]✗ Failed to read log: {e}[/red]")

@logs.command()
def tail():
    """Real-time log viewing"""
    
    if not os.path.exists(LOG_FILE):
        console.print("[yellow]⚠ Log file not found.[/yellow]")
        console.print("[dim]Start monitor first: [bold]fmon start[/bold][/dim]")
        return
    
    console.print(Panel(
        "Real-time log monitoring (Press Ctrl+C to exit)",
        title="📺 Live Log",
        border_style="cyan"
    ))
    
    try:
        # tail -f implementation
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            # Move to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    line = line.strip()
                    # 색상 적용
                    if "Created:" in line:
                        console.print(f"[green]{line}[/green]")
                    elif "Deleted:" in line:
                        console.print(f"[red]{line}[/red]")
                    elif "Modified:" in line:
                        console.print(f"[yellow]{line}[/yellow]")
                    elif "Moved" in line:
                        console.print(f"[blue]{line}[/blue]")
                    else:
                        console.print(line)
                else:
                    time.sleep(0.1)
                    
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Real-time log monitoring stopped.[/yellow]")
    except Exception as e:
        console.print(f"[red]✗ Log monitoring failed: {e}[/red]")

@logs.command()
def stats():
    """View log statistics"""
    
    analyzer = LogAnalyzer()
    stats = analyzer.get_stats()
    
    if stats["total_events"] == 0:
        console.print("[yellow]⚠ No log data available.[/yellow]")
        return
    
    # Statistics table
    table = Table(title="📈 Log Statistics", box=box.ROUNDED)
    table.add_column("Event Type", style="cyan")
    table.add_column("Count", style="white", justify="right")
    table.add_column("Percentage", style="green", justify="right")
    
    for event_type, count in stats["event_types"].items():
        percentage = (count / stats["total_events"]) * 100
        
        # Event type names
        type_names = {
            "created": "Created",
            "deleted": "Deleted", 
            "modified": "Modified",
            "moved": "Moved",
            "attribute": "Attribute Changed",
            "opened": "Opened",
            "closed": "Closed"
        }
        
        type_name = type_names.get(event_type, event_type)
        table.add_row(type_name, f"{count:,}", f"{percentage:.1f}%")
    
    console.print(table)
    
    # Daily statistics (last 7 days)
    if stats["daily_stats"]:
        daily_table = Table(title="📅 Daily Statistics (Last 7 Days)", box=box.ROUNDED)
        daily_table.add_column("Date", style="cyan")
        daily_table.add_column("Event Count", style="white", justify="right")
        
        # Show only last 7 days data
        sorted_days = sorted(stats["daily_stats"].items(), reverse=True)[:7]
        for date, count in sorted_days:
            daily_table.add_row(date, f"{count:,}")
        
        console.print(daily_table)
    
    # File information
    info_table = Table(title="📁 File Information", box=box.ROUNDED)
    info_table.add_column("Item", style="cyan")
    info_table.add_column("Value", style="white")
    
    info_table.add_row("Total Events", f"{stats['total_events']:,}")
    info_table.add_row("File Size", format_file_size(stats["file_size"]))
    if stats["last_modified"]:
        info_table.add_row("Last Modified", stats["last_modified"].strftime("%Y-%m-%d %H:%M:%S"))
    
    console.print(info_table)

@logs.command()
@click.argument('query')
@click.option('--limit', '-l', default=50, help='Maximum number of results')
def search(query: str, limit: int):
    """Search in logs"""
    
    analyzer = LogAnalyzer()
    results = analyzer.search_logs(query, limit)
    
    if not results:
        console.print(f"[yellow]⚠ No search results for '{query}'.[/yellow]")
        return
    
    console.print(Panel(
        f"Search results for '{query}': {len(results)} found",
        title="🔍 Log Search",
        border_style="green"
    ))
    
    for i, line in enumerate(results, 1):
        # 검색어 하이라이트
        highlighted = line.replace(query, f"[bold red]{query}[/bold red]")
        console.print(f"{i:3d}: {highlighted}")

@logs.command()
def clean():
    """Clean log files"""
    
    if not os.path.exists(LOG_FILE):
        console.print("[yellow]⚠ No log files to clean.[/yellow]")
        return
    
    # 확인
    if not Confirm.ask("Do you want to clean log files? (backup then delete)"):
        return
    
    try:
        # 백업 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"monitor_{timestamp}.log"
        
        # 백업
        import shutil
        shutil.copy2(LOG_FILE, backup_name)
        
        # 원본 파일 비우기
        with open(LOG_FILE, 'w') as f:
            pass
        
        console.print(f"[green]✓ Logs cleaned.[/green]")
        console.print(f"[dim]Backup file: {backup_name}[/dim]")
        
    except Exception as e:
        console.print(f"[red]✗ Failed to clean logs: {e}[/red]")

@cli.group()
def config():
    """Configuration management commands"""
    pass

@config.command()
def show():
    """View current configuration"""
    
    config_manager = ConfigManager()
    current_config = config_manager.load_config()
    
    # 설정을 Syntax로 표시
    config_text = f"""# File Monitor Configuration

recursive = {str(current_config['recursive']).lower()}
"""
    
    if current_config['extensions']:
        config_text += "\n# File extensions to monitor\n"
        for ext in current_config['extensions']:
            config_text += f"extension = {ext}\n"
    else:
        config_text += "\n# Monitor all files (no extension filter)\n"
    
    syntax = Syntax(config_text, "ini", theme="monokai", line_numbers=True)
    console.print(Panel(syntax, title="⚙️ Current Configuration", border_style="blue"))

@config.command()
@click.option('--recursive/--no-recursive', default=True, help='Enable recursive directory monitoring')
@click.option('--extensions', '-e', multiple=True, help='File extensions to monitor (multiple allowed)')
def set(recursive: bool, extensions: tuple):
    """Change configuration"""
    
    config_manager = ConfigManager()
    
    new_config = {
        "recursive": recursive,
        "extensions": list(extensions) if extensions else []
    }
    
    # 설정 미리보기
    console.print(Panel(
        f"Recursive Mode: {'Yes' if recursive else 'No'}\n"
        f"Extension Filter: {', '.join(extensions) if extensions else 'None (All files)'}",
        title="🔧 New Configuration",
        border_style="yellow"
    ))
    
    if Confirm.ask("Do you want to save this configuration?"):
        config_manager.save_config(new_config)

@config.command()
@click.argument('preset', type=click.Choice(['dev', 'log', 'all', 'web']))
def preset(preset: str):
    """Apply preset configuration"""
    
    presets = {
        'dev': {
            'name': 'Developer',
            'recursive': True,
            'extensions': ['c', 'cpp', 'h', 'hpp', 'py', 'js', 'ts', 'java', 'go', 'rs', 'php', 'rb', 'swift', 'kt', 'html', 'css', 'json', 'xml', 'yaml', 'yml', 'md', 'txt']
        },
        'log': {
            'name': 'Log Files',
            'recursive': True,
            'extensions': ['log', 'err', 'out', 'trace', 'debug', 'info', 'warn', 'error', 'access']
        },
        'all': {
            'name': 'All Files',
            'recursive': True,
            'extensions': []
        },
        'web': {
            'name': 'Web Development',
            'recursive': True,
            'extensions': ['html', 'css', 'js', 'ts', 'jsx', 'tsx', 'vue', 'scss', 'less', 'json', 'xml']
        }
    }
    
    preset_config = presets[preset]
    
    console.print(Panel(
        f"Preset: {preset_config['name']}\n"
        f"Recursive Mode: {'Yes' if preset_config['recursive'] else 'No'}\n"
        f"Extensions: {', '.join(preset_config['extensions']) if preset_config['extensions'] else 'All files'}",
        title=f"📦 {preset_config['name']} Preset",
        border_style="green"
    ))
    
    if Confirm.ask("Do you want to apply this preset?"):
        config_manager = ConfigManager()
        config_manager.save_config({
            "recursive": preset_config['recursive'],
            "extensions": preset_config['extensions']
        })

@cli.command()
def build():
    """Build C program"""
    
    console.print(Panel("Building C program...", title="🔨 Build", border_style="blue"))
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Compiling...", total=None)
            
            result = subprocess.run(['gcc', '-o', 'monitor', 'main.c', '-ljson-c', '-lpthread'], 
                                  capture_output=True, text=True)
            
            progress.remove_task(task)
        
        if result.returncode == 0:
            console.print("[green]✓ Build successful![/green]")
            console.print("[dim]Executable: monitor[/dim]")
        else:
            console.print("[red]✗ Build failed.[/red]")
            if result.stderr:
                console.print(f"[red]Error: {result.stderr}[/red]")
                
    except FileNotFoundError:
        console.print("[red]✗ GCC is not installed.[/red]")
    except Exception as e:
        console.print(f"[red]✗ Build failed: {e}[/red]")

@cli.command()
def dashboard():
    """Real-time dashboard"""
    
    def create_dashboard():
        """대시보드 레이아웃 생성"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        layout["left"].split_column(
            Layout(name="status"),
            Layout(name="config")
        )
        
        layout["right"].split_column(
            Layout(name="stats"),
            Layout(name="recent")
        )
        
        return layout
    
    def update_dashboard(layout):
        """대시보드 내용 업데이트"""
        
        # 헤더
        layout["header"].update(Panel(
            "[bold cyan]File Monitor Dashboard[/bold cyan] - Real-time Monitoring",
            title="📊 Dashboard",
            border_style="bright_blue"
        ))
        
        # 상태
        status_content = ""
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                status_content = f"[green]🟢 Running[/green]\nPID: {pid}"
            except ProcessLookupError:
                status_content = "[red]🔴 Stopped[/red]"
        else:
            status_content = "[red]🔴 Stopped[/red]"
        
        layout["status"].update(Panel(status_content, title="Status", border_style="green"))
        
        # 설정
        config_manager = ConfigManager()
        config_data = config_manager.load_config()
        config_content = f"Recursive: {'Yes' if config_data['recursive'] else 'No'}\n"
        if config_data['extensions']:
            config_content += f"Extensions: {len(config_data['extensions'])} items"
        else:
            config_content += "Filter: None"
        
        layout["config"].update(Panel(config_content, title="Configuration", border_style="blue"))
        
        # 통계
        analyzer = LogAnalyzer()
        stats = analyzer.get_stats()
        
        stats_content = f"Total Events: {stats['total_events']:,}\n"
        if stats['file_size'] > 0:
            stats_content += f"Log Size: {format_file_size(stats['file_size'])}"
        
        layout["stats"].update(Panel(stats_content, title="Statistics", border_style="yellow"))
        
        # 최근 로그
        recent_content = ""
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                recent_lines = lines[-5:] if len(lines) > 5 else lines
                for line in recent_lines:
                    line = line.strip()
                    if line:
                        # 시간 부분만 표시
                        if line.startswith('['):
                            time_part = line[1:20]  # [YYYY-MM-DD HH:MM:SS]
                            event_part = line[21:] if len(line) > 21 else ""
                            recent_content += f"{time_part}\n{event_part[:40]}...\n\n"
            except:
                recent_content = "Failed to read logs"
        else:
            recent_content = "No log file"
        
        layout["recent"].update(Panel(recent_content, title="Recent Logs", border_style="magenta"))
        
        # 푸터
        layout["footer"].update(Panel(
            "[dim]Q: Quit | R: Refresh | S: Status | L: Logs[/dim]",
            border_style="bright_black"
        ))
    
    # 대시보드 실행
    layout = create_dashboard()
    
    console.print("[bold]Starting real-time dashboard (Press Q to quit)[/bold]")
    
    try:
        with Live(layout, console=console, refresh_per_second=1) as live:
            while True:
                update_dashboard(layout)
                time.sleep(1)
                
                # 키보드 입력 확인 (간단한 구현)
                # 실제로는 더 복잡한 키보드 입력 처리가 필요
                
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠ Dashboard has been terminated.[/yellow]")

if __name__ == '__main__':
    cli()
