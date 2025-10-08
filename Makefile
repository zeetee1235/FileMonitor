# Makefile for Advanced File Monitor

CC = gcc
CFLAGS = -Wall -Wextra -g -O2 -pthread
LIBS = -ljson-c -lssl -lcrypto -lz -lpcre

# Directories
SRC_DIR = src
BUILD_DIR = build
INSTALL_DIR = /usr/local/bin

# Targets
MAIN_TARGET = $(BUILD_DIR)/main
ADVANCED_TARGET = $(BUILD_DIR)/advanced_monitor
ENHANCED_TARGET = $(BUILD_DIR)/enhanced_monitor

# Source files
MAIN_SRC = $(SRC_DIR)/main.c
ADVANCED_SRC = $(SRC_DIR)/advanced_monitor.c
ENHANCED_SRC = $(SRC_DIR)/enhanced_monitor.c

# Default target
all: $(MAIN_TARGET) $(ADVANCED_TARGET) $(ENHANCED_TARGET)

# Create build directory
$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

# Build main monitor
$(MAIN_TARGET): $(MAIN_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -o $@ $< -ljson-c

# Build advanced monitor
$(ADVANCED_TARGET): $(ADVANCED_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -o $@ $< $(LIBS)

# Build enhanced monitor  
$(ENHANCED_TARGET): $(ENHANCED_SRC) | $(BUILD_DIR)
	$(CC) $(CFLAGS) -o $@ $< $(LIBS)

# Install targets
install: $(MAIN_TARGET) $(ADVANCED_TARGET) $(ENHANCED_TARGET)
	sudo cp $(MAIN_TARGET) $(INSTALL_DIR)/file_monitor
	sudo cp $(ADVANCED_TARGET) $(INSTALL_DIR)/advanced_monitor
	sudo cp $(ENHANCED_TARGET) $(INSTALL_DIR)/enhanced_monitor
	sudo chmod +x $(INSTALL_DIR)/file_monitor
	sudo chmod +x $(INSTALL_DIR)/advanced_monitor
	sudo chmod +x $(INSTALL_DIR)/enhanced_monitor

# Clean build files
clean:
	rm -rf $(BUILD_DIR)

# Check dependencies
check-deps:
	@echo "Checking required dependencies..."
	@pkg-config --exists json-c || (echo "Missing: libjson-c-dev" && exit 1)
	@pkg-config --exists openssl || (echo "Missing: libssl-dev" && exit 1)
	@pkg-config --exists zlib || (echo "Missing: zlib1g-dev" && exit 1)
	@pkg-config --exists libpcre || (echo "Missing: libpcre3-dev" && exit 1)
	@echo "All dependencies found!"

# Development targets
dev: check-deps all

# Test targets
test: all
	@echo "Running basic tests..."
	@./$(MAIN_TARGET) --version 2>/dev/null || echo "Main monitor test failed"
	@./$(ADVANCED_TARGET) --version 2>/dev/null || echo "Advanced monitor test failed"

.PHONY: all install clean check-deps dev test
