#!/bin/bash

# 파일 모니터 통합 설정 및 실행 스크립트
# 이 스크립트 하나로 모든 설정부터 실행까지 자동으로 처리됩니다.

set -e  # 에러 발생시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 로고 출력
print_logo() {
    echo -e "${CYAN}"
    echo "=============================================================="
    echo "                                                              "
    echo "          File Monitor Auto Setup & Launcher                 "
    echo "                                                              "
    echo "         Complete setup and execution in one script!         "
    echo "                                                              "
    echo "=============================================================="
    echo -e "${NC}"
}

# 진행상황 출력
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${PURPLE}[INFO]${NC} $1"
}

# 시스템 의존성 확인 및 설치
check_and_install_dependencies() {
    print_step "Checking system dependencies..."
    
    # GCC 확인
    if ! command -v gcc &> /dev/null; then
        print_warning "GCC is not installed. Attempting to install..."
        
        # 운영체제별 패키지 매니저 감지
        if command -v dnf &> /dev/null; then
            sudo dnf install -y gcc json-c-devel
        elif command -v yum &> /dev/null; then
            sudo yum install -y gcc json-c-devel
        elif command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y gcc libjson-c-dev
        elif command -v pacman &> /dev/null; then
            sudo pacman -S gcc json-c
        else
            print_error "Unsupported package manager. Please install GCC manually."
            exit 1
        fi
    else
        print_success "GCC is already installed."
    fi
    
    # Python3 확인
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 is required. Please install Python3."
        exit 1
    else
        print_success "Python3 is installed."
    fi
    
    # pip 확인
    if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
        print_warning "pip is not installed. Attempting to install..."
        if command -v dnf &> /dev/null; then
            sudo dnf install -y python3-pip
        elif command -v yum &> /dev/null; then
            sudo yum install -y python3-pip
        elif command -v apt &> /dev/null; then
            sudo apt install -y python3-pip
        elif command -v pacman &> /dev/null; then
            sudo pacman -S python-pip
        fi
    else
        print_success "pip is installed."
    fi
}

# Python 패키지 설치
install_python_packages() {
    print_step "Installing Python packages..."
    
    # requirements.txt가 있는지 확인
    if [ -f "requirements.txt" ]; then
        print_info "Installing packages from requirements.txt..."
        python3 -m pip install --user -r requirements.txt
    else
        print_info "Installing required packages individually..."
        python3 -m pip install --user rich click inquirer psutil
    fi
    
    print_success "Python package installation completed!"
}

