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
#include <sys/statvfs.h>
#include <sys/resource.h>
#include <dirent.h>
#include <libgen.h>
#include <pthread.h>
#include <json-c/json.h>
#include <openssl/md5.h>
#include <openssl/sha.h>
#include <zlib.h>
#include <regex.h>

#define EVENT_SIZE          (sizeof(struct inotify_event))
#define BUF_LEN             (1024 * (EVENT_SIZE + 16))
#define MAX_WATCHES         1024
#define MAX_PATH_LEN        4096
#define CONFIG_FILE         "advanced_monitor.conf"
#define LOG_FILE            "advanced_monitor.log"
#define STATS_FILE          "monitor_stats.json"
#define IPC_SOCKET_PATH     "/tmp/advanced_monitor.sock"
#define MAX_LOG_SIZE_MB     50
#define MAX_LOG_FILES       10
#define HASH_SIZE           65
#define MAX_PATTERNS        100
#define STATS_UPDATE_INTERVAL 5

// 파일 해시 정보
typedef struct {
    char filepath[MAX_PATH_LEN];
    char hash[HASH_SIZE];
    time_t last_modified;
    off_t file_size;
} file_hash_info_t;

// 성능 통계 구조체
typedef struct {
    unsigned long events_processed;
    unsigned long files_monitored;
    double cpu_usage_percent;
    long memory_usage_kb;
    long disk_usage_percent;
    time_t start_time;
    time_t last_update;
    unsigned long events_per_second;
    unsigned long bytes_logged;
} monitor_stats_t;

// 정규식 패턴
typedef struct {
    char pattern[256];
    regex_t compiled_regex;
    int action; // 0: exclude, 1: include, 2: alert
} pattern_rule_t;

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
static pthread_t stats_thread;

// 고급 기능 변수
static file_hash_info_t *file_hashes = NULL;
static int hash_count = 0;
static int hash_capacity = 0;
static monitor_stats_t stats = {0};
static pattern_rule_t patterns[MAX_PATTERNS];
static int pattern_count = 0;
static int enable_checksum = 1;
static int enable_compression = 1;
static int max_file_size_mb = 100;
static pthread_mutex_t stats_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t hash_mutex = PTHREAD_MUTEX_INITIALIZER;

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

// 고급 기능 함수들
char* calculate_file_hash(const char *filepath);
int has_file_changed(const char *filepath);
void update_file_hash(const char *filepath);
void rotate_log_file();
void compress_old_log(const char *filename);
void update_performance_stats();
void* stats_thread_func(void* arg);
void check_system_resources();
int match_patterns(const char *filename);
void load_patterns_from_config();
void save_stats_to_file();
void print_realtime_stats();

// 신호 처리 함수
void signal_handler(int sig) {
    if (sig == SIGINT || sig == SIGTERM) {
        printf("\n[STOP] Received signal: %d. Shutting down safely...\n", sig);
        save_stats_to_file();
        cleanup_and_exit(0);
    } else if (sig == SIGUSR1) {
        // 실시간 통계 출력
        print_realtime_stats();
    }
}

// 파일 해시 계산 (SHA256)
char* calculate_file_hash(const char *filepath) {
    FILE *file = fopen(filepath, "rb");
    if (!file) return NULL;
    
    SHA256_CTX sha256;
    SHA256_Init(&sha256);
    
    char buffer[8192];
    size_t bytes;
    while ((bytes = fread(buffer, 1, sizeof(buffer), file)) > 0) {
        SHA256_Update(&sha256, buffer, bytes);
    }
    fclose(file);
    
    unsigned char hash[SHA256_DIGEST_LENGTH];
    SHA256_Final(hash, &sha256);
    
    char *hex_string = malloc(HASH_SIZE);
    for (int i = 0; i < SHA256_DIGEST_LENGTH; i++) {
        sprintf(hex_string + (i * 2), "%02x", hash[i]);
    }
    hex_string[64] = '\0';
    
    return hex_string;
}

