#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <errno.h>
#include <locale.h>
#include <sys/inotify.h>
#include <sys/stat.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <dirent.h>
#include <libgen.h>
#include <pthread.h>
#include <json-c/json.h>

#define EVENT_SIZE      (sizeof(struct inotify_event))
#define BUF_LEN         (1024 * (EVENT_SIZE + 16))
#define MAX_WATCHES     1024
#define MAX_PATH_LEN    4096
#define CONFIG_FILE     "monitor.conf"
#define LOG_FILE        "monitor.log"
#define IPC_SOCKET_PATH "/tmp/file_monitor.sock"

// 전역 변수
static int inotify_fd = -1;
static int watch_descriptors[MAX_WATCHES];
static char watch_paths[MAX_WATCHES][MAX_PATH_LEN];
static int watch_count = 0;
static FILE *log_file = NULL;
static int recursive_mode = 1;
static char *file_extensions[100];
static int extension_count = 0;
static int ipc_socket = -1;
static pthread_t ipc_thread;

// 함수 선언
void signal_handler(int sig);
void cleanup_and_exit(int code);
void log_event(const char *message);
char *get_timestamp();
void load_config();
int should_monitor_file(const char *filename);
int add_watch_recursive(const char *path);
int add_single_watch(const char *path);
void handle_event(struct inotify_event *event, const char *watch_path);
void print_usage(const char *program_name);
int setup_ipc_socket();
void* ipc_thread_func(void* arg);
void handle_ipc_command(int client_fd, const char* command);
void cleanup_ipc();

// 신호 처리 함수
void signal_handler(int sig) {
    if (sig == SIGINT || sig == SIGTERM) {
        printf("\nReceived signal: %d. Shutting down safely...\n", sig);
        cleanup_and_exit(0);
    }
}

// IPC 정리
void cleanup_ipc() {
    if (ipc_socket != -1) {
        close(ipc_socket);
    }
    unlink(IPC_SOCKET_PATH);
}

// 정리 및 종료 함수
void cleanup_and_exit(int code) {
    log_event("Program terminating");
    
    // IPC 정리
    cleanup_ipc();
    
    // 모든 watch 제거
    for (int i = 0; i < watch_count; i++) {
        if (watch_descriptors[i] != -1) {
            inotify_rm_watch(inotify_fd, watch_descriptors[i]);
        }
    }
    
    // 파일 디스크립터 닫기
    if (inotify_fd != -1) {
        close(inotify_fd);
    }
    
    // 로그 파일 닫기
    if (log_file) {
        fclose(log_file);
    }
    
    // 확장자 메모리 해제
    for (int i = 0; i < extension_count; i++) {
        free(file_extensions[i]);
    }
    
    exit(code);
}

// 타임스탬프 생성
char *get_timestamp() {
    static char timestamp[64];
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm_info);
    return timestamp;
}

// 로그 기록 함수
void log_event(const char *message) {
    char *timestamp = get_timestamp();
    
    // 콘솔 출력
    printf("[%s] %s\n", timestamp, message);
    
    // 로그 파일에 기록
    if (log_file) {
        fprintf(log_file, "[%s] %s\n", timestamp, message);
        fflush(log_file);
    }
}

// 설정 파일 로드
void load_config() {
    FILE *config = fopen(CONFIG_FILE, "r");
    if (!config) {
        log_event("Configuration file not found. Using default settings.");
        return;
    }
    
    char line[256];
    while (fgets(line, sizeof(line), config)) {
        // 주석 및 빈 줄 건너뛰기
        if (line[0] == '#' || line[0] == '\n') continue;
        
        // 개행 문자 제거
        line[strcspn(line, "\n")] = 0;
        
        if (strncmp(line, "recursive=", 10) == 0) {
            recursive_mode = (strcmp(line + 10, "true") == 0);
        } else if (strncmp(line, "extension=", 10) == 0) {
            if (extension_count < 100) {
                file_extensions[extension_count] = malloc(strlen(line + 10) + 1);
                strcpy(file_extensions[extension_count], line + 10);
                extension_count++;
            }
        }
    }
    
    fclose(config);
    log_event("Configuration file loaded.");
}

