# Enhanced Features Guide

This guide covers the advanced features added to File Monitor: Enhanced Monitor, Parent Directory Monitoring, and Project Root Detection.

## Enhanced Monitor

The Enhanced Monitor is a new C-based monitoring system that provides unlimited directory watching capacity and real-time statistics.

### Key Features

- **Dynamic Watch Management**: No hard limits on watched directories
- **Auto-scaling Memory**: Watch capacity expands automatically based on needs
- **Real-time Statistics**: JSON-based metrics with detailed monitoring info
- **Thread-safe Operations**: Concurrent statistics updates and log writing
- **Automatic Log Rotation**: Prevents log files from growing too large

### Usage

```bash
# Start enhanced monitoring
python3 src/fmon.py start /path/to/directory --enhanced --background

# View real-time statistics
python3 src/fmon.py perf

# View enhanced logs
python3 src/fmon.py logs show --enhanced
python3 src/fmon.py logs tail --enhanced

# Check status (shows enhanced monitor info)
python3 src/fmon.py status
```

### Statistics Output

```
=== ENHANCED MONITOR STATISTICS ===
               Enhanced Monitor Performance                
                                                           
  Metric                 Value      Details                
 ───────────────────────────────────────────────────────── 
  Total Events           1,234      events processed       
  Active Watches         567        directories monitored  
  Watch Capacity         1,024      max directories        
  Memory Usage           12,345     KB                     
  Watch Limit Hits       2          expansion triggers     
  Memory Reallocations   1          dynamic expansions     
  Most Active Path       /src/...   89 events              
  Uptime                 02:15:43   h:m:s                  
```

### When to Use Enhanced Monitor

- **Large Projects**: Projects with hundreds or thousands of directories
- **Deep Directory Trees**: Complex nested directory structures
- **Performance Monitoring**: When you need real-time statistics
- **Production Monitoring**: Long-running monitoring with detailed metrics

## Parent Directory Monitoring

Monitor parent directories without changing your current working directory.

### Basic Parent Monitoring

```bash
# Monitor 1 level up (default)
python3 src/fmon.py start . --parent --background

# Monitor specific levels up
python3 src/fmon.py start . --parent --levels 2 --background
python3 src/fmon.py start . --parent --levels 3 --background
```

### Use Cases

1. **Subdirectory Development**: Working in `/project/src/components` but want to monitor entire `/project`
2. **Module Development**: Working in `/app/modules/auth` but want to monitor `/app`
3. **Deep Project Navigation**: Working deep in project but want project-wide monitoring

### Examples

```bash
# Working in nested directory
cd /my/project/src/frontend/components
python3 /path/to/FileMonitor/src/fmon.py start . --parent --levels 3 --background
# Now monitoring: /my/project

# Working in source directory
cd /app/src
python3 /path/to/FileMonitor/src/fmon.py start . --parent --background
# Now monitoring: /app
```

## Project Root Detection

Automatically detect and monitor project root directories based on common project markers.

### Detected Project Types

The system automatically detects:

- **Git Repositories**: `.git` directory
- **Python Projects**: `requirements.txt`, `setup.py`, `pyproject.toml`
- **Node.js Projects**: `package.json`, `node_modules`
- **Rust Projects**: `Cargo.toml`
- **Go Projects**: `go.mod`
- **Java Projects**: `pom.xml`, `build.gradle`
- **C/C++ Projects**: `CMakeLists.txt`, `Makefile`
- **Ruby Projects**: `Gemfile`
- **PHP Projects**: `composer.json`

### Usage

```bash
# Auto-detect project root
python3 src/fmon.py start . --project-root --background

# Combine with enhanced monitoring
python3 src/fmon.py start . --project-root --enhanced --background
```

### How It Works

1. **Start from current directory**
2. **Search upward** for project markers
3. **Stop at first match** or filesystem root
4. **Monitor detected project root**

### Examples

```bash
# Working anywhere in a Git project
cd /my/git/project/deep/nested/directory
python3 /path/to/FileMonitor/src/fmon.py start . --project-root --background
# Automatically finds and monitors /my/git/project (has .git directory)

# Working in Python project subdirectory
cd /python/app/src/models
python3 /path/to/FileMonitor/src/fmon.py start . --project-root --background
# Automatically finds and monitors /python/app (has requirements.txt)
```

## Combining Features

You can combine all features for powerful monitoring:

```bash
# Enhanced monitoring with project root detection
python3 src/fmon.py start . --project-root --enhanced --background

# Parent monitoring with enhanced features
python3 src/fmon.py start . --parent --levels 2 --enhanced --background

# Full-featured monitoring
python3 src/fmon.py start /path --project-root --enhanced --recursive --background
```

## Monitor Type Comparison

| Feature | Basic Monitor | Advanced Monitor | Enhanced Monitor |
|---------|---------------|------------------|------------------|
| Directory Watching | Limited (1024) | Limited (1024) | Unlimited |
| Checksums | No | Yes | No |
| Real-time Stats | No | Basic | Comprehensive |
| Memory Usage | Low | Medium | Dynamic |
| Log Rotation | No | No | Yes |
| Performance | Good | Good | Excellent |
| Best For | Small projects | Security-focused | Large projects |

## Performance Guidelines

### Small Projects (< 100 directories)
```bash
python3 src/fmon.py start . --background
```

### Medium Projects (100-500 directories)
```bash
python3 src/fmon.py start . --advanced --background
```

### Large Projects (> 500 directories)
```bash
python3 src/fmon.py start . --enhanced --background
```

### Very Large Projects (> 1000 directories)
```bash
python3 src/fmon.py start . --enhanced --project-root --background
```

## Troubleshooting

### Enhanced Monitor Not Starting
```bash
# Check if enhanced monitor is built
ls -la enhanced_monitor

# Rebuild if necessary
python3 src/fmon.py build -t enhanced_monitor

# Check dependencies
ldd enhanced_monitor
```

### Project Root Not Detected
```bash
# Manually check for project markers
ls -la  # Look for .git, package.json, etc.
find . -maxdepth 3 -name ".git" -o -name "package.json" -o -name "requirements.txt"

# Use parent monitoring instead
python3 src/fmon.py start . --parent --levels 3 --background
```

### Performance Issues
```bash
# Check statistics
python3 src/fmon.py perf

# If memory usage is high, check watch count
# Consider using file extension filtering
python3 src/fmon.py config set extensions py,js,txt
```

## Advanced Configuration

### Enhanced Monitor Settings

The enhanced monitor creates these files:
- `enhanced_stats.json`: Real-time statistics
- `enhanced_monitor.log`: Detailed logs with rotation

### Log Level Filtering

Enhanced monitor logs are color-coded:
- **ERROR**: Red (system errors, critical issues)
- **INFO**: Green (normal operations, events)
- **DEBUG**: Dim (detailed debugging info)

### Statistics JSON Format

```json
{
  "total_events": 1234,
  "active_watches": 567,
  "watch_capacity": 1024,
  "memory_usage_kb": 12345,
  "watch_limit_hits": 2,
  "memory_reallocations": 1,
  "most_active_path": "/src/components",
  "max_events_per_path": 89,
  "uptime_seconds": 8143
}
```

This file is updated every few seconds and can be read by external tools for monitoring integration.