// 파일 변경 확인 (해시 기반)
int has_file_changed(const char *filepath) {
    if (!enable_checksum) return 1;
    
    pthread_mutex_lock(&hash_mutex);
    
    // 기존 해시 찾기
    for (int i = 0; i < hash_count; i++) {
        if (strcmp(file_hashes[i].filepath, filepath) == 0) {
            char *new_hash = calculate_file_hash(filepath);
            if (!new_hash) {
                pthread_mutex_unlock(&hash_mutex);
                return 1;
            }
            
            int changed = (strcmp(file_hashes[i].hash, new_hash) != 0);
            
            if (changed) {
                strncpy(file_hashes[i].hash, new_hash, HASH_SIZE - 1);
                file_hashes[i].last_modified = time(NULL);
                
                struct stat st;
                if (stat(filepath, &st) == 0) {
                    file_hashes[i].file_size = st.st_size;
                }
            }
            
            free(new_hash);
            pthread_mutex_unlock(&hash_mutex);
            return changed;
        }
    }
    
    // 새 파일이면 해시 추가
    if (hash_count >= hash_capacity) {
        hash_capacity = hash_capacity == 0 ? 1000 : hash_capacity * 2;
        file_hashes = realloc(file_hashes, hash_capacity * sizeof(file_hash_info_t));
    }
    
    char *new_hash = calculate_file_hash(filepath);
    if (new_hash) {
        strncpy(file_hashes[hash_count].filepath, filepath, MAX_PATH_LEN - 1);
        strncpy(file_hashes[hash_count].hash, new_hash, HASH_SIZE - 1);
        file_hashes[hash_count].last_modified = time(NULL);
        
        struct stat st;
        if (stat(filepath, &st) == 0) {
            file_hashes[hash_count].file_size = st.st_size;
        }
        
        hash_count++;
        free(new_hash);
    }
    
    pthread_mutex_unlock(&hash_mutex);
    return 1; // 새 파일은 변경된 것으로 간주
}

// 로그 파일 로테이션
void rotate_log_file() {
    if (!log_file) return;
    
    fclose(log_file);
    
    char old_name[MAX_PATH_LEN];
    char new_name[MAX_PATH_LEN];
    
    // 기존 로그 파일들을 뒤로 밀기
    for (int i = MAX_LOG_FILES - 1; i > 0; i--) {
        snprintf(old_name, sizeof(old_name), "%s.%d", LOG_FILE, i - 1);
        snprintf(new_name, sizeof(new_name), "%s.%d", LOG_FILE, i);
        
        if (access(old_name, F_OK) == 0) {
            if (i == MAX_LOG_FILES - 1) {
                // 가장 오래된 파일은 삭제
                unlink(old_name);
            } else {
                rename(old_name, new_name);
            }
        }
    }
    
    // 현재 로그 파일을 .0으로 이름 변경
    snprintf(new_name, sizeof(new_name), "%s.0", LOG_FILE);
    rename(LOG_FILE, new_name);
    
    // 압축 활성화된 경우 압축
    if (enable_compression) {
        compress_old_log(new_name);
    }
    
    // 새 로그 파일 열기
    log_file = fopen(LOG_FILE, "a");
    if (log_file) {
        log_event("🔄 Log file rotated successfully");
    }
}

// 로그 파일 압축
void compress_old_log(const char *filename) {
    char gz_filename[MAX_PATH_LEN];
    snprintf(gz_filename, sizeof(gz_filename), "%s.gz", filename);
    
    FILE *input = fopen(filename, "rb");
    if (!input) return;
    
    gzFile output = gzopen(gz_filename, "wb9");
    if (!output) {
        fclose(input);
        return;
    }
    
    char buffer[8192];
    size_t bytes;
    while ((bytes = fread(buffer, 1, sizeof(buffer), input)) > 0) {
        gzwrite(output, buffer, bytes);
    }
    
    fclose(input);
    gzclose(output);
    unlink(filename); // 원본 파일 삭제
    
    char msg[512];
    snprintf(msg, sizeof(msg), "Compressed log file: %s", gz_filename);
    log_event(msg);
}

// 성능 통계 업데이트
void update_performance_stats() {
    pthread_mutex_lock(&stats_mutex);
    
    stats.last_update = time(NULL);
    
    // CPU 사용률 계산 (간단한 방법)
    struct rusage usage;
    getrusage(RUSAGE_SELF, &usage);
    
    long total_time = usage.ru_utime.tv_sec + usage.ru_stime.tv_sec;
    long elapsed_time = stats.last_update - stats.start_time;
    if (elapsed_time > 0) {
        stats.cpu_usage_percent = (double)total_time / elapsed_time * 100.0;
    }
    
    // 메모리 사용량 (KB)
    stats.memory_usage_kb = usage.ru_maxrss;
    
    // 디스크 사용량 확인
    struct statvfs disk_stat;
    if (statvfs(".", &disk_stat) == 0) {
        unsigned long total_space = disk_stat.f_blocks * disk_stat.f_frsize;
        unsigned long free_space = disk_stat.f_bavail * disk_stat.f_frsize;
        unsigned long used_space = total_space - free_space;
        stats.disk_usage_percent = (used_space * 100) / total_space;
    }
    
    // 초당 이벤트 수 계산
    if (elapsed_time > 0) {
        stats.events_per_second = stats.events_processed / elapsed_time;
    }
    
    pthread_mutex_unlock(&stats_mutex);
}

