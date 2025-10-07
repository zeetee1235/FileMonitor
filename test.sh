#!/bin/bash

# File Monitor 전체 테스트 스크립트
# 모든 기능을 자동으로 테스트하고 결과를 보고합니다.

set +e  # 에러 발생시에도 계속 진행

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 테스트 결과 추적
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 출력 함수들
print_header() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║                                                               ║"
    echo "║          🧪 File Monitor Automated Test Suite 🧪            ║"
    echo "║                                                               ║"
    echo "║         Comprehensive testing of all components              ║"
    echo "║                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
    ((TOTAL_TESTS++))
}

print_pass() {
    echo -e "${GREEN}[✓ PASS]${NC} $1"
    ((PASSED_TESTS++))
}

print_fail() {
    echo -e "${RED}[✗ FAIL]${NC} $1"
    ((FAILED_TESTS++))
}

print_info() {
    echo -e "${PURPLE}[INFO]${NC} $1"
}

print_section() {
    echo ""
    echo -e "${YELLOW}═══ $1 ═══${NC}"
    echo ""
}

# 테스트 정리 함수
cleanup() {
    print_info "Cleaning up test environment..."
    
    # 실행 중인 모니터 중지
    if python3 src/fmon.py status | grep -q "🟢 Running"; then
        python3 src/fmon.py stop >/dev/null 2>&1 || true
    fi
    
    # 테스트 파일들 정리
    rm -rf test_output/ test_temp/ >/dev/null 2>&1 || true
    rm -f test_*.log test_*.conf >/dev/null 2>&1 || true
    
    print_info "Cleanup completed"
}

# 인터럽트 처리
trap cleanup EXIT INT TERM

# 테스트 시작
main() {
    print_header
    
    print_section "1. PROJECT STRUCTURE VERIFICATION"
    test_project_structure
    
    print_section "2. DEPENDENCY CHECK"
    test_dependencies
    
    print_section "3. BUILD SYSTEM"
    test_build_system
    
    print_section "4. CLI INTERFACE"
    test_cli_interface
    
    print_section "5. CONFIGURATION SYSTEM"
    test_configuration
    
    print_section "6. MONITORING FUNCTIONALITY"
    test_monitoring
    
    print_section "7. LOG SYSTEM"
    test_log_system
    
    print_section "8. SETUP SCRIPTS"
    test_setup_scripts
    
    print_section "9. ERROR HANDLING"
    test_error_handling
    
    print_section "10. PERFORMANCE TEST"
    test_performance
    
    # 최종 결과 출력
    print_final_results
}

# 1. 프로젝트 구조 테스트
test_project_structure() {
    print_test "Checking project directory structure"
    
    required_dirs=("src" "docs" "examples")
    required_files=("README.md" "LICENSE" "requirements.txt" "setup_and_run.sh")
    required_src_files=("src/main.c" "src/fmon.py" "src/interactive_menu.py")
    
    all_good=true
    
    # 디렉토리 확인
    for dir in "${required_dirs[@]}"; do
        if [ -d "$dir" ]; then
            print_pass "Directory '$dir' exists"
        else
            print_fail "Directory '$dir' missing"
            all_good=false
        fi
    done
    
    # 루트 파일 확인
    for file in "${required_files[@]}"; do
        if [ -f "$file" ]; then
            print_pass "File '$file' exists"
        else
            print_fail "File '$file' missing"
            all_good=false
        fi
    done
    
    # 소스 파일 확인
    for file in "${required_src_files[@]}"; do
        if [ -f "$file" ]; then
            print_pass "Source file '$file' exists"
        else
            print_fail "Source file '$file' missing"
            all_good=false
        fi
    done
    
    if [ "$all_good" = true ]; then
        print_pass "Project structure is correct"
    else
        print_fail "Project structure has issues"
    fi
}

# 2. 의존성 테스트
test_dependencies() {
    print_test "Checking system dependencies"
    
    # GCC 확인
    if command -v gcc >/dev/null 2>&1; then
        print_pass "GCC compiler available"
    else
        print_fail "GCC compiler not found"
    fi
    
    # Python3 확인
    if command -v python3 >/dev/null 2>&1; then
        print_pass "Python3 available"
    else
        print_fail "Python3 not found"
    fi
    
    # Python 패키지 확인
    print_test "Checking Python packages"
    
    packages=("rich" "click" "inquirer" "psutil")
    for package in "${packages[@]}"; do
        if python3 -c "import $package" >/dev/null 2>&1; then
            print_pass "Python package '$package' available"
        else
            print_fail "Python package '$package' missing"
        fi
    done
    
    # JSON-C 라이브러리 확인 (선택적)
    print_test "Checking JSON-C library (optional)"
    if echo '#include <json-c/json.h>' | gcc -E - >/dev/null 2>&1; then
        print_pass "JSON-C library available"
    else
        print_info "JSON-C library not available (will use basic build)"
    fi
}

