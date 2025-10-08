# File Monitor

Real-time file system monitoring tool with simple terminal interface and comprehensive logging capabilities.

![File Monitor Screenshot](docs/screenshot.png)

## Features

- **Real-time monitoring** - Track file changes instantly using Linux inotify
- **Simple CLI** - Clean terminal interface with plain text output
- **Interactive mode** - Navigate with arrow keys and intuitive menus
- **Comprehensive logging** - Detailed event tracking with timestamps
- **Flexible filtering** - Monitor specific file extensions or all files
- **Multiple interfaces** - Command-line, interactive, and basic status display
- **Background operation** - Run monitoring in the background
- **Easy setup** - Simple installation and configuration

## Quick Start

### One-Command Setup & Run

```bash
git clone https://github.com/your-username/FileMonitor.git
cd FileMonitor
chmod +x setup_and_run.sh
./setup_and_run.sh
```

This script will:
- Install all dependencies (GCC, Python packages)
- Build the C monitoring program
- Create configuration files
- Set up test environment
- Launch interactive menu

### Manual Installation

1. **Install dependencies:**
   ```bash
   # Ubuntu/Debian
   sudo apt update && sudo apt install gcc libjson-c-dev python3-pip
   
   # Fedora/RHEL
   sudo dnf install gcc json-c-devel python3-pip
   
   # Arch Linux
   sudo pacman -S gcc json-c python-pip
   ```

2. **Install Python packages:**
   ```bash
   pip3 install --user -r requirements.txt
   ```

3. **Build the monitor:**
   ```bash
   python3 src/fmon.py build -t all
   ```

## Usage

### Interactive Mode (Recommended)
```bash
python3 src/interactive_menu.py
# or
python3 src/fmon.py --interactive
```

Use arrow keys to navigate through options:
- Start/stop monitoring
- View logs and status
- Configure settings
- Test monitoring

### Command Line Interface

**Start monitoring:**
```bash
python3 src/fmon.py start /path/to/directory --background
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

### Configuration

Edit `monitor.conf` to customize monitoring:

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

## Features in Detail

### Real-time Monitoring
- **File events**: Create, modify, delete, move, attribute changes
- **Directory monitoring**: Recursive or single-level
- **Performance**: Low CPU usage with inotify
- **Filtering**: Extension-based filtering for focused monitoring

### Logging & Analysis
- **Comprehensive logs**: All events with timestamps
- **Log viewing**: Show recent entries or real-time monitoring
- **Simple output**: Plain text logs for easy reading

### User Interface
- **Simple CLI**: Clean terminal output
- **Interactive menus**: Arrow key navigation
- **Status display**: Current monitoring information

## Advanced Usage

### Background Monitoring
```bash
# Start background monitoring
python3 src/fmon.py start /home/user/projects --background

# Check if running
python3 src/fmon.py status

# View logs while running
python3 src/fmon.py logs tail
```

### Log Viewing
```bash
# Show recent logs
python3 src/fmon.py logs show

# Real-time log monitoring
python3 src/fmon.py logs tail
```

### Custom Configuration
```bash
# Set custom extensions
python3 src/fmon.py config set extensions js,ts,jsx,tsx
python3 src/fmon.py config set recursive true

# View current config
python3 src/fmon.py config show
```

## Project Structure

```
FileMonitor/
├── src/                    # Source code
│   ├── main.c             # C monitoring program (basic)
│   ├── advanced_monitor.c # C monitoring program (advanced)
│   ├── fmon.py            # Python CLI interface
│   └── interactive_menu.py # Interactive menu system
├── docs/                   # Documentation
│   └── QUICK_START.md     # Quick start guide
├── build/                 # Built executables
├── setup_and_run.sh      # Setup script
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## Development

### Building from Source
```bash
# Clone repository
git clone https://github.com/your-username/FileMonitor.git
cd FileMonitor

# Build C programs
python3 src/fmon.py build -t all

# Install Python dependencies
pip3 install --user -r requirements.txt
```

### Testing
```bash
# Test basic monitoring
python3 src/fmon.py start test_monitoring --background
echo "test content" > test_monitoring/test.txt
python3 src/fmon.py logs show
python3 src/fmon.py stop
```

## Requirements

- **OS**: Linux (uses inotify)
- **Compiler**: GCC
- **Libraries**: json-c, pthread, openssl, zlib, pcre
- **Python**: 3.6+
- **Python packages**: rich, click, inquirer, psutil

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for terminal output
- Uses [Click](https://github.com/pallets/click) for CLI framework
- Interactive menus powered by [Inquirer](https://github.com/magmax/python-inquirer)

---

<details>
<summary>Click here</summary>
<br>
<p align="center">
  <img src="docs/osage_chan_plush.jpg" alt="Osage-chan" width="200">
  <br>
  <em>으헤~~</em>
  <br>
</p>
</details>

