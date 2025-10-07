# 🚀 Quick Start Guide

Get File Monitor up and running in under 2 minutes!

## ⚡ One-Command Setup

The fastest way to get started:

```bash
git clone https://github.com/your-username/FileMonitor.git
cd FileMonitor
chmod +x setup_and_run.sh
./setup_and_run.sh
```

The script will:
- ✅ Install all system dependencies
- ✅ Build the C monitoring program  
- ✅ Install Python packages
- ✅ Create configuration files
- ✅ Set up test environment
- ✅ Launch interactive menu

## 🎮 Using the Interactive Menu

After running the setup script, you'll see a colorful menu:

```
🎮 Interactive Mode (Arrow keys + Enter)
🚀 Start Background Monitoring  
📊 Check Current Status
📄 View Recent Logs
📺 Real-time Dashboard
⚙️ View Configuration
🧪 Create Test Files and Test Monitoring
❌ Exit
```

**Navigation:**
- Use ↑/↓ arrow keys to navigate
- Press Enter to select
- Perfect for beginners!

## 🖥️ Command Line Usage

For power users who prefer the command line:

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
python3 src/fmon.py logs show -n 10

# Real-time log watching
python3 src/fmon.py logs tail
```

### Stop Monitoring
```bash
python3 src/fmon.py stop
```

## ⚙️ Basic Configuration

### Quick Setup for Web Development
```bash
python3 src/fmon.py config preset web
```
This monitors: html, css, js, ts, jsx, tsx, vue, scss, less, json, xml

### Quick Setup for All Files
```bash
python3 src/fmon.py config preset all
```

### Custom Extensions
Edit `monitor.conf`:
```ini
recursive=true
extension=py
extension=js
extension=html
```

## 🧪 Test Your Setup

1. **Start monitoring a test directory:**
   ```bash
   python3 src/fmon.py start test_dir --background
   ```

2. **Create some test files:**
   ```bash
   echo "console.log('test');" > test_dir/test.js
   echo "<h1>Hello</h1>" > test_dir/test.html
   ```

3. **Check the logs:**
   ```bash
   python3 src/fmon.py logs show -n 5
   ```

You should see output like:
```
[2025-10-08 10:30:15] Created: /path/to/test_dir/test.js
[2025-10-08 10:30:15] Modified: /path/to/test_dir/test.js
[2025-10-08 10:30:16] Created: /path/to/test_dir/test.html
```

## 🎯 Common Use Cases

### Monitor Your Code Project
```bash
cd /your/project/directory
python3 /path/to/FileMonitor/src/fmon.py start . --background
```

### Web Development Monitoring
```bash
python3 src/fmon.py config preset web
python3 src/fmon.py start ./src --background
python3 src/fmon.py dashboard  # Watch changes live!
```

### Log File Monitoring
```bash
python3 src/fmon.py config preset log
python3 src/fmon.py start /var/log --background
```

## 🔍 Real-time Dashboard

For the coolest experience, try the live dashboard:

```bash
python3 src/fmon.py dashboard
```

This shows:
- 📊 Real-time statistics
- 📈 Event counts
- 📝 Recent activity
- 💾 Memory usage
- ⚙️ Current configuration

Press `Q` to quit the dashboard.

## 🆘 Troubleshooting

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
chmod +x run_interactive.sh
```

### "Python module not found"
```bash
pip3 install --user -r requirements.txt
```

### "Monitor not starting"
1. Check if already running: `python3 src/fmon.py status`
2. Stop existing: `python3 src/fmon.py stop`
3. Try again: `python3 src/fmon.py start test_dir --background`

## 🎉 You're Ready!

Now you can:
- ✅ Monitor any directory for file changes
- ✅ Use the beautiful interactive interface
- ✅ Analyze logs and statistics
- ✅ Configure monitoring for your needs
- ✅ Run monitoring in the background

**Next Steps:**
- Read the main [README.md](../README.md) for advanced features
- Explore configuration presets
- Try the real-time dashboard
- Set up monitoring for your development projects

Happy monitoring! 🚀
