# 🔍 File Monitor

real-time file system monitoring tool with terminal interface and comprehensive logging capabilities.

![File Monitor Screenshot](docs/screenshot.png)

## ✨ Features

- **Real-time monitoring** - Track file changes instantly using Linux inotify
- **Beautiful CLI** - Rich terminal interface with colors and modern design
- **Interactive mode** - Navigate with arrow keys and intuitive menus
- **Comprehensive logging** - Detailed event tracking with timestamps
- **Flexible filtering** - Monitor specific file extensions or all files
- **Multiple interfaces** - Command-line, interactive, and dashboard modes
- **Background operation** - Run monitoring in the background
- **Live dashboard** - Real-time statistics and log viewing
- **Easy setup** - One-script installation and configuration

## 🚀 Quick Start

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
   gcc -o monitor src/main.c -ljson-c -lpthread
   ```

## 📖 Usage

### Interactive Mode (Recommended)
```bash
./run_interactive.sh
# or
python3 src/fmon.py --interactive
```

Use arrow keys to navigate through options:
- Start/stop monitoring
- View logs and statistics  
- Configure settings
- Real-time dashboard
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
python3 src/fmon.py logs show -n 20
```

**Real-time log monitoring:**
```bash
python3 src/fmon.py logs tail
```

**Live dashboard:**
```bash
python3 src/fmon.py dashboard
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

**Configuration presets:**
```bash
# Web development
python3 src/fmon.py config preset web

# All files
python3 src/fmon.py config preset all

# Developer files
python3 src/fmon.py config preset dev

# Log files only
python3 src/fmon.py config preset log
```

## 📊 Features in Detail

### Real-time Monitoring
- **File events**: Create, modify, delete, move, attribute changes
- **Directory monitoring**: Recursive or single-level
- **Performance**: Low CPU usage with inotify
- **Filtering**: Extension-based filtering for focused monitoring

### Logging & Analysis
- **Comprehensive logs**: All events with timestamps
- **Log analysis**: Statistics, search, and filtering
- **Log management**: Rotation, cleanup, and backup
- **Export formats**: JSON-structured logs for integration

### User Interface
- **Rich CLI**: Beautiful terminal output with colors
- **Interactive menus**: Arrow key navigation
- **Live dashboard**: Real-time statistics display
- **Progress indicators**: Visual feedback for operations

## 🔧 Advanced Usage

### Background Monitoring
```bash
# Start background monitoring
python3 src/fmon.py start /home/user/projects --background

# Check if running
python3 src/fmon.py status

# View logs while running
python3 src/fmon.py logs tail
```

### Log Analysis
```bash
# Search logs
python3 src/fmon.py logs search "error"

# View statistics
python3 src/fmon.py logs stats

# Show last 100 entries
python3 src/fmon.py logs show -n 100
```

### Custom Configuration
```bash
# Set custom extensions
python3 src/fmon.py config set --extensions js,ts,jsx,tsx --recursive

# View current config
python3 src/fmon.py config show
```

## 📁 Project Structure

```
FileMonitor/
├── src/                    # Source code
│   ├── main.c             # C monitoring program
│   ├── fmon.py            # Python CLI interface
│   └── interactive_menu.py # Interactive menu system
├── docs/                   # Documentation
│   ├── QUICK_START.md     # Quick start guide
│   └── screenshot.png     # Demo screenshot
├── examples/              # Example configurations
│   └── monitor.conf       # Sample configuration
├── setup_and_run.sh      # One-script setup
├── run_interactive.sh    # Interactive mode launcher
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

## 🛠️ Development

### Building from Source
```bash
# Clone repository
git clone https://github.com/your-username/FileMonitor.git
cd FileMonitor

# Build C program
gcc -o monitor src/main.c -ljson-c -lpthread

# Install Python dependencies
pip3 install --user -r requirements.txt
```

### Testing
```bash
# Run setup script to test all components
./setup_and_run.sh

# Test specific features
python3 src/fmon.py start test_dir --background
echo "test content" > test_dir/test.txt
python3 src/fmon.py logs show -n 5
```

## 📋 Requirements

- **OS**: Linux (uses inotify)
- **Compiler**: GCC
- **Libraries**: json-c, pthread
- **Python**: 3.6+
- **Python packages**: rich, click, inquirer, psutil

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🌟 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Uses [Click](https://github.com/pallets/click) for CLI framework
- Interactive menus powered by [Inquirer](https://github.com/magmax/python-inquirer)

---

<p align="center">
  <strong> 으헤~~ </strong><br>
</p>


<details>
<summary>Click here</summary>
<br>
<p align="center">
  <img src="docs/osage_chan_plush.jpg" alt="Osage-chan says: Great job reading the documentation!" width="200">
  <br>
  <em>Listen to inabakumori's songs while coding</em>
  <br>
</p>
</details>

