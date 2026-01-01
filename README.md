# File Monitor

Real-time file system monitoring tool with a unified architecture and three monitoring modes.

![File Monitor Screenshot](docs/screenshot.png)

## Quick Start

### One-Command Setup & Run

```bash
git clone https://github.com/your-username/FileMonitor.git
cd FileMonitor
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This script will:
- Install all dependencies (GCC, Python packages)
- Build the unified monitoring program
- Create configuration files
- Set up test environment
- Launch interactive menu

### Manual Installation

1. **Install dependencies:**
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install gcc libjson-c-dev libssl-dev zlib1g-dev python3-pip
   
   # Fedora/RHEL
   sudo dnf install gcc json-c-devel openssl-devel zlib-devel python3-pip
   
   # Arch Linux
   sudo pacman -S gcc json-c openssl zlib python-pip
   ```

2. **Install Python packages:**
   ```bash
   pip3 install --user -r requirements.txt
   ```

3. **Build the monitor:**
   ```bash
   make all
   # or
   python3 src/fmon.py build
   ```

## Usage

### Interactive Mode (Recommended)
```bash
./scripts/run_interactive.sh
# or
python3 src/interactive_menu.py
```

Use arrow keys to navigate through options:
- Start/stop monitoring
- View logs and status
- Configure settings
- Test monitoring

### Command Line Interface

**Start monitoring with different modes:**
```bash
# Basic mode (simple file monitoring)
python3 src/fmon.py start . --mode=basic --background

# Advanced mode (with checksums and log rotation)
python3 src/fmon.py start . --mode=advanced --background

# Enhanced mode (with dynamic scaling, no watch limits)
python3 src/fmon.py start . --mode=enhanced --background
```

**Monitor parent directory (project root):**
```bash
python3 src/fmon.py start . --parent --background
```

**Auto-detect and monitor project root:**
```bash
python3 src/fmon.py start . --project-root --background
```

**Check status:**
```bash
python3 src/fmon.py status
```

**View recent logs:**
```bash
python3 src/fmon.py logs show
```

**Real-time log monitoring:**
```bash
python3 src/fmon.py logs tail
```

**Stop monitoring:**
```bash
python3 src/fmon.py stop
```

### Direct Binary Usage

```bash
# Basic monitoring
./build/monitor --mode=basic /path/to/dir

# Advanced monitoring
./build/monitor --mode=advanced /path/to/dir

# Enhanced monitoring
./build/monitor --mode=enhanced /path/to/dir
```

### Configuration

Copy and edit the example configuration:
```bash
cp config/monitor.conf.example config/monitor.conf
```

Edit `config/monitor.conf` to customize monitoring:

```ini
# Enable recursive directory monitoring
recursive=true

# Monitor specific file extensions
extension=js
extension=html
extension=css
extension=py
extension=json
```

**Configuration commands:**
```bash
# Set extensions
python3 src/fmon.py config set extensions txt,py,js

# Set recursive mode
python3 src/fmon.py config set recursive true

# Show current config
python3 src/fmon.py config show
```

## Monitor Modes

FileMonitor provides a single unified binary with three operational modes:

### Basic Mode
Simple, lightweight file monitoring:
- File event tracking (create, modify, delete, move)
- Recursive directory monitoring
- Extension-based filtering
- Basic logging

### Advanced Mode
All basic features plus:
- **SHA256 checksums** for file integrity verification
- **Log rotation** and compression (gzip)
- Performance statistics and metrics
- Resource monitoring (CPU, memory, disk)

### Enhanced Mode
All basic features plus:
- **Dynamic watch management** with no hard limits
- Automatic memory reallocation as needed
- Enhanced statistics tracking
- Most active path identification
- Intelligent resource optimization

## Features

### Real-time Monitoring
- **File events**: Create, modify, delete, move, attribute changes
- **Directory monitoring**: Recursive or single-level
- **Performance**: Low CPU usage with inotify
- **Filtering**: Extension-based filtering for focused monitoring

### Parent Directory & Project Detection
- **Parent directory monitoring**: Monitor 1-5 levels up from current directory
- **Project root detection**: Automatically detect `.git`, `package.json`, `requirements.txt`, etc.
- **Smart targeting**: Monitor entire project from any subdirectory

### Logging & Analysis
- **Comprehensive logs**: All events with timestamps
- **Statistics**: Real-time metrics in JSON format
- **Log viewing**: Show recent entries or real-time monitoring
- **Color-coded logs**: Error, info, and debug level highlighting

## Project Structure

```
FileMonitor/
├── src/                       # Source code
│   ├── monitor.c             # Unified C monitoring program
│   ├── fmon.py               # Python CLI interface
│   └── interactive_menu.py   # Interactive TUI menu
├── config/                    # Configuration files
│   └── monitor.conf.example  # Example configuration
├── scripts/                   # Utility scripts
│   ├── setup.sh             # Setup script
│   └── run_interactive.sh   # Interactive menu launcher
├── tests/                     # Test files
│   └── test.sh              # Test suite
├── docs/                      # Documentation
├── build/                     # Built executables (gitignored)
│   └── monitor               # Unified monitor binary
├── logs/                      # Runtime logs (gitignored)
├── Makefile                   # Build system
├── requirements.txt           # Python dependencies
├── MIGRATION.md              # Migration guide from v1.x
└── README.md                 # This file
```

## Development

### Building from Source
```bash
# Clone repository
git clone https://github.com/your-username/FileMonitor.git
cd FileMonitor

# Check dependencies
make check-deps

# Build
make all

# Install Python dependencies
pip3 install --user -r requirements.txt
```

### Testing
```bash
# Run test suite
make test

# Or run tests manually
cd tests && bash test.sh

# Test each mode
./build/monitor --mode=basic /tmp &
./build/monitor --mode=advanced /tmp &
./build/monitor --mode=enhanced /tmp &
```

## Requirements

- **OS**: Linux (uses inotify)
- **Compiler**: GCC
- **Libraries**: json-c, pthread, openssl, zlib
- **Python**: 3.6+
- **Python packages**: rich, click, inquirer, psutil

## Migration from v1.x

If you're upgrading from the old three-binary architecture, see [MIGRATION.md](MIGRATION.md) for detailed migration instructions.

**Key changes:**
- Three binaries (`main`, `advanced_monitor`, `enhanced_monitor`) merged into one
- Use `--mode` flag instead of separate binaries
- Simplified CLI: `--advanced` and `--enhanced` flags replaced with `--mode=advanced|enhanced`

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for terminal output
- Uses [Click](https://github.com/pallets/click) for CLI framework
- Interactive menus powered by [Inquirer](https://github.com/magmax/python-inquirer)

---

<details>
<summary>Monitoring</summary>
<br>
<p align="center">
  <img src="docs/MUAH.webp" alt="Monitoring" width="200">
  <br>
  <em>mwah!</em>
  <br>
</p>
</details>