# 3. 빌드 시스템 테스트
test_build_system() {
    print_test "Testing C program build"
    
    # 백업 생성
    if [ -f "monitor" ]; then
        cp monitor monitor.backup
    fi
    
    # 빌드 테스트
    if gcc -o monitor src/main.c -ljson-c -lpthread >/dev/null 2>&1; then
        print_pass "C program builds with JSON-C"
    elif gcc -o monitor src/main.c -lpthread >/dev/null 2>&1; then
        print_pass "C program builds (basic version)"
    else
        print_fail "C program build failed"
    fi
    
    # 실행 파일 확인
    if [ -x "monitor" ]; then
        print_pass "Monitor executable created"
    else
        print_fail "Monitor executable not created"
    fi
    
    # CLI 빌드 명령 테스트
    print_test "Testing CLI build command"
    if timeout 10 python3 src/fmon.py build >/dev/null 2>&1; then
        print_pass "CLI build command works"
    else
        print_fail "CLI build command failed"
    fi
}

# 4. CLI 인터페이스 테스트
test_cli_interface() {
    print_test "Testing CLI help system"
    
    if python3 src/fmon.py --help >/dev/null 2>&1; then
        print_pass "Main help command works"
    else
        print_fail "Main help command failed"
    fi
    
    # 서브명령어 도움말 테스트
    subcommands=("start" "stop" "status" "logs" "config")
    for cmd in "${subcommands[@]}"; do
        if timeout 5 python3 src/fmon.py $cmd --help >/dev/null 2>&1; then
            print_pass "Help for '$cmd' command works"
        else
            print_fail "Help for '$cmd' command failed"
        fi
    done
    
    # 버전 확인
    print_test "Testing version command"
    if python3 src/fmon.py --version >/dev/null 2>&1; then
        print_pass "Version command works"
    else
        print_fail "Version command failed"
    fi
}

# 5. 설정 시스템 테스트
test_configuration() {
    print_test "Testing configuration system"
    
    # 설정 표시
    if timeout 10 python3 src/fmon.py config show >/dev/null 2>&1; then
        print_pass "Configuration display works"
    else
        print_fail "Configuration display failed"
    fi
    
    # 프리셋 테스트
    presets=("web" "dev" "all" "log")
    for preset in "${presets[@]}"; do
        print_test "Testing '$preset' preset"
        if timeout 10 bash -c "echo 'y' | python3 src/fmon.py config preset $preset" >/dev/null 2>&1; then
            print_pass "Preset '$preset' works"
        else
            print_fail "Preset '$preset' failed"
        fi
    done
}

# 6. 모니터링 기능 테스트
test_monitoring() {
    print_test "Testing monitoring functionality"
    
    # 테스트 디렉토리 생성
    mkdir -p test_output
    
    # 상태 확인 (중지 상태)
    if python3 src/fmon.py status | grep -q "🔴 Stopped"; then
        print_pass "Status check works (stopped state)"
    else
        print_fail "Status check failed (stopped state)"
    fi
    
    # 백그라운드 시작
    print_test "Starting background monitoring"
    if timeout 15 bash -c "echo 'y' | python3 src/fmon.py start test_output --background" >/dev/null 2>&1; then
        print_pass "Background monitoring started"
        
        sleep 2
        
        # 상태 확인 (실행 상태)
        if python3 src/fmon.py status | grep -q "🟢 Running"; then
            print_pass "Status check works (running state)"
        else
            print_fail "Status check failed (running state)"
        fi
        
        # 파일 생성 테스트
        print_test "Testing file monitoring"
        echo "console.log('test');" > test_output/test.js
        echo "<h1>Test</h1>" > test_output/test.html
        sleep 2
        
        # 로그 확인
        if [ -f "monitor.log" ] && grep -q "Created:" monitor.log; then
            print_pass "File events are logged"
            
            # 영어 로그 확인
            if grep -q "Created:" monitor.log && ! grep -q "생성됨:" monitor.log; then
                print_pass "Logs are in English"
            else
                print_fail "Logs contain Korean text"
            fi
        else
            print_fail "File events not logged properly"
        fi
        
        # 모니터 중지
        if python3 src/fmon.py stop >/dev/null 2>&1; then
            print_pass "Monitor stopped successfully"
        else
            print_fail "Failed to stop monitor"
        fi
        
    else
        print_fail "Failed to start background monitoring"
    fi
}

# 7. 로그 시스템 테스트
test_log_system() {
    print_test "Testing log system"
    
    # 로그가 존재하는지 확인
    if [ -f "monitor.log" ]; then
        print_pass "Log file exists"
        
        # 로그 표시
        if timeout 10 python3 src/fmon.py logs show -n 5 >/dev/null 2>&1; then
            print_pass "Log display works"
        else
            print_fail "Log display failed"
        fi
        
        # 로그 통계
        if timeout 10 python3 src/fmon.py logs stats >/dev/null 2>&1; then
            print_pass "Log statistics work"
        else
            print_fail "Log statistics failed"
        fi
        
        # 로그 검색
        if timeout 10 python3 src/fmon.py logs search "Created" >/dev/null 2>&1; then
            print_pass "Log search works"
        else
            print_fail "Log search failed"
        fi
        
    else
        print_info "No log file found (monitor not run yet)"
    fi
}

