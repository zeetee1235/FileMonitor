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
```

### Check What's Happening
```bash
# Quick status check
python3 src/fmon.py status

# See recent activity
python3 src/fmon.py logs show

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

2. **Create some test files:**
   ```bash
   echo "console.log('test');" > test_monitoring/test.js
   echo "print('hello')" > test_monitoring/test.py
   ```

3. **Check the logs:**
   ```bash
   python3 src/fmon.py logs show
   ```

You should see output like:
```
[2025-10-08 10:30:15] Created: /path/to/test_monitoring/test.js
[2025-10-08 10:30:15] Modified: /path/to/test_monitoring/test.js
[2025-10-08 10:30:16] Created: /path/to/test_monitoring/test.py
```

## Common Use Cases

### Monitor Your Code Project
```bash
cd /your/project/directory
python3 /path/to/FileMonitor/src/fmon.py start . --background
```

### Python Development Monitoring
```bash
python3 src/fmon.py config set extensions py,txt
python3 src/fmon.py start ./src --background
```

### Web Development Monitoring
```bash
python3 src/fmon.py config set extensions html,css,js,ts
python3 src/fmon.py start ./src --background
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
- Use the simple interactive interface
- View logs and status information
- Configure monitoring for your needs
- Run monitoring in the background

**Next Steps:**
- Read the main [README.md](../README.md) for advanced features
- Try different configuration settings
- Set up monitoring for your development projects

Happy monitoring!