// 파일 모니터링 여부 확인
int should_monitor_file(const char *filename) {
    if (extension_count == 0) return 1; // 필터가 없으면 모든 파일 모니터링
    
    const char *ext = strrchr(filename, '.');
    if (!ext) return 0; // 확장자가 없으면 무시
    
    ext++; // '.' 건너뛰기
    
    for (int i = 0; i < extension_count; i++) {
        if (strcmp(ext, file_extensions[i]) == 0) {
            return 1;
        }
    }
    
    return 0;
}

// 단일 디렉토리 watch 추가
int add_single_watch(const char *path) {
    if (watch_count >= MAX_WATCHES) {
        log_event("Maximum number of watches reached.");
        return -1;
    }
    
    uint32_t mask = IN_CREATE | IN_DELETE | IN_MODIFY | IN_MOVED_FROM | 
                    IN_MOVED_TO | IN_ATTRIB | IN_OPEN | IN_CLOSE_WRITE;
    
    int wd = inotify_add_watch(inotify_fd, path, mask);
    if (wd == -1) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "Failed to add watch: %s (%s)", path, strerror(errno));
        log_event(error_msg);
        return -1;
    }
    
    watch_descriptors[watch_count] = wd;
    strncpy(watch_paths[watch_count], path, MAX_PATH_LEN - 1);
    watch_paths[watch_count][MAX_PATH_LEN - 1] = '\0';
    watch_count++;
    
    char success_msg[512];
    snprintf(success_msg, sizeof(success_msg), "Watch added: %s", path);
    log_event(success_msg);
    
    return wd;
}

// 재귀적 디렉토리 watch 추가
int add_watch_recursive(const char *path) {
    struct stat statbuf;
    if (stat(path, &statbuf) != 0) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "Failed to check path status: %s", path);
        log_event(error_msg);
        return -1;
    }
    
    if (!S_ISDIR(statbuf.st_mode)) {
        log_event("Specified path is not a directory.");
        return -1;
    }
    
    // 현재 디렉토리에 watch 추가
    if (add_single_watch(path) == -1) {
        return -1;
    }
    
    // 재귀 모드가 활성화된 경우 하위 디렉토리도 처리
    if (recursive_mode) {
        DIR *dir = opendir(path);
        if (!dir) {
            char error_msg[512];
            snprintf(error_msg, sizeof(error_msg), "Failed to open directory: %s", path);
            log_event(error_msg);
            return -1;
        }
        
        struct dirent *entry;
        while ((entry = readdir(dir)) != NULL) {
            if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
                continue;
            }
            
            char full_path[MAX_PATH_LEN];
            snprintf(full_path, sizeof(full_path), "%s/%s", path, entry->d_name);
            
            if (stat(full_path, &statbuf) == 0 && S_ISDIR(statbuf.st_mode)) {
                add_watch_recursive(full_path);
            }
        }
        
        closedir(dir);
    }
    
    return 0;
}