// 통계 스레드 함수
void* stats_thread_func(void* arg) {
    while (1) {
        sleep(STATS_UPDATE_INTERVAL);
        update_performance_stats();
        check_system_resources();
        save_stats_to_file();
    }
    return NULL;
}

// 시스템 리소스 확인
void check_system_resources() {
    // 로그 파일 크기 확인
    struct stat log_stat;
    if (stat(LOG_FILE, &log_stat) == 0) {
        long log_size_mb = log_stat.st_size / (1024 * 1024);
        stats.bytes_logged = log_stat.st_size;
        
        if (log_size_mb > MAX_LOG_SIZE_MB) {
            log_event("[WARN] Log file size limit reached. Rotating...");
            rotate_log_file();
        }
    }
    
    // 디스크 공간 확인
    if (stats.disk_usage_percent > 90) {
        char warning[256];
        snprintf(warning, sizeof(warning), 
                "[WARN] Disk usage critical: %ld%% used", stats.disk_usage_percent);
        log_event(warning);
    }
    
    // inotify 인스턴스 한계 확인
    FILE *max_user_instances = fopen("/proc/sys/fs/inotify/max_user_instances", "r");
    if (max_user_instances) {
        int max_instances;
        fscanf(max_user_instances, "%d", &max_instances);
        fclose(max_user_instances);
        
        if (watch_count > max_instances * 0.8) {
            log_event("[WARN] Approaching inotify watch limit");
        }
    }
}

// 정규식 패턴 매칭
int match_patterns(const char *filename) {
    if (pattern_count == 0) return 1; // 패턴이 없으면 모든 파일 허용
    
    for (int i = 0; i < pattern_count; i++) {
        if (regexec(&patterns[i].compiled_regex, filename, 0, NULL, 0) == 0) {
            if (patterns[i].action == 0) return 0; // exclude
            if (patterns[i].action == 1) return 1; // include
            if (patterns[i].action == 2) {        // alert
                char alert_msg[512];
                snprintf(alert_msg, sizeof(alert_msg), 
                        "🚨 ALERT: Pattern matched '%s' for file: %s", 
                        patterns[i].pattern, filename);
                log_event(alert_msg);
                return 1;
            }
        }
    }
    
    return 1;
}

// 설정에서 패턴 로드
void load_patterns_from_config() {
    FILE *config = fopen(CONFIG_FILE, "r");
    if (!config) return;
    
    char line[512];
    while (fgets(line, sizeof(line), config) && pattern_count < MAX_PATTERNS) {
        if (strncmp(line, "pattern_exclude=", 16) == 0) {
            line[strcspn(line, "\n")] = 0;
            strncpy(patterns[pattern_count].pattern, line + 16, 255);
            patterns[pattern_count].action = 0;
            if (regcomp(&patterns[pattern_count].compiled_regex, line + 16, REG_EXTENDED) == 0) {
                pattern_count++;
            }
        } else if (strncmp(line, "pattern_include=", 16) == 0) {
            line[strcspn(line, "\n")] = 0;
            strncpy(patterns[pattern_count].pattern, line + 16, 255);
            patterns[pattern_count].action = 1;
            if (regcomp(&patterns[pattern_count].compiled_regex, line + 16, REG_EXTENDED) == 0) {
                pattern_count++;
            }
        } else if (strncmp(line, "pattern_alert=", 14) == 0) {
            line[strcspn(line, "\n")] = 0;
            strncpy(patterns[pattern_count].pattern, line + 14, 255);
            patterns[pattern_count].action = 2;
            if (regcomp(&patterns[pattern_count].compiled_regex, line + 14, REG_EXTENDED) == 0) {
                pattern_count++;
            }
        }
    }
    
    fclose(config);
}

