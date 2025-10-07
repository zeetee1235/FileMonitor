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
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║          🔍 File Monitor Auto Setup & Launcher 🚀            ║"
    echo "║                                                               ║"
    echo "║         Complete setup and execution in one script!           ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 진행상황 출력
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_info() {
    echo -e "${PURPLE}[ℹ]${NC} $1"
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
    print_step "Building C monitor program..."
    
    if [ -f "src/main.c" ]; then
        # JSON-C 라이브러리와 함께 컴파일
        if gcc -o monitor src/main.c -ljson-c -lpthread 2>/dev/null; then
            print_success "C program build successful!"
        else
            print_warning "JSON-C library not found. Attempting to build basic version..."
            if gcc -o monitor src/main.c -lpthread; then
                print_success "Basic C program build successful!"
            else
                print_error "Failed to build C program."
                exit 1
            fi
        fi
    else
        print_error "src/main.c file not found."
        exit 1
    fi
}

# 설정 파일 생성
create_config_files() {
    print_step "Checking and creating configuration files..."
    
    # monitor.conf 파일이 없으면 기본 설정 생성
    if [ ! -f "monitor.conf" ]; then
        print_info "Creating default configuration file..."
        if [ -f "examples/monitor.conf" ]; then
            cp examples/monitor.conf .
            print_success "Configuration file copied from examples/monitor.conf"
        else
            cat > monitor.conf << 'EOF'
# File Monitor Configuration File
# Comments start with '#'

# Recursive directory monitoring
recursive=true

# File extensions to monitor (web development preset)
extension=html
extension=css
extension=js
extension=ts
extension=jsx
extension=tsx
extension=vue
extension=scss
extension=less
extension=json
extension=xml
EOF
            print_success "Default configuration file (monitor.conf) created successfully!"
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
    
    echo -e "${CYAN}┌─────────────────────────────────────────┐${NC}"
    echo -e "${CYAN}│               System Status             │${NC}"
    echo -e "${CYAN}├─────────────────────────────────────────┤${NC}"
    
    # 파일 존재 확인
    if [ -f "monitor" ]; then
        echo -e "${CYAN}│${NC} C Program:      ${GREEN}✓ Built${NC}                 │"
    else
        echo -e "${CYAN}│${NC} C Program:      ${RED}✗ Missing${NC}              │"
    fi
    
    if [ -f "src/fmon.py" ]; then
        echo -e "${CYAN}│${NC} Python CLI:     ${GREEN}✓ Ready${NC}                │"
    else
        echo -e "${CYAN}│${NC} Python CLI:     ${RED}✗ Missing${NC}              │"
    fi
    
    if [ -f "src/interactive_menu.py" ]; then
        echo -e "${CYAN}│${NC} Interactive Menu: ${GREEN}✓ Ready${NC}              │"
    else
        echo -e "${CYAN}│${NC} Interactive Menu: ${RED}✗ Missing${NC}            │"
    fi
    
    if [ -f "monitor.conf" ]; then
        echo -e "${CYAN}│${NC} Config File:    ${GREEN}✓ Present${NC}              │"
    else
        echo -e "${CYAN}│${NC} Config File:    ${RED}✗ Missing${NC}              │"
    fi
    
    # 모니터 실행 상태 확인
    if [ -f "monitor.pid" ]; then
        PID=$(cat monitor.pid)
        if kill -0 $PID 2>/dev/null; then
            echo -e "${CYAN}│${NC} Monitor Status: ${GREEN}🟢 Running (PID: $PID)${NC}     │"
        else
            echo -e "${CYAN}│${NC} Monitor Status: ${RED}🔴 Stopped${NC}              │"
            rm -f monitor.pid
        fi
    else
        echo -e "${CYAN}│${NC} Monitor Status: ${RED}🔴 Stopped${NC}              │"
    fi
    
    echo -e "${CYAN}└─────────────────────────────────────────┘${NC}"
}

# 실행 옵션 메뉴
show_execution_menu() {
    echo ""
    print_step "Please select an execution option:"
    echo ""
    echo -e "${GREEN}1)${NC} 🎮 Interactive Mode (Arrow keys + Enter)"
    echo -e "${GREEN}2)${NC} 🚀 Start Background Monitoring"
    echo -e "${GREEN}3)${NC} 📊 Check Current Status"
    echo -e "${GREEN}4)${NC} 📄 View Recent Logs"
    echo -e "${GREEN}5)${NC} 📺 Real-time Dashboard"
    echo -e "${GREEN}6)${NC} ⚙️ View Configuration"
    echo -e "${GREEN}7)${NC} 🧪 Create Test Files and Test Monitoring"
    echo -e "${GREEN}8)${NC} ❌ Exit"
    echo ""
    echo -n "Choice (1-8): "
    read choice
    
    case $choice in
        1)
            print_info "Starting interactive mode..."
            python3 src/interactive_menu.py
            ;;
        2)
            print_info "Starting background monitoring..."
            python3 src/fmon.py start . --background
            sleep 2
            python3 src/fmon.py status
            ;;
        3)
            print_info "Checking current status..."
            python3 src/fmon.py status
            ;;
        4)
            print_info "Displaying recent logs..."
            python3 src/fmon.py logs show -n 10
            ;;
        5)
            print_info "Starting real-time dashboard... (Press Q to exit)"
            sleep 1
            python3 src/fmon.py dashboard
            ;;
        6)
            print_info "Displaying current configuration..."
            python3 src/fmon.py config show
            ;;
        7)
            print_info "Running test..."
            run_test_demo
            ;;
        8)
            print_info "Exiting script."
            exit 0
            ;;
        *)
            print_error "Invalid choice. Please enter a number between 1-8."
            show_execution_menu
            ;;
    esac
}

# 테스트 데모 실행
run_test_demo() {
    print_step "Running file monitoring test..."
    
    # 모니터가 실행 중인지 확인
    if [ ! -f "monitor.pid" ]; then
        print_info "Starting monitoring for test..."
        python3 src/fmon.py start test_dir --background
        sleep 2
    fi
    
    print_info "Performing file change test in test_dir..."
    
    # 테스트 파일들 생성
    echo "// Test file 1" > test_dir/test1.js
    sleep 1
    echo "<h1>Test HTML</h1>" > test_dir/test.html
    sleep 1
    echo "body { color: red; }" > test_dir/test.css
    sleep 1
    
    print_success "Test files have been created!"
    print_info "Checking recent logs..."
    sleep 1
    
    python3 src/fmon.py logs show -n 5
    
    print_info "Test completed. Please verify that file changes have been logged."
}

# 메인 실행 함수
main() {
    print_logo
    
    echo -e "${YELLOW}🔧 Starting automatic setup...${NC}"
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
    print_success "🎉 All setup completed successfully!"
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
    
    print_success "👋 Exiting File Monitor setup and launcher script!"
}

# 스크립트 실행
main "$@"