// 이벤트 처리 함수
void handle_event(struct inotify_event *event, const char *watch_path) {
    if (!event->len) return;
    
    // 로그 파일과 설정 파일은 모니터링에서 제외 (무한 루프 방지)
    if (strcmp(event->name, LOG_FILE) == 0 || 
        strcmp(event->name, CONFIG_FILE) == 0 ||
        strstr(event->name, ".tmp") != NULL ||
        strstr(event->name, ".swp") != NULL) {
        return;
    }
    
    // 파일 필터링 확인
    if (!should_monitor_file(event->name)) {
        return;
    }
    
    char full_path[MAX_PATH_LEN];
    snprintf(full_path, sizeof(full_path), "%s/%s", watch_path, event->name);
    
    char event_msg[1024];
    
    if (event->mask & IN_CREATE) {
        snprintf(event_msg, sizeof(event_msg), "Created: %s", full_path);
        log_event(event_msg);
        
        // 새로 생성된 디렉토리가 있으면 재귀적으로 watch 추가
        if (recursive_mode && (event->mask & IN_ISDIR)) {
            add_watch_recursive(full_path);
        }
    }
    
    if (event->mask & IN_DELETE) {
        snprintf(event_msg, sizeof(event_msg), "Deleted: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_MODIFY) {
        snprintf(event_msg, sizeof(event_msg), "Modified: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_MOVED_FROM) {
        snprintf(event_msg, sizeof(event_msg), "Moved from: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_MOVED_TO) {
        snprintf(event_msg, sizeof(event_msg), "Moved to: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_ATTRIB) {
        snprintf(event_msg, sizeof(event_msg), "Attribute changed: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_OPEN) {
        snprintf(event_msg, sizeof(event_msg), "Opened: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_CLOSE_WRITE) {
        snprintf(event_msg, sizeof(event_msg), "Closed: %s", full_path);
        log_event(event_msg);
    }
}

// IPC 소켓 설정
int setup_ipc_socket() {
    int sock;
    struct sockaddr_un addr;
    
    // 기존 소켓 파일 제거
    unlink(IPC_SOCKET_PATH);
    
    sock = socket(AF_UNIX, SOCK_STREAM, 0);
    if (sock == -1) {
        perror("IPC socket creation failed");
        return -1;
    }
    
    memset(&addr, 0, sizeof(addr));
    addr.sun_family = AF_UNIX;
    strcpy(addr.sun_path, IPC_SOCKET_PATH);
    
    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) == -1) {
        perror("IPC socket bind failed");
        close(sock);
        return -1;
    }
    
    if (listen(sock, 5) == -1) {
        perror("IPC socket listen failed");
        close(sock);
        return -1;
    }
    
    return sock;
}

// IPC 명령 처리
void handle_ipc_command(int client_fd, const char* command) {
    json_object *root = json_object_new_object();
    json_object *success = json_object_new_boolean(1);
    json_object_object_add(root, "success", success);
    
    // 명령 파싱
    json_object *cmd_obj = json_tokener_parse(command);
    if (cmd_obj) {
        json_object *cmd_name;
        if (json_object_object_get_ex(cmd_obj, "command", &cmd_name)) {
            const char *cmd_str = json_object_get_string(cmd_name);
            
            if (strcmp(cmd_str, "status") == 0) {
                json_object *data = json_object_new_object();
                json_object *running = json_object_new_boolean(1);
                json_object *watch_cnt = json_object_new_int(watch_count);
                
                json_object_object_add(data, "running", running);
                json_object_object_add(data, "watch_count", watch_cnt);
                json_object_object_add(root, "data", data);
            } else if (strcmp(cmd_str, "stop") == 0) {
                json_object *msg = json_object_new_string("Stopping monitoring");
                json_object_object_add(root, "message", msg);
                
                // 응답 전송 후 종료
                const char *response = json_object_to_json_string(root);
                send(client_fd, response, strlen(response), 0);
                close(client_fd);
                json_object_put(root);
                json_object_put(cmd_obj);
                cleanup_and_exit(0);
                return;
            }
        }
        json_object_put(cmd_obj);
    }
    
    // 응답 전송
    const char *response = json_object_to_json_string(root);
    send(client_fd, response, strlen(response), 0);
    close(client_fd);
    json_object_put(root);
}

// IPC 스레드 함수
void* ipc_thread_func(void* arg) {
    int sock = *(int*)arg;
    
    while (1) {
        int client_fd = accept(sock, NULL, NULL);
        if (client_fd == -1) {
            if (errno == EINTR) continue;
            perror("IPC accept failed");
            break;
        }
        
        char buffer[1024];
        ssize_t bytes = recv(client_fd, buffer, sizeof(buffer) - 1, 0);
        if (bytes > 0) {
            buffer[bytes] = '\0';
            handle_ipc_command(client_fd, buffer);
        } else {
            close(client_fd);
        }
    }
    
    return NULL;
}

// 사용법 출력
void print_usage(const char *program_name) {
    printf("사용법: %s <감시할_디렉토리>\n", program_name);
    printf("\n옵션:\n");
    printf("  -h, --help     이 도움말 출력\n");
    printf("\n설정 파일 (%s) 형식:\n", CONFIG_FILE);
    printf("  recursive=true         # 하위 디렉토리 재귀 감시\n");
    printf("  extension=txt          # 특정 확장자만 감시\n");
    printf("  extension=log          # 여러 확장자 지정 가능\n");
    printf("\n로그는 %s 파일에 저장됩니다.\n", LOG_FILE);
    printf("IPC 소켓: %s\n", IPC_SOCKET_PATH);
}

int main(int argc, char **argv) {
    // UTF-8 로케일 설정
    setlocale(LC_ALL, "en_US.UTF-8");
    
    // 인수 확인
    if (argc < 2) {
        print_usage(argv[0]);
        exit(1);
    }
    
    // 도움말 옵션 확인
    if (strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0) {
        print_usage(argv[0]);
        exit(0);
    }
    
    // 신호 처리 등록
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    // 로그 파일 열기
    log_file = fopen(LOG_FILE, "a");
    if (!log_file) {
        fprintf(stderr, "로그 파일을 열 수 없습니다: %s\n", LOG_FILE);
        exit(1);
    }
    
    // 설정 파일 로드
    load_config();
    
    // IPC 소켓 설정
    ipc_socket = setup_ipc_socket();
    if (ipc_socket != -1) {
        if (pthread_create(&ipc_thread, NULL, ipc_thread_func, &ipc_socket) != 0) {
            perror("IPC thread creation failed");
            close(ipc_socket);
            ipc_socket = -1;
        } else {
            log_event("IPC socket initialized");
        }
    }
    
    // inotify 초기화
    inotify_fd = inotify_init1(IN_CLOEXEC);
    if (inotify_fd < 0) {
        perror("inotify_init1 실패");
        cleanup_and_exit(1);
    }
    
    // watch 추가
    if (add_watch_recursive(argv[1]) == -1) {
        cleanup_and_exit(1);
    }
    
    char start_msg[512];
    snprintf(start_msg, sizeof(start_msg), "File monitoring started: %s (recursive: %s)", 
             argv[1], recursive_mode ? "yes" : "no");
    log_event(start_msg);
    
    if (extension_count > 0) {
        char ext_msg[512] = "Filter extensions: ";
        for (int i = 0; i < extension_count; i++) {
            strcat(ext_msg, file_extensions[i]);
            if (i < extension_count - 1) strcat(ext_msg, ", ");
        }
        log_event(ext_msg);
    }
    
    // 이벤트 처리 루프
    char buffer[BUF_LEN];
    while (1) {
        ssize_t length = read(inotify_fd, buffer, BUF_LEN);
        if (length < 0) {
            if (errno == EINTR) continue; // 신호에 의한 중단은 계속
            perror("read error");
            break;
        }
        
        ssize_t i = 0;
        while (i < length) {
            struct inotify_event *event = (struct inotify_event *) &buffer[i];
            
            // 해당 watch의 경로 찾기
            char *watch_path = NULL;
            for (int j = 0; j < watch_count; j++) {
                if (watch_descriptors[j] == event->wd) {
                    watch_path = watch_paths[j];
                    break;
                }
            }
            
            if (watch_path) {
                handle_event(event, watch_path);
            }
            
            i += EVENT_SIZE + event->len;
        }
    }
    
    cleanup_and_exit(0);
    return 0;
}