// 통계를 파일에 저장
void save_stats_to_file() {
    pthread_mutex_lock(&stats_mutex);
    
    json_object *root = json_object_new_object();
    json_object *events = json_object_new_int64(stats.events_processed);
    json_object *files = json_object_new_int64(stats.files_monitored);
    json_object *cpu = json_object_new_double(stats.cpu_usage_percent);
    json_object *memory = json_object_new_int64(stats.memory_usage_kb);
    json_object *disk = json_object_new_int64(stats.disk_usage_percent);
    json_object *uptime = json_object_new_int64(stats.last_update - stats.start_time);
    json_object *eps = json_object_new_int64(stats.events_per_second);
    json_object *bytes_logged = json_object_new_int64(stats.bytes_logged);
    
    json_object_object_add(root, "events_processed", events);
    json_object_object_add(root, "files_monitored", files);
    json_object_object_add(root, "cpu_usage_percent", cpu);
    json_object_object_add(root, "memory_usage_kb", memory);
    json_object_object_add(root, "disk_usage_percent", disk);
    json_object_object_add(root, "uptime_seconds", uptime);
    json_object_object_add(root, "events_per_second", eps);
    json_object_object_add(root, "bytes_logged", bytes_logged);
    
    FILE *stats_file = fopen(STATS_FILE, "w");
    if (stats_file) {
        fprintf(stats_file, "%s\n", json_object_to_json_string_ext(root, JSON_C_TO_STRING_PRETTY));
        fclose(stats_file);
    }
    
    json_object_put(root);
    pthread_mutex_unlock(&stats_mutex);
}

// 실시간 통계 출력
void print_realtime_stats() {
    pthread_mutex_lock(&stats_mutex);
    
    printf("\n[STATS] === REAL-TIME PERFORMANCE STATS ===\n");
    printf("⏱️  Uptime: %ld seconds\n", stats.last_update - stats.start_time);
    printf("🔢 Events processed: %lu\n", stats.events_processed);
    printf("[DIR] Files monitored: %lu\n", stats.files_monitored);
    printf("⚡ Events/second: %lu\n", stats.events_per_second);
    printf("🖥️  CPU usage: %.2f%%\n", stats.cpu_usage_percent);
    printf("💾 Memory usage: %ld KB\n", stats.memory_usage_kb);
    printf("💿 Disk usage: %ld%%\n", stats.disk_usage_percent);
    printf("📝 Bytes logged: %lu\n", stats.bytes_logged);
    printf("[WATCH]  Active watches: %d\n", watch_count);
    printf("[SEARCH] Hash entries: %d\n", hash_count);
    printf("📋 Regex patterns: %d\n", pattern_count);
    printf("=====================================\n\n");
    
    pthread_mutex_unlock(&stats_mutex);
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
    
    // 통계 업데이트
    pthread_mutex_lock(&stats_mutex);
    stats.events_processed++;
    pthread_mutex_unlock(&stats_mutex);
}

// 설정 파일 로드
void load_config() {
    FILE *config = fopen(CONFIG_FILE, "r");
    if (!config) {
        log_event("[CONFIG] Configuration file not found. Using default settings.");
        return;
    }
    
    char line[256];
    while (fgets(line, sizeof(line), config)) {
        if (line[0] == '#' || line[0] == '\n') continue;
        
        line[strcspn(line, "\n")] = 0;
        
        if (strncmp(line, "recursive=", 10) == 0) {
            recursive_mode = (strcmp(line + 10, "true") == 0);
        } else if (strncmp(line, "extension=", 10) == 0) {
            if (extension_count < 100) {
                file_extensions[extension_count] = malloc(strlen(line + 10) + 1);
                strcpy(file_extensions[extension_count], line + 10);
                extension_count++;
            }
        } else if (strncmp(line, "enable_checksum=", 16) == 0) {
            enable_checksum = (strcmp(line + 16, "true") == 0);
        } else if (strncmp(line, "enable_compression=", 19) == 0) {
            enable_compression = (strcmp(line + 19, "true") == 0);
        } else if (strncmp(line, "max_file_size_mb=", 17) == 0) {
            max_file_size_mb = atoi(line + 17);
        }
    }
    
    fclose(config);
    load_patterns_from_config();
    log_event("📋 Configuration file loaded.");
}