# C 프로그램 빌드
build_c_program() {
    print_step "Building C monitor programs..."
    
    # 고급 의존성 확인
    print_info "Checking for advanced monitoring dependencies..."
    
    # 필요한 라이브러리들 확인
    LIBS_TO_CHECK=("json-c" "openssl" "zlib" "pcre")
    MISSING_LIBS=()
    
    for lib in "${LIBS_TO_CHECK[@]}"; do
        case $lib in
            "json-c")
                if ! pkg-config --exists json-c 2>/dev/null; then
                    MISSING_LIBS+=("libjson-c-dev")
                fi
                ;;
            "openssl")
                if ! pkg-config --exists openssl 2>/dev/null; then
                    MISSING_LIBS+=("libssl-dev")
                fi
                ;;
            "zlib")
                if ! pkg-config --exists zlib 2>/dev/null; then
                    MISSING_LIBS+=("zlib1g-dev")
                fi
                ;;
            "pcre")
                if ! pkg-config --exists libpcre 2>/dev/null; then
                    MISSING_LIBS+=("libpcre3-dev")
                fi
                ;;
        esac
    done
    
    # 누락된 라이브러리 설치
    if [ ${#MISSING_LIBS[@]} -gt 0 ]; then
        print_warning "Missing libraries for advanced features: ${MISSING_LIBS[*]}"
        print_info "Attempting to install missing libraries..."
        
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y "${MISSING_LIBS[@]}"
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y json-c-devel openssl-devel zlib-devel pcre-devel
        elif command -v yum &> /dev/null; then
            sudo yum install -y json-c-devel openssl-devel zlib-devel pcre-devel
        elif command -v pacman &> /dev/null; then
            sudo pacman -S json-c openssl zlib pcre
        else
            print_warning "Unable to auto-install libraries. Only basic monitoring will be available."
        fi
    fi
    
    # Makefile이 있으면 사용, 없으면 직접 컴파일
    if [ -f "Makefile" ]; then
        print_info "Using Makefile for building..."
        if make all 2>/dev/null; then
            print_success "All monitor programs built successfully using Makefile!"
        else
            print_warning "Makefile build failed. Attempting manual build..."
            build_manually
        fi
    else
        print_info "No Makefile found. Building manually..."
        build_manually
    fi
}

# 수동 빌드 함수
build_manually() {
    # build 디렉토리 생성
    mkdir -p build
    
    # 기본 모니터 빌드
    if [ -f "src/main.c" ]; then
        print_info "Building basic monitor..."
        if gcc -o build/main src/main.c -ljson-c -lpthread 2>/dev/null; then
            print_success "Basic monitor build successful!"
        else
            print_warning "JSON-C library not found. Building without JSON support..."
            if gcc -o build/main src/main.c -lpthread; then
                print_success "Basic monitor built (without JSON support)!"
            else
                print_error "Failed to build basic monitor."
                exit 1
            fi
        fi
    fi
    
    # 고급 모니터 빌드 (라이브러리 사용 가능할 때만)
    if [ -f "src/advanced_monitor.c" ]; then
        print_info "Building advanced monitor..."
        if gcc -Wall -Wextra -g -O2 -pthread -o build/advanced_monitor src/advanced_monitor.c -ljson-c -lssl -lcrypto -lz -lpcre 2>/dev/null; then
            print_success "Advanced monitor build successful!"
        else
            print_warning "Advanced monitor dependencies not available."
        fi
    fi
    
    # Enhanced 모니터 빌드 (새 기능)
    if [ -f "src/enhanced_monitor.c" ]; then
        print_info "Building enhanced monitor..."
        if gcc -Wall -Wextra -g -O2 -pthread -o build/enhanced_monitor src/enhanced_monitor.c -ljson-c 2>/dev/null; then
            print_success "Enhanced monitor build successful!"
        else
            print_warning "Enhanced monitor build failed. JSON-C library required."
        fi
    fi
}

# 설정 파일 생성
create_config_files() {
    print_step "Checking and creating configuration files..."
    
    # monitor.conf 파일이 없으면 기본 설정 생성
    if [ ! -f "monitor.conf" ]; then
        print_info "Creating default configuration file..."
        if [ -f "examples/advanced_monitor.conf" ]; then
            cp examples/advanced_monitor.conf monitor.conf
            print_success "Advanced configuration file copied from examples/advanced_monitor.conf"
        elif [ -f "examples/monitor.conf" ]; then
            cp examples/monitor.conf monitor.conf
            print_success "Configuration file copied from examples/monitor.conf"
        else
            cat > monitor.conf << 'EOF'
# Advanced File Monitor Configuration

# Basic settings
recursive=true
max_file_size_mb=100

# File extensions to monitor
extension=txt
extension=log
extension=conf
extension=py
extension=c
extension=h
extension=js
extension=html
extension=css
extension=json
extension=xml

# Advanced features
enable_checksum=true
enable_compression=true

# Regex patterns for advanced filtering
# Exclude temporary files
pattern_exclude=.*\.(tmp|swp|bak)$
pattern_exclude=^\..*

# Include only source code files
pattern_include=.*\.(c|h|py|js|html|css)$

# Alert patterns for critical files
pattern_alert=.*\.conf$
pattern_alert=.*passwd.*
pattern_alert=.*\.key$
pattern_alert=.*\.pem$
EOF
            print_success "Advanced configuration file (monitor.conf) created successfully!"
        fi
    else
        print_success "Configuration file already exists."
    fi
    
    # requirements.txt 파일이 없으면 생성
    if [ ! -f "requirements.txt" ]; then
        print_info "Creating requirements.txt file..."
        cat > requirements.txt << 'EOF'
rich>=13.0.0
click>=8.0.0
inquirer>=3.0.0
psutil>=5.8.0
EOF
        print_success "requirements.txt created successfully!"
    fi
}

# 실행 권한 설정
set_permissions() {
    print_step "Setting execute permissions..."
    
    # 모든 스크립트 파일에 실행 권한 부여
    for script in *.sh *.py; do
        if [ -f "$script" ]; then
            chmod +x "$script"
        fi
    done
    
    print_success "Execute permissions set successfully!"
}

# 테스트 디렉토리 생성
create_test_directory() {
    print_step "Setting up test directory..."
    
    if [ ! -d "test_dir" ]; then
        mkdir -p test_dir
        print_success "Test directory (test_dir) created successfully!"
    else
        print_success "Test directory already exists."
    fi
    
    # 샘플 파일 생성
    if [ ! -f "test_dir/sample.js" ]; then
        echo "console.log('Hello File Monitor!');" > test_dir/sample.js
        print_info "Sample file created: test_dir/sample.js"
    fi
}

# 상태 확인
check_system_status() {
    print_step "Checking system status..."
    
    echo -e "${CYAN}+------------------------------------------+${NC}"
    echo -e "${CYAN}|               System Status             |${NC}"
    echo -e "${CYAN}+------------------------------------------+${NC}"
    
    # 파일 존재 확인
    if [ -f "build/main" ]; then
        echo -e "${CYAN}|${NC} Basic Monitor:  ${GREEN}Built${NC}                 |"
    else
        echo -e "${CYAN}|${NC} Basic Monitor:  ${RED}Missing${NC}              |"
    fi
    
    if [ -f "build/advanced_monitor" ]; then
        echo -e "${CYAN}|${NC} Advanced Monitor: ${GREEN}Built${NC}               |"
    else
        echo -e "${CYAN}|${NC} Advanced Monitor: ${YELLOW}Not Built${NC}           |"
    fi
    
    if [ -f "build/enhanced_monitor" ]; then
        echo -e "${CYAN}|${NC} Enhanced Monitor: ${GREEN}Built${NC}               |"
    else
        echo -e "${CYAN}|${NC} Enhanced Monitor: ${YELLOW}Not Built${NC}           |"
    fi
    
    if [ -f "src/fmon.py" ]; then
        echo -e "${CYAN}|${NC} Python CLI:     ${GREEN}Ready${NC}                |"
    else
        echo -e "${CYAN}|${NC} Python CLI:     ${RED}Missing${NC}              |"
    fi
    
    if [ -f "src/interactive_menu.py" ]; then
        echo -e "${CYAN}|${NC} Interactive Menu: ${GREEN}Ready${NC}              |"
    else
        echo -e "${CYAN}|${NC} Interactive Menu: ${RED}Missing${NC}            |"
    fi
    
    if [ -f "monitor.conf" ]; then
        echo -e "${CYAN}|${NC} Config File:    ${GREEN}Present${NC}              |"
    else
        echo -e "${CYAN}|${NC} Config File:    ${RED}Missing${NC}              |"
    fi
    
    # 모니터 실행 상태 확인
    if [ -f "monitor.pid" ]; then
        PID=$(cat monitor.pid)
        if kill -0 $PID 2>/dev/null; then
            echo -e "${CYAN}|${NC} Monitor Status: ${GREEN}Running (PID: $PID)${NC}     |"
        else
            echo -e "${CYAN}|${NC} Monitor Status: ${RED}Stopped${NC}              |"
            rm -f monitor.pid
        fi
    else
        echo -e "${CYAN}|${NC} Monitor Status: ${RED}Stopped${NC}              |"
    fi
    
    echo -e "${CYAN}+------------------------------------------+${NC}"
}

# 실행 옵션 메뉴
show_execution_menu() {
    echo ""
    print_step "Please select an execution option:"
    echo ""
    echo -e "${GREEN}1)${NC} Interactive Mode (Arrow keys + Enter)"
    echo -e "${GREEN}2)${NC} Start Basic Monitoring (Background)"
    echo -e "${GREEN}3)${NC} Start Advanced Monitoring (with checksums)"
    echo -e "${GREEN}4)${NC} Start Enhanced Monitoring (unlimited capacity)"
    echo -e "${GREEN}5)${NC} Parent Directory Monitoring"
    echo -e "${GREEN}6)${NC} Project Root Auto-detection"
    echo -e "${GREEN}7)${NC} Check Current Status (Real-time)"
    echo -e "${GREEN}8)${NC} View Recent Logs"
    echo -e "${GREEN}9)${NC} Performance Statistics (Real-time)"
    echo -e "${GREEN}10)${NC} View Configuration"
    echo -e "${GREEN}11)${NC} Create Test Files and Test Monitoring"
    echo -e "${GREEN}12)${NC} Exit"
    echo ""
    echo -n "Choice (1-12): "
    read choice
    
    case $choice in
        1)
            print_info "Starting interactive mode..."
            python3 src/interactive_menu.py
            ;;
        2)
            print_info "Starting basic background monitoring..."
            python3 src/fmon.py start . --background
            sleep 2
            python3 src/fmon.py status
            ;;
        3)
            print_info "Starting advanced background monitoring..."
            python3 src/fmon.py start . --background --advanced
            sleep 2
            python3 src/fmon.py status
            ;;
        4)
            print_info "Starting enhanced background monitoring..."
            python3 src/fmon.py start . --background --enhanced
            sleep 2
            python3 src/fmon.py status
            ;;
        5)
            print_info "Starting parent directory monitoring..."
            python3 src/fmon.py start . --parent --background
            sleep 2
            python3 src/fmon.py status
            ;;
        6)
            print_info "Starting project root monitoring..."
            python3 src/fmon.py start . --project-root --enhanced --background
            sleep 2
            python3 src/fmon.py status
            ;;
        7)
            print_info "Checking current status (real-time)..."
            python3 src/fmon.py status
            ;;
        8)
            print_info "Displaying recent logs..."
            python3 src/fmon.py logs show -n 10
            ;;
        9)
            print_info "Displaying performance statistics (real-time)..."
            python3 src/fmon.py perf
            ;;
        10)
            print_info "Displaying current configuration..."
            python3 src/fmon.py config show
            ;;
        11)
            print_info "Running test..."
            run_test_demo
            ;;
        12)
            print_info "Exiting script."
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please enter a number between 1-12."
            show_execution_menu
            ;;
    esac
}

