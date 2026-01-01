# Migration Guide: Version 1.x to 2.0

This guide helps you migrate from the old three-binary architecture to the new unified monitor.

## What Changed?

### Major Changes

1. **Three binaries merged into one**: `main`, `advanced_monitor`, and `enhanced_monitor` are now a single `monitor` binary
2. **New `--mode` flag**: Instead of using different binaries, use `--mode=basic|advanced|enhanced`
3. **Simplified CLI**: Removed `--advanced` and `--enhanced` flags in favor of `--mode`
4. **Reorganized structure**: Scripts moved to `scripts/`, tests to `tests/`, config to `config/`

### File Structure Changes

**Before:**
```
FileMonitor/
├── build/
│   ├── main
│   ├── advanced_monitor
│   └── enhanced_monitor
├── src/
│   ├── main.c
│   ├── advanced_monitor.c
│   └── enhanced_monitor.c
├── test.sh
├── setup_and_run.sh
├── run_interactive.sh
└── monitor.conf
```

**After:**
```
FileMonitor/
├── build/
│   └── monitor              # Single unified binary
├── src/
│   └── monitor.c            # Single unified source
├── tests/
│   └── test.sh
├── scripts/
│   ├── setup.sh
│   └── run_interactive.sh
├── config/
│   └── monitor.conf.example
└── logs/                    # Runtime logs directory
```

## Migration Steps

### 1. Update Your Scripts

#### Old Way:
```bash
# Start basic monitoring
./build/main /path/to/dir

# Start advanced monitoring
./build/advanced_monitor /path/to/dir

# Start enhanced monitoring
./build/enhanced_monitor /path/to/dir
```

#### New Way:
```bash
# Start basic monitoring
./build/monitor --mode=basic /path/to/dir

# Start advanced monitoring
./build/monitor --mode=advanced /path/to/dir

# Start enhanced monitoring
./build/monitor --mode=enhanced /path/to/dir
```

### 2. Update Python CLI Commands

#### Old Way:
```bash
# Start with basic monitoring
python3 src/fmon.py start /path/to/dir

# Start with advanced features
python3 src/fmon.py start /path/to/dir --advanced

# Start with enhanced features
python3 src/fmon.py start /path/to/dir --enhanced
```

#### New Way:
```bash
# Start with basic monitoring (default)
python3 src/fmon.py start /path/to/dir --mode=basic

# Start with advanced features
python3 src/fmon.py start /path/to/dir --mode=advanced

# Start with enhanced features
python3 src/fmon.py start /path/to/dir --mode=enhanced
```

### 3. Update Build Commands

#### Old Way:
```bash
make all                    # Build all three binaries
make build/main            # Build basic monitor
make build/advanced_monitor # Build advanced monitor
make build/enhanced_monitor # Build enhanced monitor
```

#### New Way:
```bash
make all    # Build unified monitor
make        # Same as above (default target)
```

### 4. Update Configuration Files

Configuration file location has changed:
- **Old**: `monitor.conf` in project root
- **New**: `config/monitor.conf.example` (copy and rename to `config/monitor.conf`)

The config file format remains the same:
```ini
recursive=true
extension=c
extension=h
extension=py
extension=js
```

### 5. Update Log File References

Log files are now unified:
- **Old**: `monitor.log`, `advanced_monitor.log`, `enhanced_monitor.log`
- **New**: `monitor.log` (all modes write to same file)

Stats files are also unified:
- **Old**: `monitor_stats.json`, `enhanced_stats.json`
- **New**: `monitor_stats.json` (includes mode information)

## Breaking Changes

### Command Line

| Old Command | New Command |
|------------|-------------|
| `fmon start --enhanced` | `fmon start --mode=enhanced` |
| `fmon start --advanced` | `fmon start --mode=advanced` |
| `fmon logs --enhanced` | `fmon logs show` |
| `fmon build -t advanced` | `fmon build` |

### Direct Binary Execution

| Old Binary | New Command |
|-----------|-------------|
| `./build/main <dir>` | `./build/monitor --mode=basic <dir>` |
| `./build/advanced_monitor <dir>` | `./build/monitor --mode=advanced <dir>` |
| `./build/enhanced_monitor <dir>` | `./build/monitor --mode=enhanced <dir>` |

### Status Output

The `fmon status` command now shows:
- Single "Monitor" status (not separate Basic/Enhanced/Advanced)
- Current mode (basic/advanced/enhanced)
- Mode-specific statistics

## Feature Equivalence

All features from the three separate monitors are preserved:

### Basic Mode (formerly `main`)
- Simple file monitoring
- Recursive directory watching
- Extension filtering
- Basic logging

### Advanced Mode (formerly `advanced_monitor`)
- All basic features
- **SHA256 checksums** for file integrity
- **Log rotation** and compression
- Performance statistics
- Resource monitoring

### Enhanced Mode (formerly `enhanced_monitor`)
- All basic features
- **Dynamic watch management** (no hard limits)
- Automatic memory reallocation
- Enhanced statistics
- Most active path tracking
- Memory optimization

## Testing Your Migration

After updating your code, test each mode:

```bash
# Clean and rebuild
make clean && make all

# Test basic mode
./build/monitor --mode=basic /tmp &
kill %1

# Test advanced mode
./build/monitor --mode=advanced /tmp &
kill %1

# Test enhanced mode
./build/monitor --mode=enhanced /tmp &
kill %1

# Test Python CLI
python3 src/fmon.py build
python3 src/fmon.py start /tmp --mode=basic --background
python3 src/fmon.py status
python3 src/fmon.py stop
```

## Rollback Plan

If you need to rollback to the old version:

```bash
git checkout v1.x  # Replace with your old version tag
make clean
make all
```

## Getting Help

If you encounter issues during migration:

1. Check the updated README.md for new examples
2. Run `fmon --help` or `./build/monitor --help` for usage
3. Open an issue on GitHub with:
   - Your old command/script
   - Error messages
   - What you've tried

## Benefits of Migration

- **60% less C code** to maintain (one file vs. three)
- **Simpler build process** (one target instead of three)
- **Consistent CLI** interface
- **Single point of debugging**
- **Better resource usage** (no duplicate code in memory)
- **Easier to understand** for new contributors

## Timeline

- **Recommended**: Migrate immediately to benefit from improvements
- **Support**: Old three-binary structure is no longer maintained
- **Compatibility**: No backward compatibility layer (clean break)
