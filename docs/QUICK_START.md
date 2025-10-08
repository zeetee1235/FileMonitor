# Quick Start Guide


## One-Command Setup

The fastest way to get started:

```bash
git clone https://github.com/your-username/FileMonitor.git
cd FileMonitor
chmod +x setup_and_run.sh
./setup_and_run.sh
```

The script will:
- Install all system dependencies
- Build the C monitoring program  
- Install Python packages
- Create configuration files
- Set up test environment
- Launch interactive menu

## Using the Interactive Menu

After running the setup script, you'll see a simple menu:

```
File Monitor Interactive Menu
========================================
Status: Stopped

[?] Select action:: 
 > Start monitoring
   View status
   View logs
   Configuration
   Build program
   Performance stats
   Exit
```

**Navigation:**
- Use up/down arrow keys to navigate
- Press Enter to select
- Perfect for beginners!

## Command Line Usage

For users who prefer the command line:

### Start Monitoring
```bash
# Monitor current directory
python3 src/fmon.py start . --background

# Monitor specific directory
python3 src/fmon.py start /path/to/your/project --background

# Monitor parent directory (great for project monitoring)
python3 src/fmon.py start . --parent --background

# Auto-detect and monitor project root
python3 src/fmon.py start . --project-root --background

# Enhanced monitoring for large projects
python3 src/fmon.py start . --enhanced --background
```

### Check What's Happening
```bash
# Quick status check (shows all monitor types)
python3 src/fmon.py status

# View performance statistics
python3 src/fmon.py perf

# See recent activity
python3 src/fmon.py logs show

# See enhanced monitor logs
python3 src/fmon.py logs show --enhanced

# Real-time log watching
python3 src/fmon.py logs tail
```

### Stop Monitoring
```bash
python3 src/fmon.py stop
```

## Basic Configuration

### Custom Extensions
Edit `monitor.conf`:
```ini
recursive=true
extension=py
extension=js
extension=html
```

### Configuration Commands
```bash
# Set extensions
python3 src/fmon.py config set extensions py,js,html

# Enable recursive monitoring
python3 src/fmon.py config set recursive true

# Show current settings
python3 src/fmon.py config show
```

## Test Your Setup

1. **Start monitoring a test directory:**
   ```bash
   python3 src/fmon.py start test_monitoring --background
   ```

2. **Or test enhanced monitoring:**
   ```bash
   python3 src/fmon.py start test_monitoring --enhanced --background
   ```

3. **Create some test files:**
   ```bash
   echo "console.log('test');" > test_monitoring/test.js
   echo "print('hello')" > test_monitoring/test.py
   ```

4. **Check the logs:**
   ```bash
   python3 src/fmon.py logs show
   # For enhanced monitor:
   python3 src/fmon.py logs show --enhanced
   ```

5. **View performance statistics:**
   ```bash
   python3 src/fmon.py perf
   ```

You should see output like:
```
[2025-10-08 10:30:15] Created: /path/to/test_monitoring/test.js
[2025-10-08 10:30:15] Modified: /path/to/test_monitoring/test.js
[2025-10-08 10:30:16] Created: /path/to/test_monitoring/test.py
```

## New Features Overview

### Enhanced Monitor
The Enhanced Monitor provides unlimited directory watching capacity and real-time statistics:

```bash
# Start enhanced monitoring
python3 src/fmon.py start . --enhanced --background

# View real-time statistics
python3 src/fmon.py perf

# Example output:
# Total Events: 1,234 events processed
# Active Watches: 567 directories monitored
# Memory Usage: 12,345 KB
# Watch Limit Hits: 0 expansion triggers
```

### Parent Directory Monitoring
Monitor your entire project from any subdirectory:

```bash
# Monitor parent directory
python3 src/fmon.py start . --parent --background

# Monitor specific levels up
python3 src/fmon.py start . --parent --levels 3 --background

# Auto-detect project root (.git, package.json, etc.)
python3 src/fmon.py start . --project-root --background
```

### Monitor Type Comparison
- **Basic Monitor**: Simple file monitoring, good for small projects
- **Advanced Monitor**: Includes checksum verification, moderate projects
- **Enhanced Monitor**: Unlimited capacity, real-time stats, large projects

## Common Use Cases

### Monitor Your Code Project
```bash
cd /your/project/directory
python3 /path/to/FileMonitor/src/fmon.py start . --background
```

### Monitor Entire Project from Subdirectory
```bash
cd /your/project/src/components
python3 /path/to/FileMonitor/src/fmon.py start . --project-root --background
```

### Enhanced Monitoring for Large Projects
```bash
cd /your/large/project
python3 /path/to/FileMonitor/src/fmon.py start . --enhanced --project-root --background
```

### Python Development Monitoring
```bash
python3 src/fmon.py config set extensions py,txt
python3 src/fmon.py start ./src --parent --background
```

### Web Development Monitoring
```bash
python3 src/fmon.py config set extensions html,css,js,ts
python3 src/fmon.py start ./src --enhanced --background
```

### Monitor Parent Directories
```bash
# Monitor 2 levels up from current directory
python3 src/fmon.py start . --parent --levels 2 --background

# Auto-detect project root and monitor
python3 src/fmon.py start . --project-root --background
```

## Troubleshooting

### "gcc not found"
```bash
# Ubuntu/Debian
sudo apt install gcc

# Fedora
sudo dnf install gcc

# Arch Linux
sudo pacman -S gcc
```

### "Permission denied"
```bash
chmod +x setup_and_run.sh
```

### "Python module not found"
```bash
pip3 install --user -r requirements.txt
```

### "Monitor not starting"
1. Check if already running: `python3 src/fmon.py status`
2. Stop existing: `python3 src/fmon.py stop`
3. Try again: `python3 src/fmon.py start test_monitoring --background`

### "Build failed"
```bash
# Install missing dependencies
sudo dnf install json-c-devel openssl-devel zlib-devel pcre-devel

# Try building again
python3 src/fmon.py build -t all
```

## You're Ready!

Now you can:
- Monitor any directory for file changes
- Use enhanced monitoring for large projects with unlimited capacity
- Monitor parent directories and project roots automatically
- Use the simple interactive interface
- View real-time performance statistics
- View logs and status information for all monitor types
- Configure monitoring for your needs
- Run monitoring in the background

**Advanced Features:**
- **Project Root Detection**: Automatically finds `.git`, `package.json`, `requirements.txt`, etc.
- **Parent Directory Monitoring**: Monitor 1-5 levels up from current directory
- **Enhanced Statistics**: Real-time memory usage, event counts, watch statistics
- **Dynamic Scaling**: No limits on watched directories with enhanced monitor
- **Color-coded Logs**: Enhanced monitor logs with error/info/debug highlighting

**Real-world Examples:**
```bash
# Web developer working in /project/src/components
cd /project/src/components
python3 /path/to/FileMonitor/src/fmon.py start . --project-root --enhanced --background
# Monitors entire /project directory automatically

# Python developer with large codebase
cd /my/python/project
python3 /path/to/FileMonitor/src/fmon.py start . --enhanced --background
# Handles thousands of files without limits

# Quick monitoring of parent directory
cd /project/deep/nested/dir
python3 /path/to/FileMonitor/src/fmon.py start . --parent --levels 3 --background
# Monitors /project directory
```

**Next Steps:**
- Read the main [README.md](../README.md) for advanced features
- Check out [Enhanced Features Guide](ENHANCED_FEATURES.md) for detailed guide on new capabilities
- Try different configuration settings
- Set up monitoring for your development projects

Happy monitoring!
