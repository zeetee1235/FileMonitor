# Makefile for Unified File Monitor

CC = gcc
CFLAGS = -Wall -Wextra -g -O2 -pthread
LIBS = -ljson-c -lssl -lcrypto -lz

# Directories
SRC_DIR = src
BUILD_DIR = build
INSTALL_DIR = /usr/local/bin
TEST_DIR = tests
CONFIG_DIR = config

# Targets
TARGET = $(BUILD_DIR)/monitor

# Source files
SRC = $(SRC_DIR)/monitor.c

# Default target
all: $(TARGET)

# Create build directory
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Build unified monitor
$(TARGET): $(SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -o $@ $< $(LIBS)

# Install target
install: $(TARGET)
	sudo cp $(TARGET) $(INSTALL_DIR)/file_monitor
	sudo chmod +x $(INSTALL_DIR)/file_monitor
	@echo "Installed to $(INSTALL_DIR)/file_monitor"

# Uninstall target
uninstall:
	sudo rm -f $(INSTALL_DIR)/file_monitor
	@echo "Uninstalled file_monitor"

# Clean build files
clean:
	rm -rf $(BUILD_DIR)
	rm -f *.log *.json *.pid
	@echo "Cleaned build artifacts"

# Check dependencies
check-deps:
	@echo "Checking required dependencies..."
	@pkg-config --exists json-c || (echo "Missing: libjson-c-dev" && exit 1)
	@pkg-config --exists openssl || (echo "Missing: libssl-dev" && exit 1)
	@pkg-config --exists zlib || (echo "Missing: zlib1g-dev" && exit 1)
	@echo "All dependencies found!"

# Development target
dev: check-deps all

# Test target
test: all
	@echo "Running monitor tests..."
	@./$(TARGET) --version
	@./$(TARGET) --help
	@echo "Basic compilation tests passed!"
	@if [ -f $(TEST_DIR)/test.sh ]; then \
		echo "Running test suite..."; \
		cd $(TEST_DIR) && bash test.sh; \
	else \
		echo "Test suite not found at $(TEST_DIR)/test.sh"; \
	fi

# Help target
help:
	@echo "Unified File Monitor - Build System"
	@echo ""
	@echo "Available targets:"
	@echo "  make          - Build the unified monitor (default)"
	@echo "  make all      - Same as make"
	@echo "  make install  - Install to $(INSTALL_DIR)"
	@echo "  make uninstall - Remove from $(INSTALL_DIR)"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make check-deps - Verify all dependencies are installed"
	@echo "  make dev      - Check dependencies and build"
	@echo "  make test     - Run tests"
	@echo "  make help     - Show this help message"

.PHONY: all install uninstall clean check-deps dev test help