// 파일 모니터링 여부 확인 (확장된 버전)
int should_monitor_file(const char *filename) {
    // 정규식 패턴 확인
    if (!match_patterns(filename)) {
        return 0;
    }
    
    // 기존 확장자 필터
    if (extension_count == 0) return 1;
    
    const char *ext = strrchr(filename, '.');
    if (!ext) return 0;
    
    ext++;
    
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
        log_event("[WARN] Maximum number of watches reached.");
        return -1;
    }
    
    uint32_t mask = IN_CREATE | IN_DELETE | IN_MODIFY | IN_MOVED_FROM | 
                    IN_MOVED_TO | IN_ATTRIB | IN_OPEN | IN_CLOSE_WRITE;
    
    int wd = inotify_add_watch(inotify_fd, path, mask);
    if (wd == -1) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "[ERROR] Failed to add watch: %s (%s)", path, strerror(errno));
        log_event(error_msg);
        return -1;
    }
    
    watch_descriptors[watch_count] = wd;
    strncpy(watch_paths[watch_count], path, MAX_PATH_LEN - 1);
    watch_paths[watch_count][MAX_PATH_LEN - 1] = '\0';
    watch_count++;
    
    char success_msg[512];
    snprintf(success_msg, sizeof(success_msg), "[WATCH] Watch added: %s", path);
    log_event(success_msg);
    
    pthread_mutex_lock(&stats_mutex);
    stats.files_monitored++;
    pthread_mutex_unlock(&stats_mutex);
    
    return wd;
}

