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

def detect_project_root(start_path: str = '.') -> str:
    """프로젝트 루트 디렉토리 자동 감지
    
    다음 파일들 중 하나를 찾으면 프로젝트 루트로 판단:
    - .git/ (Git 저장소)
    - package.json (Node.js)
    - requirements.txt (Python)
    - Cargo.toml (Rust)
    - pom.xml (Maven)
    - build.gradle (Gradle)
    - Makefile
    - README.md (상위에 다른 표시가 없을 때)
    """
    current_path = os.path.abspath(start_path)
    project_indicators = [
        '.git',
        'package.json',
        'requirements.txt', 
        'Cargo.toml',
        'pom.xml',
        'build.gradle',
        'Makefile',
        'pyproject.toml',
        'setup.py',
        '.gitignore'
    ]
    
    # 최대 10단계까지만 올라가기
    for _ in range(10):
        # 프로젝트 표시 파일들 확인
        for indicator in project_indicators:
            if os.path.exists(os.path.join(current_path, indicator)):
                return current_path
                
        # 루트 디렉토리에 도달했으면 중단
        parent_path = os.path.dirname(current_path)
        if parent_path == current_path:  # 루트 디렉토리
            break
            
        current_path = parent_path
    
    # 프로젝트 루트를 찾지 못한 경우 시작 경로 반환
    return os.path.abspath(start_path)

def get_target_directory(path: str, parent: bool, project_root: bool, levels: int) -> str:
    """모니터링할 대상 디렉토리 결정"""
    
    if project_root:
        # 프로젝트 루트 자동 감지
        return detect_project_root(path)
    elif parent:
        # 상위 디렉토리로 이동
        current_path = os.path.abspath(path)
        for _ in range(levels):
            parent_path = os.path.dirname(current_path)
            if parent_path == current_path:  # 루트에 도달
                break
            current_path = parent_path
        return current_path
    else:
        # 지정된 경로 사용
        return os.path.abspath(path)

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
            console.print(f"Failed to load configuration file: {e}")
            
        return config
    
    def save_config(self, config: dict):
        """설정 파일 저장"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                f.write("# File Monitor Configuration\n")
                f.write("# Comments start with '#'\n\n")
                
                f.write(f"# Recursive directory monitoring\n")
                f.write(f"recursive={'true' if config['recursive'] else 'false'}\n\n")
                
                if config.get('extensions'):
                    f.write("# File extensions to monitor\n")
                    for ext in config['extensions']:
                        f.write(f"extension={ext}\n")
                        
            console.print("SUCCESS: Configuration saved")
        except Exception as e:
            console.print(f"ERROR: Failed to save configuration: {e}")

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
            console.print(f"Log analysis failed: {e}")
            
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
            console.print(f"Log search failed: {e}")
            
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
    
    Simple file system monitoring tool.
    """
    if interactive:
        # 인터랙티브 모드 실행
        try:
            import subprocess
            subprocess.run([sys.executable, 'src/interactive_menu.py'])
        except FileNotFoundError:
            console.print("ERROR: src/interactive_menu.py not found")
        except KeyboardInterrupt:
            console.print("\nExiting...")
        ctx.exit()
    elif ctx.invoked_subcommand is None:
        # 명령어 없이 실행되면 help 표시
        console.print(ctx.get_help())