# 8. 설정 스크립트 테스트
test_setup_scripts() {
    print_test "Testing setup scripts"
    
    # setup_and_run.sh 실행 가능 여부
    if [ -x "setup_and_run.sh" ]; then
        print_pass "setup_and_run.sh is executable"
        
        # 스크립트 문법 확인
        if bash -n setup_and_run.sh >/dev/null 2>&1; then
            print_pass "setup_and_run.sh syntax is correct"
        else
            print_fail "setup_and_run.sh has syntax errors"
        fi
        
    else
        print_fail "setup_and_run.sh is not executable"
    fi
    
    # run_interactive.sh 테스트
    if [ -x "run_interactive.sh" ]; then
        print_pass "run_interactive.sh is executable"
        
        if bash -n run_interactive.sh >/dev/null 2>&1; then
            print_pass "run_interactive.sh syntax is correct"
        else
            print_fail "run_interactive.sh has syntax errors"
        fi
    else
        print_fail "run_interactive.sh is not executable"
    fi
}

# 9. 에러 처리 테스트
test_error_handling() {
    print_test "Testing error handling"
    
    # 존재하지 않는 디렉토리 모니터링
    if timeout 10 python3 src/fmon.py start /nonexistent/directory 2>/dev/null; then
        print_fail "Should fail on nonexistent directory"
    else
        print_pass "Correctly handles nonexistent directory"
    fi
    
    # 잘못된 명령어
    if timeout 5 python3 src/fmon.py invalid_command 2>/dev/null; then
        print_fail "Should fail on invalid command"
    else
        print_pass "Correctly handles invalid commands"
    fi
    
    # 중복 시작 처리
    print_test "Testing duplicate start handling"
    if timeout 15 bash -c "echo 'n' | python3 src/fmon.py start test_output --background" >/dev/null 2>&1; then
        if timeout 15 bash -c "echo 'n' | python3 src/fmon.py start test_output --background" >/dev/null 2>&1; then
            print_pass "Handles duplicate start attempts"
        else
            print_fail "Duplicate start handling failed"
        fi
        python3 src/fmon.py stop >/dev/null 2>&1 || true
    fi
}

# 10. 성능 테스트
test_performance() {
    print_test "Testing performance"
    
    # 많은 파일 생성 테스트
    mkdir -p test_temp
    
    # 백그라운드 모니터링 시작
    if timeout 15 bash -c "echo 'y' | python3 src/fmon.py start test_temp --background" >/dev/null 2>&1; then
        
        start_time=$(date +%s)
        
        # 100개 파일 생성
        for i in {1..100}; do
            echo "content $i" > test_temp/file_$i.txt >/dev/null 2>&1
        done
        
        sleep 3  # 로그 기록 시간
        
        end_time=$(date +%s)
        duration=$((end_time - start_time))
        
        if [ $duration -lt 30 ]; then
            print_pass "Performance test passed (${duration}s for 100 files)"
        else
            print_fail "Performance test failed (${duration}s for 100 files)"
        fi
        
        # 모니터 중지
        python3 src/fmon.py stop >/dev/null 2>&1 || true
        
    else
        print_fail "Could not start monitoring for performance test"
    fi
}

# 최종 결과 출력
print_final_results() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║                      TEST RESULTS SUMMARY                     ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════════════╣${NC}"
    
    echo -e "${CYAN}║${NC} Total Tests:     ${YELLOW}${TOTAL_TESTS}${NC}"
    echo -e "${CYAN}║${NC} Passed Tests:    ${GREEN}${PASSED_TESTS}${NC}"
    echo -e "${CYAN}║${NC} Failed Tests:    ${RED}${FAILED_TESTS}${NC}"
    
    # 성공률 계산
    if [ $TOTAL_TESTS -gt 0 ]; then
        success_rate=$((PASSED_TESTS * 100 / TOTAL_TESTS))
        echo -e "${CYAN}║${NC} Success Rate:    ${YELLOW}${success_rate}%${NC}"
    fi
    
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
    
    # 최종 판정
    if [ $FAILED_TESTS -eq 0 ]; then
        echo ""
        echo -e "${GREEN}🎉 ALL TESTS PASSED! 🎉${NC}"
        echo -e "${GREEN}The File Monitor system is working perfectly!${NC}"
        exit 0
    else
        echo ""
        echo -e "${RED}❌ SOME TESTS FAILED ❌${NC}"
        echo -e "${RED}Please check the failed tests above.${NC}"
        exit 1
    fi
}

# 메인 함수 실행
main "$@"