// 재귀적 디렉토리 watch 추가
int add_watch_recursive(const char *path) {
    struct stat statbuf;
    if (stat(path, &statbuf) != 0) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "[ERROR] Failed to check path status: %s", path);
        log_event(error_msg);
        return -1;
    }
    
    if (!S_ISDIR(statbuf.st_mode)) {
        log_event("[ERROR] Specified path is not a directory.");
        return -1;
    }
    
    if (add_single_watch(path) == -1) {
        return -1;
    }
    
    if (recursive_mode) {
        DIR *dir = opendir(path);
        if (!dir) {
            char error_msg[512];
            snprintf(error_msg, sizeof(error_msg), "[ERROR] Failed to open directory: %s", path);
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

// 이벤트 처리 함수 (확장된 버전)
void handle_event(struct inotify_event *event, const char *watch_path) {
    if (!event->len) return;
    
    // 시스템 파일 제외
    if (strcmp(event->name, LOG_FILE) == 0 || 
        strcmp(event->name, CONFIG_FILE) == 0 ||
        strcmp(event->name, STATS_FILE) == 0 ||
        strstr(event->name, ".tmp") != NULL ||
        strstr(event->name, ".swp") != NULL) {
        return;
    }
    
    if (!should_monitor_file(event->name)) {
        return;
    }
    
    char full_path[MAX_PATH_LEN];
    snprintf(full_path, sizeof(full_path), "%s/%s", watch_path, event->name);
    
    char event_msg[1024];
    
    // 파일 크기 확인
    struct stat st;
    long file_size = 0;
    if (stat(full_path, &st) == 0) {
        file_size = st.st_size;
        
        // 파일 크기 제한 확인
        if (file_size > max_file_size_mb * 1024 * 1024) {
            snprintf(event_msg, sizeof(event_msg),
                    "Large file detected (%ld MB): %s",
                    file_size / (1024 * 1024), full_path);
            log_event(event_msg);
        }
    }
    
    if (event->mask & IN_CREATE) {
        snprintf(event_msg, sizeof(event_msg), "Created: %s (%ld bytes)", full_path, file_size);
        log_event(event_msg);
        
        if (recursive_mode && (event->mask & IN_ISDIR)) {
            add_watch_recursive(full_path);
        }
    }
    
    if (event->mask & IN_DELETE) {
        snprintf(event_msg, sizeof(event_msg), "Deleted: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_MODIFY) {
        // 체크섬 기반 실제 변경 확인
        if (has_file_changed(full_path)) {
            snprintf(event_msg, sizeof(event_msg), "Modified: %s (%ld bytes)", full_path, file_size);
            log_event(event_msg);
        }
    }
    
    if (event->mask & IN_MOVED_FROM) {
        snprintf(event_msg, sizeof(event_msg), "Moved from: %s", full_path);
        log_event(event_msg);
    }
    
    if (event->mask & IN_MOVED_TO) {
        snprintf(event_msg, sizeof(event_msg), "Moved to: %s (%ld bytes)", full_path, file_size);
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
        snprintf(event_msg, sizeof(event_msg), "Closed: %s (%ld bytes)", full_path, file_size);
        log_event(event_msg);
    }
}

// 정리 및 종료 함수
void cleanup_and_exit(int code) {
    log_event("[STOP] Program terminating");
    
    // 통계 저장
    save_stats_to_file();
    
    // 스레드 종료
    if (stats_thread) {
        pthread_cancel(stats_thread);
    }
    
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
    
    // 메모리 해제
    for (int i = 0; i < extension_count; i++) {
        free(file_extensions[i]);
    }
    
    if (file_hashes) {
        free(file_hashes);
    }
    
    for (int i = 0; i < pattern_count; i++) {
        regfree(&patterns[i].compiled_regex);
    }
    
    exit(code);
}

// 사용법 출력
void print_usage(const char *program_name) {
    printf("[SEARCH] Advanced File Monitor v2.0\n");
    printf("Usage: %s <directory_to_monitor>\n", program_name);
    printf("\nOptions:\n");
    printf("  -h, --help     Show this help message\n");
    printf("  -s, --stats    Print real-time statistics (send SIGUSR1)\n");
    printf("\nFeatures:\n");
    printf("  [OK] Real-time performance monitoring\n");
    printf("  [SEARCH] File checksum-based change detection\n");
    printf("  🔄 Automatic log rotation and compression\n");
    printf("  📋 Advanced regex pattern matching\n");
    printf("  [STATS] System resource monitoring\n");
    printf("  💾 JSON-based statistics export\n");
    printf("\nConfiguration file: %s\n", CONFIG_FILE);
    printf("Log file: %s\n", LOG_FILE);
    printf("Statistics file: %s\n", STATS_FILE);
    printf("\nSend SIGUSR1 to display real-time stats: kill -USR1 <pid>\n");
}

int main(int argc, char **argv) {
    setlocale(LC_ALL, "en_US.UTF-8");
    
    if (argc < 2) {
        print_usage(argv[0]);
        exit(1);
    }
    
    if (strcmp(argv[1], "-h") == 0 || strcmp(argv[1], "--help") == 0) {
        print_usage(argv[0]);
        exit(0);
    }
    
    // 신호 처리 등록
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGUSR1, signal_handler);
    
    // 통계 초기화
    stats.start_time = time(NULL);
    stats.last_update = stats.start_time;
    
    // 로그 파일 열기
    log_file = fopen(LOG_FILE, "a");
    if (!log_file) {
        fprintf(stderr, "[ERROR] Cannot open log file: %s\n", LOG_FILE);
        exit(1);
    }
    
    // 설정 파일 로드
    load_config();
    
    // 통계 스레드 시작
    if (pthread_create(&stats_thread, NULL, stats_thread_func, NULL) != 0) {
        log_event("[WARN] Failed to create statistics thread");
    }
    
    // inotify 초기화
    inotify_fd = inotify_init1(IN_CLOEXEC);
    if (inotify_fd < 0) {
        perror("[ERROR] inotify_init1 failed");
        cleanup_and_exit(1);
    }
    
    // watch 추가
    if (add_watch_recursive(argv[1]) == -1) {
        cleanup_and_exit(1);
    }
    
    char start_msg[512];
    snprintf(start_msg, sizeof(start_msg), 
            "[START] Advanced File Monitor started: %s (recursive: %s, checksum: %s, compression: %s)", 
            argv[1], 
            recursive_mode ? "yes" : "no",
            enable_checksum ? "yes" : "no",
            enable_compression ? "yes" : "no");
    log_event(start_msg);
    
    if (extension_count > 0) {
        char ext_msg[512] = "[SEARCH] Filter extensions: ";
        for (int i = 0; i < extension_count; i++) {
            strcat(ext_msg, file_extensions[i]);
            if (i < extension_count - 1) strcat(ext_msg, ", ");
        }
        log_event(ext_msg);
    }
    
    if (pattern_count > 0) {
        char pattern_msg[256];
        snprintf(pattern_msg, sizeof(pattern_msg), "📋 Loaded %d regex patterns", pattern_count);
        log_event(pattern_msg);
    }
    
    log_event("[INFO] Send SIGUSR1 for real-time stats (kill -USR1 <pid>)");
    
    // 이벤트 처리 루프
    char buffer[BUF_LEN];
    while (1) {
        ssize_t length = read(inotify_fd, buffer, BUF_LEN);
        if (length < 0) {
            if (errno == EINTR) continue;
            perror("[ERROR] read error");
            break;
        }
        
        ssize_t i = 0;
        while (i < length) {
            struct inotify_event *event = (struct inotify_event *) &buffer[i];
            
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