@cli.command()
@click.argument('path', default='.')
@click.option('--background', '-b', is_flag=True, help='Run in background')
@click.option('--config', '-c', default=CONFIG_FILE, help='Configuration file path')
@click.option('--advanced', '-a', is_flag=True, help='Use advanced monitoring features')
@click.option('--enhanced', '-e', is_flag=True, help='Use enhanced monitoring (dynamic watch management)')
@click.option('--parent', '-p', is_flag=True, help='Monitor parent directory')
@click.option('--project-root', '-r', is_flag=True, help='Auto-detect and monitor project root')
@click.option('--levels', '-l', type=int, default=1, help='Number of parent levels to go up (with --parent)')
def start(path: str, background: bool, config: str, advanced: bool, enhanced: bool, parent: bool, project_root: bool, levels: int):
    """Start file monitoring
    
    Examples:
      fmon start                     # Monitor current directory
      fmon start /path/to/dir        # Monitor specific directory  
      fmon start --parent            # Monitor parent directory
      fmon start --parent -l 2       # Monitor 2 levels up
      fmon start --project-root      # Auto-detect project root
      fmon start --enhanced          # Use enhanced monitor (no watch limits)
      fmon start --enhanced --advanced # Combined enhanced + advanced features
    """
    
    # 대상 디렉토리 결정
    target_path = get_target_directory(path, parent, project_root, levels)
    
    # 경로 검증
    if not os.path.exists(target_path):
        console.print(f"ERROR: Target path not found: {target_path}")
        sys.exit(1)
    
    # 경로 정보 표시
    if project_root:
        console.print(f"Project root detected: {target_path}")
        if target_path != os.path.abspath(path):
            console.print(f"  (from: {os.path.abspath(path)})")
    elif parent:
        console.print(f"Monitoring parent directory ({levels} level{'s' if levels > 1 else ''} up): {target_path}")
        console.print(f"  (from: {os.path.abspath(path)})")
    
    # 절대 경로로 변환
    abs_path = target_path
    
    # 이미 실행 중인지 확인
    ipc = MonitorIPC()
    if ipc.is_monitor_running():
        console.print("WARNING: Monitor is already running")
        if not Confirm.ask("Stop existing monitor and start new one?"):
            return
        else:
            # 기존 모니터 중지
            stop_monitor()
    
    # 설정 로드
    config_manager = ConfigManager(config)
    monitor_config = config_manager.load_config()
    
    # 실행할 프로그램 선택 (스크립트 위치 기준 절대 경로)
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    if enhanced:
        monitor_executable = os.path.join(script_dir, 'build', 'enhanced_monitor')
        monitor_name = 'Enhanced Monitor'
    elif advanced:
        monitor_executable = os.path.join(script_dir, 'build', 'advanced_monitor')
        monitor_name = 'Advanced Monitor'
    else:
        monitor_executable = os.path.join(script_dir, 'build', 'main')
        monitor_name = 'Standard Monitor'
    
    # 실행 파일 존재 확인
    if not os.path.exists(monitor_executable):
        console.print(f"ERROR: {monitor_executable} not found")
        console.print("Build first: make all")
        sys.exit(1)
    
    # 시작 정보 표시
    console.print(f"Starting {monitor_name}")
    console.print(f"Directory: {abs_path}")
    console.print(f"Recursive: {'Yes' if monitor_config['recursive'] else 'No'}")
    console.print(f"Mode: {'Background' if background else 'Foreground'}")
    
    if enhanced:
        console.print("Features: Dynamic Watch Management, Auto-scaling, Enhanced Stats")
    elif advanced:
        console.print("Features: Checksum, Log Rotation, Performance Stats")
    
    if monitor_config['extensions']:
        ext_text = ", ".join(monitor_config['extensions'][:10])
        if len(monitor_config['extensions']) > 10:
            ext_text += f" and {len(monitor_config['extensions']) - 10} more"
        console.print(f"Extensions: {ext_text}")
    else:
        console.print("Filter: All files")
    
    # C 프로그램 실행
    try:
        if background:
            # 백그라운드에서 실행
            cmd = [monitor_executable, abs_path]
            if advanced and os.path.exists(config):
                cmd.extend(['--config', config])
                
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # PID 파일에 저장
            with open(PID_FILE, 'w') as f:
                f.write(str(process.pid))
            
            console.print(f"SUCCESS: {monitor_name} started in background (PID: {process.pid})")
            console.print("Commands:")
            console.print("  fmon logs --tail    # View logs")
            console.print("  fmon status         # Check status")
            console.print("  fmon stop           # Stop monitor")
        else:
            # 포그라운드에서 실행
            console.print("Press Ctrl+C to stop monitoring")
            
            cmd = [monitor_executable, abs_path]
            if advanced and os.path.exists(config):
                cmd.extend(['--config', config])
                
            process = subprocess.Popen(cmd)
            
            try:
                process.wait()
            except KeyboardInterrupt:
                console.print("\nInterrupted by user")
                process.terminate()
                process.wait()
                
    except FileNotFoundError:
        console.print(f"ERROR: {monitor_executable} not found")
        console.print("Build first: make all")
        sys.exit(1)
    except Exception as e:
        console.print(f"ERROR: Failed to start monitor: {e}")
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
            
            console.print("SUCCESS: Monitor stopped")
            return True
            
        except (FileNotFoundError, ProcessLookupError):
            console.print("WARNING: PID file exists but process is not running")
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
            return False
        except Exception as e:
            console.print(f"ERROR: Failed to stop monitor: {e}")
            return False
    else:
        console.print("WARNING: No running monitor found")
        return False