# 테스트 데모 실행
run_test_demo() {
    print_step "Running enhanced file monitoring test..."
    
    # 모니터가 실행 중인지 확인
    if [ ! -f "monitor.pid" ] && [ ! -f "enhanced_stats.json" ]; then
        print_info "Starting enhanced monitoring for test..."
        python3 src/fmon.py start test_dir --enhanced --background
        sleep 2
    fi
    
    print_info "Performing file change test in test_dir..."
    
    # 테스트 파일들 생성
    echo "// Test file 1 - $(date)" > test_dir/test1.js
    sleep 1
    echo "<h1>Test HTML - $(date)</h1>" > test_dir/test.html
    sleep 1
    echo "body { color: red; } /* $(date) */" > test_dir/test.css
    sleep 1
    echo "print('Python test - $(date)')" > test_dir/test.py
    sleep 1
    
    # 중첩 디렉토리 테스트
    mkdir -p test_dir/nested/deep
    echo "console.log('Deep test - $(date)');" > test_dir/nested/deep/deep.js
    sleep 1
    
    print_success "Test files have been created!"
    print_info "Checking recent logs..."
    sleep 2
    
    # Enhanced monitor 로그가 있으면 우선 표시
    if [ -f "enhanced_monitor.log" ]; then
        print_info "Enhanced monitor logs:"
        python3 src/fmon.py logs show --enhanced -n 8
    else
        print_info "Basic monitor logs:"
        python3 src/fmon.py logs show -n 8
    fi
    
    print_info "Performance statistics:"
    python3 src/fmon.py perf
    
    print_success "Test completed. Enhanced monitoring demonstrates:"
    echo "  - Real-time file change detection"
    echo "  - Dynamic watch management"
    echo "  - Performance statistics"
    echo "  - No watch limits"
}

# 메인 실행 함수
main() {
    print_logo
    
    echo -e "${YELLOW}Starting automatic setup...${NC}"
    echo ""
    
    # 1단계: 의존성 확인 및 설치
    check_and_install_dependencies
    
    # 2단계: Python 패키지 설치
    install_python_packages
    
    # 3단계: 설정 파일 생성
    create_config_files
    
    # 4단계: C 프로그램 빌드
    build_c_program
    
    # 5단계: 권한 설정
    set_permissions
    
    # 6단계: 테스트 디렉토리 생성
    create_test_directory
    
    echo ""
    print_success "All setup completed successfully!"
    echo ""
    
    # 7단계: 상태 확인
    check_system_status
    
    # 8단계: 실행 옵션 제공
    while true; do
        show_execution_menu
        echo ""
        echo -n "Would you like to perform another task? (y/n): "
        read continue_choice
        if [[ $continue_choice != "y" && $continue_choice != "Y" ]]; then
            break
        fi
        echo ""
    done
    
    print_success "Exiting File Monitor setup and launcher script!"
}

# 스크립트 실행
main "$@"