@cli.command()
def stop():
    """Stop file monitoring"""
    console.print("Stopping monitor...")
    stop_monitor()

@cli.command()
def status():
    """Check monitor status (supports all monitor types)"""
    
    # 테이블 생성 (터미널 크기에 맞게 조정)
    table = Table(title="File Monitor Status", box=box.SIMPLE, width=80)
    table.add_column("Item", style="cyan", no_wrap=True, width=20)
    table.add_column("Value", style="white", width=50)
    
    # Enhanced Monitor 상태 확인
    enhanced_stats_file = "enhanced_stats.json"
    enhanced_log_file = "enhanced_monitor.log"
    enhanced_running = False
    
    if os.path.exists(enhanced_stats_file):
        try:
            with open(enhanced_stats_file, 'r') as f:
                enhanced_stats = json.load(f)
            
            # Enhanced monitor는 통계 파일로 실행 상태 확인
            if enhanced_stats.get('uptime_seconds', 0) > 0:
                enhanced_running = True
                table.add_row("Enhanced Monitor", "[green]Running[/green]")
                table.add_row("Active Watches", f"{enhanced_stats.get('active_watches', 0):,}")
                table.add_row("Total Events", f"{enhanced_stats.get('total_events', 0):,}")
                table.add_row("Memory Usage", f"{enhanced_stats.get('memory_usage_kb', 0):,} KB")
                
                uptime = enhanced_stats.get('uptime_seconds', 0)
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                seconds = uptime % 60
                table.add_row("Enhanced Uptime", f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        except:
            table.add_row("Enhanced Monitor", "Stopped")
    else:
        table.add_row("Enhanced Monitor", "Stopped")
    
    # 기본 모니터 실행 상태 확인
    basic_running = False
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            
            # 프로세스 존재 확인
            try:
                os.kill(pid, 0)
                basic_running = True
                table.add_row("Basic Monitor", "[green]Running[/green]")
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
                table.add_row("Basic Monitor", "Stopped (PID file exists but no process)")
                os.remove(PID_FILE)
                
        except Exception as e:
            table.add_row("Basic Monitor", f"Error: {e}")
    else:
        table.add_row("Basic Monitor", "Stopped")
    
    # 전체 상태 요약
    if enhanced_running or basic_running:
        table.add_row("Overall Status", "[green]Monitoring Active[/green]")
    else:
        table.add_row("Overall Status", "[red]All Monitors Stopped[/red]")
    
    # Enhanced Monitor 로그 파일 정보
    if os.path.exists(enhanced_log_file):
        stat = os.stat(enhanced_log_file)
        table.add_row("Enhanced Log", enhanced_log_file)
        table.add_row("Enhanced Log Size", format_file_size(stat.st_size))
        table.add_row("Enhanced Log Modified", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
    
    # 기본 로그 파일 정보
    if os.path.exists(LOG_FILE):
        stat = os.stat(LOG_FILE)
        table.add_row("Basic Log", LOG_FILE)
        table.add_row("Basic Log Size", format_file_size(stat.st_size))
        table.add_row("Basic Log Modified", datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
        
        # 라인 수 계산
        try:
            with open(LOG_FILE, 'r') as f:
                line_count = sum(1 for _ in f)
            table.add_row("Basic Log Lines", f"{line_count:,}")
        except:
            pass
    
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
        table.add_row("Config File", "None")
    
    console.print(table)

@cli.group()
def logs():
    """Log management commands"""
    pass

@logs.command()
@click.option('--lines', '-n', default=20, help='Number of lines to display')
@click.option('--enhanced', is_flag=True, help='Show enhanced monitor logs')
def show(lines: int, enhanced: bool):
    """View recent logs (supports all monitor types)"""
    
    # Enhanced Monitor 로그 파일 확인
    enhanced_log_file = "enhanced_monitor.log"
    basic_log_file = LOG_FILE
    
    if enhanced:
        log_file = enhanced_log_file
        log_type = "Enhanced Monitor"
    else:
        log_file = basic_log_file
        log_type = "Basic Monitor"
    
    if not os.path.exists(log_file):
        if enhanced:
            console.print("WARNING: Enhanced monitor log file not found")
            console.print("Start enhanced monitor first: fmon start --enhanced")
        else:
            console.print("WARNING: Log file not found")
            console.print("Start monitor first: fmon start")
        return
    
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            all_lines = f.readlines()
        
        recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
        
        console.print(f"Recent {len(recent_lines)} lines from {log_type} log:")
        console.print("=" * 60)
        
        for line in recent_lines:
            line = line.strip()
            if line:
                # Enhanced monitor 로그 색상 지정
                if enhanced and ('ERROR' in line or 'WARN' in line):
                    console.print(f"[red]{line}[/red]")
                elif enhanced and ('INFO' in line):
                    console.print(f"[green]{line}[/green]")
                elif enhanced and ('DEBUG' in line):
                    console.print(f"[dim]{line}[/dim]")
                else:
                    console.print(line)
                    
    except Exception as e:
        console.print(f"ERROR: Failed to read log: {e}")

@logs.command()
@click.option('--enhanced', is_flag=True, help='Tail enhanced monitor logs')
def tail(enhanced: bool):
    """Real-time log viewing (supports all monitor types)"""
    
    # Enhanced Monitor 로그 파일 확인
    enhanced_log_file = "enhanced_monitor.log"
    basic_log_file = LOG_FILE
    
    if enhanced:
        log_file = enhanced_log_file
        log_type = "Enhanced Monitor"
    else:
        log_file = basic_log_file
        log_type = "Basic Monitor"
    
    if not os.path.exists(log_file):
        if enhanced:
            console.print("WARNING: Enhanced monitor log file not found")
            console.print("Start enhanced monitor first: fmon start --enhanced")
        else:
            console.print("WARNING: Log file not found")
            console.print("Start monitor first: fmon start")
        return
    
    console.print(f"Real-time {log_type} log monitoring (Press Ctrl+C to exit)")
    console.print("=" * 60)
    
    try:
        # tail -f implementation
        with open(log_file, 'r', encoding='utf-8') as f:
            # Move to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    line = line.strip()
                    # Enhanced monitor 로그 색상 지정
                    if enhanced and ('ERROR' in line or 'WARN' in line):
                        console.print(f"[red]{line}[/red]")
                    elif enhanced and ('INFO' in line):
                        console.print(f"[green]{line}[/green]")
                    elif enhanced and ('DEBUG' in line):
                        console.print(f"[dim]{line}[/dim]")
                    else:
                        console.print(line)
                else:
                    time.sleep(0.1)
                    
    except KeyboardInterrupt:
        console.print(f"\nReal-time {log_type} log monitoring stopped")
    except Exception as e:
        console.print(f"ERROR: Log monitoring failed: {e}")

@logs.command()
def stats():
    """View log statistics"""
    
    analyzer = LogAnalyzer()
    stats = analyzer.get_stats()
    
    if stats["total_events"] == 0:
        console.print("WARNING: No log data available")
        return
    
    # Statistics table
    table = Table(title="Log Statistics", box=box.SIMPLE, width=80)
    table.add_column("Event Type", style="cyan", width=30)
    table.add_column("Count", style="white", justify="right", width=15)
    table.add_column("Percentage", style="green", justify="right", width=15)
    
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
    
    # File information
    console.print(f"\nTotal Events: {stats['total_events']:,}")
    console.print(f"File Size: {format_file_size(stats['file_size'])}")
    if stats["last_modified"]:
        console.print(f"Last Modified: {stats['last_modified'].strftime('%Y-%m-%d %H:%M:%S')}")

@logs.command()
@click.argument('query')
@click.option('--limit', '-l', default=50, help='Maximum number of results')
def search(query: str, limit: int):
    """Search in logs"""
    
    analyzer = LogAnalyzer()
    results = analyzer.search_logs(query, limit)
    
    if not results:
        console.print(f"WARNING: No search results for '{query}'")
        return
    
    console.print(f"Search results for '{query}': {len(results)} found")
    console.print("=" * 50)
    
    for i, line in enumerate(results, 1):
        console.print(f"{i:3d}: {line}")

@logs.command()
def clean():
    """Clean log files"""
    
    if not os.path.exists(LOG_FILE):
        console.print("WARNING: No log files to clean")
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
        
        console.print("SUCCESS: Logs cleaned")
        console.print(f"Backup file: {backup_name}")
        
    except Exception as e:
        console.print(f"ERROR: Failed to clean logs: {e}")

@cli.group()
def config():
    """Configuration management commands"""
    pass

@config.command()
def show():
    """View current configuration"""
    
    config_manager = ConfigManager()
    current_config = config_manager.load_config()
    
    # 설정을 간단한 텍스트로 표시
    console.print("Current Configuration:")
    console.print("=" * 30)
    console.print(f"Recursive: {str(current_config['recursive']).lower()}")
    
    if current_config['extensions']:
        console.print("Extensions:")
        for ext in current_config['extensions']:
            console.print(f"  - {ext}")
    else:
        console.print("Filter: All files (no extension filter)")

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
    console.print("New Configuration:")
    console.print("=" * 20)
    console.print(f"Recursive Mode: {'Yes' if recursive else 'No'}")
    console.print(f"Extension Filter: {', '.join(extensions) if extensions else 'None (All files)'}")
    
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
@click.option('--target', '-t', type=click.Choice(['main', 'advanced', 'all']), default='all', help='Build target')
def build(target: str):
    """Build C program"""
    
    console.print(f"Building {target} target...")
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            if target == 'all':
                task = progress.add_task("Building all targets...", total=None)
                result = subprocess.run(['make', 'all'], capture_output=True, text=True)
            elif target == 'main':
                task = progress.add_task("Building main monitor...", total=None)
                result = subprocess.run(['make', 'build/main'], capture_output=True, text=True)
            elif target == 'advanced':
                task = progress.add_task("Building advanced monitor...", total=None)
                result = subprocess.run(['make', 'build/advanced_monitor'], capture_output=True, text=True)
            
            progress.remove_task(task)
        
        if result.returncode == 0:
            console.print(f"SUCCESS: Build completed ({target})")
            
            # 빌드된 파일 목록 표시
            if target == 'all':
                console.print("Executables:")
                console.print("  - build/main (Standard monitor)")
                console.print("  - build/advanced_monitor (Advanced monitor)")
            elif target == 'main':
                console.print("Executable: build/main")
            elif target == 'advanced':
                console.print("Executable: build/advanced_monitor")
                
        else:
            console.print(f"ERROR: Build failed ({target})")
            if result.stderr:
                console.print(f"Error: {result.stderr}")
            if result.stdout:
                console.print(f"Output: {result.stdout}")
                
    except FileNotFoundError:
        console.print("ERROR: Make is not installed")
        console.print("Install build tools: sudo apt install build-essential")
    except Exception as e:
        console.print(f"ERROR: Build failed: {e}")

@cli.command()
def perf():
    """View performance statistics (supports all monitor types)"""
    
    # Enhanced Monitor 통계 파일 확인
    enhanced_stats_file = "enhanced_stats.json"
    advanced_stats_file = "performance_stats.json"
    
    enhanced_available = os.path.exists(enhanced_stats_file)
    advanced_available = os.path.exists(advanced_stats_file)
    
    if not enhanced_available and not advanced_available:
        console.print("WARNING: No performance statistics available")
        console.print("Start monitor first:")
        console.print("  fmon start --enhanced    # Enhanced statistics")
        console.print("  fmon start --advanced    # Advanced statistics")
        return
    
    # Enhanced Monitor 통계 표시
    if enhanced_available:
        try:
            with open(enhanced_stats_file, 'r') as f:
                enhanced_stats = json.load(f)
            
            console.print("\n=== ENHANCED MONITOR STATISTICS ===")
            
            # Enhanced statistics table
            enhanced_table = Table(title="Enhanced Monitor Performance", box=box.SIMPLE, width=80)
            enhanced_table.add_column("Metric", style="cyan", width=20)
            enhanced_table.add_column("Value", style="white", width=15)
            enhanced_table.add_column("Details", style="dim", width=30)
            
            # Core metrics
            enhanced_table.add_row("Total Events", f"{enhanced_stats.get('total_events', 0):,}", "events processed")
            enhanced_table.add_row("Active Watches", f"{enhanced_stats.get('active_watches', 0):,}", "directories monitored")
            enhanced_table.add_row("Watch Capacity", f"{enhanced_stats.get('watch_capacity', 0):,}", "max directories")
            enhanced_table.add_row("Memory Usage", f"{enhanced_stats.get('memory_usage_kb', 0):,}", "KB")
            enhanced_table.add_row("Watch Limit Hits", f"{enhanced_stats.get('watch_limit_hits', 0):,}", "expansion triggers")
            enhanced_table.add_row("Memory Reallocations", f"{enhanced_stats.get('memory_reallocations', 0):,}", "dynamic expansions")
            
            if enhanced_stats.get('most_active_path') and enhanced_stats.get('most_active_path') != 'none':
                enhanced_table.add_row("Most Active Path", enhanced_stats['most_active_path'][:50] + "...", 
                                     f"{enhanced_stats.get('max_events_per_path', 0)} events")
            
            if 'uptime_seconds' in enhanced_stats:
                uptime = enhanced_stats['uptime_seconds']
                hours = uptime // 3600
                minutes = (uptime % 3600) // 60
                seconds = uptime % 60
                enhanced_table.add_row("Uptime", f"{hours:02d}:{minutes:02d}:{seconds:02d}", "h:m:s")
            
            console.print(enhanced_table)
            
        except json.JSONDecodeError:
            console.print("ERROR: Invalid enhanced statistics file")
        except Exception as e:
            console.print(f"ERROR: Failed to read enhanced statistics: {e}")
    
    # Advanced Monitor 통계 표시 (기존 코드)
    if advanced_available:
        try:
            with open(advanced_stats_file, 'r') as f:
                stats = json.load(f)
            
            console.print("\n=== ADVANCED MONITOR STATISTICS ===")
            
            # Performance table
            perf_table = Table(title="Advanced Monitor Performance", box=box.SIMPLE, width=80)
            perf_table.add_column("Metric", style="cyan", width=25)
            perf_table.add_column("Value", style="white", width=20)
            perf_table.add_column("Unit", style="dim", width=15)
            perf_table.add_column("Unit", style="dim")
            
            # CPU and Memory stats
            if 'cpu_usage' in stats:
                perf_table.add_row("CPU Usage", f"{stats['cpu_usage']:.1f}", "%")
            if 'memory_usage' in stats:
                perf_table.add_row("Memory Usage", f"{stats['memory_usage']:.1f}", "MB")
            if 'memory_peak' in stats:
                perf_table.add_row("Peak Memory", f"{stats['memory_peak']:.1f}", "MB")
            
            # File operation stats
            if 'files_processed' in stats:
                perf_table.add_row("Files Processed", f"{stats['files_processed']:,}", "files")
            if 'events_per_second' in stats:
                perf_table.add_row("Events/Second", f"{stats['events_per_second']:.2f}", "ops/s")
            if 'checksums_computed' in stats:
                perf_table.add_row("Checksums Computed", f"{stats['checksums_computed']:,}", "files")
            
            # Timing stats
            if 'avg_processing_time' in stats:
                perf_table.add_row("Avg Processing Time", f"{stats['avg_processing_time']:.3f}", "ms")
            if 'uptime' in stats:
                hours = stats['uptime'] // 3600
                minutes = (stats['uptime'] % 3600) // 60
                seconds = stats['uptime'] % 60
                perf_table.add_row("Uptime", f"{hours:02d}:{minutes:02d}:{seconds:02d}", "h:m:s")
            
            console.print(perf_table)
            
            # Update time
            if 'last_updated' in stats:
                update_time = datetime.fromtimestamp(stats['last_updated']).strftime("%Y-%m-%d %H:%M:%S")
                console.print(f"\nLast updated: {update_time}")
            
        except json.JSONDecodeError:
            console.print("ERROR: Invalid performance statistics file")
        except Exception as e:
            console.print(f"ERROR: Failed to read performance statistics: {e}")


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
            title="Dashboard",
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
