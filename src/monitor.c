/*
 * Unified File Monitor
 * Consolidated implementation supporting three modes:
 *   - basic: Simple file monitoring
 *   - advanced: File monitoring with checksums and compression
 *   - enhanced: File monitoring with dynamic scaling
 */

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
#include <sys/resource.h>
#include <sys/statvfs.h>
#include <dirent.h>
#include <libgen.h>
#include <pthread.h>
#include <json-c/json.h>
#include <openssl/sha.h>
#include <zlib.h>

// Constants
#define EVENT_SIZE          (sizeof(struct inotify_event))
#define BUF_LEN             (1024 * (EVENT_SIZE + 16))
#define MAX_PATH_LEN        4096
#define CONFIG_FILE         "monitor.conf"
#define LOG_FILE            "monitor.log"
#define STATS_FILE          "monitor_stats.json"
#define IPC_SOCKET_PATH     "/tmp/file_monitor.sock"
#define INITIAL_WATCH_CAPACITY 1024
#define WATCH_GROWTH_FACTOR    2
#define MAX_LOG_SIZE_MB     50
#define MAX_LOG_FILES       10
#define HASH_SIZE           65
#define STATS_UPDATE_INTERVAL 5

// Monitor modes
typedef enum {
    MODE_BASIC,
    MODE_ADVANCED,
    MODE_ENHANCED
} monitor_mode_t;

// Dynamic watch management structure (for enhanced mode)
typedef struct {
    int wd;
    char path[MAX_PATH_LEN];
    time_t added_time;
    unsigned long event_count;
} watch_entry_t;

typedef struct {
    watch_entry_t *entries;
    size_t capacity;
    size_t count;
    pthread_mutex_t mutex;
} watch_manager_t;

// File hash info (for advanced mode)
typedef struct {
    char filepath[MAX_PATH_LEN];
    char hash[HASH_SIZE];
    time_t last_modified;
    off_t file_size;
} file_hash_info_t;

// Statistics structure
typedef struct {
    unsigned long total_events;
    unsigned long total_files_processed;
    unsigned long memory_usage_kb;
    double cpu_usage_percent;
    time_t start_time;
    time_t last_update;
    unsigned long watch_limit_hits;
    unsigned long memory_reallocations;
    unsigned long events_per_second;
    unsigned long bytes_logged;
    long disk_usage_percent;
    char most_active_path[MAX_PATH_LEN];
    unsigned long max_events_per_path;
} monitor_stats_t;

// Global variables
static monitor_mode_t mode = MODE_BASIC;
static int inotify_fd = -1;
static FILE *log_file = NULL;
static int recursive_mode = 1;
static volatile int running = 1;
static pthread_t stats_thread;
static int ipc_socket = -1;

// Basic mode variables
static int watch_descriptors[1024];
static char watch_paths[1024][MAX_PATH_LEN];
static int watch_count = 0;

// Enhanced mode variables
static watch_manager_t watch_manager = {0};

// Advanced mode variables
static file_hash_info_t *file_hashes = NULL;
static int hash_count = 0;
static int hash_capacity = 0;
static int enable_checksum = 1;
static int enable_compression = 1;
static pthread_mutex_t hash_mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_mutex_t stats_mutex = PTHREAD_MUTEX_INITIALIZER;

// File extensions filter
static char **file_extensions = NULL;
static int extension_count = 0;

// Statistics
static monitor_stats_t stats = {0};

// Function declarations
void signal_handler(int sig);
void cleanup_and_exit(int code);
void log_event(const char *message);
char *get_timestamp();
int load_config();
int should_monitor_file(const char *filename);
void print_usage(const char *program_name);

// Basic mode functions
int add_watch_basic(const char *path);
int add_watch_recursive_basic(const char *path);
void handle_event_basic(struct inotify_event *event, const char *watch_path);

// Enhanced mode functions
int init_watch_manager();
void cleanup_watch_manager();
int add_watch_dynamic(const char *path);
watch_entry_t *find_watch_by_wd(int wd);
int add_watch_recursive_enhanced(const char *path);
void handle_event_enhanced(struct inotify_event *event);

// Advanced mode functions
char* calculate_file_hash(const char *filepath);
int check_file_changed(const char *filepath);
void update_file_hash(const char *filepath);
void rotate_log_file();
void compress_old_log(const char *filename);
void handle_event_advanced(struct inotify_event *event, const char *watch_path);

// Statistics functions
void update_stats();
void save_stats();
void* stats_thread_func(void* arg);

// Signal handler
void signal_handler(int sig) {
    if (sig == SIGINT || sig == SIGTERM) {
        printf("\n[STOP] Received signal: %d. Shutting down safely...\n", sig);
        running = 0;
        save_stats();
        cleanup_and_exit(0);
    } else if (sig == SIGUSR1) {
        update_stats();
        printf("\n=== MONITOR STATS ===\n");
        printf("Mode: %s\n", mode == MODE_BASIC ? "basic" : 
                             mode == MODE_ADVANCED ? "advanced" : "enhanced");
        printf("Total Events: %lu\n", stats.total_events);
        if (mode == MODE_ENHANCED) {
            printf("Active Watches: %zu/%zu\n", watch_manager.count, watch_manager.capacity);
            printf("Memory Reallocations: %lu\n", stats.memory_reallocations);
        } else {
            printf("Active Watches: %d\n", watch_count);
        }
        printf("Memory Usage: %lu KB\n", stats.memory_usage_kb);
        printf("Uptime: %ld seconds\n", time(NULL) - stats.start_time);
        printf("=====================\n");
    }
}

// Cleanup and exit
void cleanup_and_exit(int code) {
    running = 0;
    
    if (inotify_fd != -1) {
        if (mode == MODE_ENHANCED) {
            // Enhanced mode cleanup
            pthread_mutex_lock(&watch_manager.mutex);
            for (size_t i = 0; i < watch_manager.count; i++) {
                inotify_rm_watch(inotify_fd, watch_manager.entries[i].wd);
            }
            pthread_mutex_unlock(&watch_manager.mutex);
            cleanup_watch_manager();
        } else {
            // Basic/Advanced mode cleanup
            for (int i = 0; i < watch_count; i++) {
                if (watch_descriptors[i] != -1) {
                    inotify_rm_watch(inotify_fd, watch_descriptors[i]);
                }
            }
        }
        close(inotify_fd);
        inotify_fd = -1;
    }
    
    if (log_file) {
        fclose(log_file);
        log_file = NULL;
    }
    
    if (ipc_socket != -1) {
        close(ipc_socket);
        unlink(IPC_SOCKET_PATH);
        ipc_socket = -1;
    }
    
    // Cleanup file extensions
    if (file_extensions) {
        for (int i = 0; i < extension_count; i++) {
            free(file_extensions[i]);
        }
        free(file_extensions);
    }
    
    // Cleanup file hashes (advanced mode)
    if (file_hashes) {
        free(file_hashes);
    }
    
    save_stats();
    log_event("[STOP] Monitor terminated gracefully");
    
    exit(code);
}

// Logging functions
void log_event(const char *message) {
    if (!log_file) return;
    
    char *timestamp = get_timestamp();
    fprintf(log_file, "[%s] %s\n", timestamp, message);
    fflush(log_file);
    free(timestamp);
    
    // Check log size and rotate if needed (advanced mode)
    if (mode == MODE_ADVANCED) {
        fseek(log_file, 0, SEEK_END);
        long size = ftell(log_file);
        if (size > MAX_LOG_SIZE_MB * 1024 * 1024) {
            rotate_log_file();
        }
    }
}

char *get_timestamp() {
    time_t now = time(NULL);
    struct tm *tm_info = localtime(&now);
    char *timestamp = malloc(20);
    strftime(timestamp, 20, "%Y-%m-%d %H:%M:%S", tm_info);
    return timestamp;
}

// Configuration loading
int load_config() {
    FILE *config_file = fopen(CONFIG_FILE, "r");
    if (!config_file) {
        log_event("[CONFIG] Configuration file not found. Using defaults.");
        return 0;
    }
    
    char line[256];
    int extensions_capacity = 10;
    file_extensions = malloc(sizeof(char*) * extensions_capacity);
    extension_count = 0;
    
    while (fgets(line, sizeof(line), config_file)) {
        line[strcspn(line, "\n")] = 0;
        
        if (strncmp(line, "recursive=", 10) == 0) {
            recursive_mode = (strcmp(line + 10, "true") == 0 || strcmp(line + 10, "yes") == 0);
        } else if (strncmp(line, "extension=", 10) == 0) {
            if (extension_count >= extensions_capacity) {
                extensions_capacity *= 2;
                file_extensions = realloc(file_extensions, sizeof(char*) * extensions_capacity);
            }
            file_extensions[extension_count] = strdup(line + 10);
            extension_count++;
        }
    }
    
    fclose(config_file);
    
    char config_msg[256];
    snprintf(config_msg, sizeof(config_msg), 
            "[CONFIG] Loaded: recursive=%s, extensions=%d", 
            recursive_mode ? "yes" : "no", extension_count);
    log_event(config_msg);
    
    return 0;
}

int should_monitor_file(const char *filename) {
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

// ===== BASIC MODE FUNCTIONS =====

int add_watch_basic(const char *path) {
    if (watch_count >= 1024) {
        log_event("[ERROR] Maximum watch limit reached (basic mode)");
        return -1;
    }
    
    int wd = inotify_add_watch(inotify_fd, path,
                              IN_CREATE | IN_DELETE | IN_MODIFY | 
                              IN_MOVE | IN_ATTRIB | IN_OPEN | IN_CLOSE);
    
    if (wd == -1) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg),
                "[ERROR] Failed to add watch for %s: %s", path, strerror(errno));
        log_event(error_msg);
        return -1;
    }
    
    watch_descriptors[watch_count] = wd;
    strncpy(watch_paths[watch_count], path, MAX_PATH_LEN - 1);
    watch_paths[watch_count][MAX_PATH_LEN - 1] = '\0';
    watch_count++;
    
    char success_msg[512];
    snprintf(success_msg, sizeof(success_msg), "[WATCH] Added: %s (wd: %d)", path, wd);
    log_event(success_msg);
    
    return wd;
}

int add_watch_recursive_basic(const char *path) {
    struct stat path_stat;
    if (stat(path, &path_stat) != 0) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "[ERROR] Cannot stat path: %s", path);
        log_event(error_msg);
        return -1;
    }
    
    if (!S_ISDIR(path_stat.st_mode)) {
        log_event("[ERROR] Path is not a directory");
        return -1;
    }
    
    if (add_watch_basic(path) == -1) {
        return -1;
    }
    
    if (!recursive_mode) {
        return 0;
    }
    
    DIR *dir = opendir(path);
    if (!dir) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "[ERROR] Cannot open directory: %s", path);
        log_event(error_msg);
        return -1;
    }
    
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        
        char subpath[MAX_PATH_LEN];
        snprintf(subpath, sizeof(subpath), "%s/%s", path, entry->d_name);
        
        struct stat sub_stat;
        if (stat(subpath, &sub_stat) == 0 && S_ISDIR(sub_stat.st_mode)) {
            add_watch_recursive_basic(subpath);
        }
    }
    
    closedir(dir);
    return 0;
}

void handle_event_basic(struct inotify_event *event, const char *watch_path) {
    stats.total_events++;
    
    if (event->len > 0) {
        char full_path[MAX_PATH_LEN];
        snprintf(full_path, sizeof(full_path), "%s/%s", watch_path, event->name);
        
        if (!should_monitor_file(event->name)) {
            return;
        }
        
        char log_msg[MAX_PATH_LEN + 100];
        
        if (event->mask & IN_CREATE) {
            snprintf(log_msg, sizeof(log_msg), "Created: %s", full_path);
            log_event(log_msg);
            
            if (event->mask & IN_ISDIR && recursive_mode) {
                add_watch_recursive_basic(full_path);
            }
        }
        if (event->mask & IN_DELETE) {
            snprintf(log_msg, sizeof(log_msg), "Deleted: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MODIFY) {
            snprintf(log_msg, sizeof(log_msg), "Modified: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MOVED_FROM) {
            snprintf(log_msg, sizeof(log_msg), "Moved from: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MOVED_TO) {
            snprintf(log_msg, sizeof(log_msg), "Moved to: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_OPEN) {
            snprintf(log_msg, sizeof(log_msg), "Opened: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_CLOSE) {
            snprintf(log_msg, sizeof(log_msg), "Closed: %s", full_path);
            log_event(log_msg);
        }
    }
}

// ===== ENHANCED MODE FUNCTIONS =====

int init_watch_manager() {
    watch_manager.capacity = INITIAL_WATCH_CAPACITY;
    watch_manager.count = 0;
    watch_manager.entries = malloc(sizeof(watch_entry_t) * watch_manager.capacity);
    
    if (!watch_manager.entries) {
        log_event("[ERROR] Failed to allocate watch manager memory");
        return -1;
    }
    
    if (pthread_mutex_init(&watch_manager.mutex, NULL) != 0) {
        log_event("[ERROR] Failed to initialize watch manager mutex");
        free(watch_manager.entries);
        return -1;
    }
    
    log_event("[INFO] Watch manager initialized");
    return 0;
}

void cleanup_watch_manager() {
    if (watch_manager.entries) {
        pthread_mutex_lock(&watch_manager.mutex);
        free(watch_manager.entries);
        watch_manager.entries = NULL;
        watch_manager.count = 0;
        watch_manager.capacity = 0;
        pthread_mutex_unlock(&watch_manager.mutex);
        pthread_mutex_destroy(&watch_manager.mutex);
    }
}

int add_watch_dynamic(const char *path) {
    pthread_mutex_lock(&watch_manager.mutex);
    
    if (watch_manager.count >= watch_manager.capacity) {
        size_t new_capacity = watch_manager.capacity * WATCH_GROWTH_FACTOR;
        watch_entry_t *new_entries = realloc(watch_manager.entries,
                                           sizeof(watch_entry_t) * new_capacity);
        
        if (!new_entries) {
            pthread_mutex_unlock(&watch_manager.mutex);
            log_event("[ERROR] Failed to expand watch manager capacity");
            stats.watch_limit_hits++;
            return -1;
        }
        
        watch_manager.entries = new_entries;
        watch_manager.capacity = new_capacity;
        stats.memory_reallocations++;
        
        char msg[256];
        snprintf(msg, sizeof(msg), "[INFO] Watch manager expanded to %zu entries",
                new_capacity);
        log_event(msg);
    }
    
    int wd = inotify_add_watch(inotify_fd, path,
                              IN_CREATE | IN_DELETE | IN_MODIFY |
                              IN_MOVE | IN_ATTRIB | IN_OPEN | IN_CLOSE);
    
    if (wd == -1) {
        pthread_mutex_unlock(&watch_manager.mutex);
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg),
                "[ERROR] Failed to add watch for %s: %s", path, strerror(errno));
        log_event(error_msg);
        return -1;
    }
    
    watch_entry_t *entry = &watch_manager.entries[watch_manager.count];
    entry->wd = wd;
    strncpy(entry->path, path, MAX_PATH_LEN - 1);
    entry->path[MAX_PATH_LEN - 1] = '\0';
    entry->added_time = time(NULL);
    entry->event_count = 0;
    
    watch_manager.count++;
    
    pthread_mutex_unlock(&watch_manager.mutex);
    
    char success_msg[512];
    snprintf(success_msg, sizeof(success_msg), "[WATCH] Added: %s (wd: %d)", path, wd);
    log_event(success_msg);
    
    return wd;
}

watch_entry_t *find_watch_by_wd(int wd) {
    pthread_mutex_lock(&watch_manager.mutex);
    
    for (size_t i = 0; i < watch_manager.count; i++) {
        if (watch_manager.entries[i].wd == wd) {
            pthread_mutex_unlock(&watch_manager.mutex);
            return &watch_manager.entries[i];
        }
    }
    
    pthread_mutex_unlock(&watch_manager.mutex);
    return NULL;
}

int add_watch_recursive_enhanced(const char *path) {
    struct stat path_stat;
    if (stat(path, &path_stat) != 0) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "[ERROR] Cannot stat path: %s", path);
        log_event(error_msg);
        return -1;
    }
    
    if (!S_ISDIR(path_stat.st_mode)) {
        log_event("[ERROR] Path is not a directory");
        return -1;
    }
    
    if (add_watch_dynamic(path) == -1) {
        return -1;
    }
    
    if (!recursive_mode) {
        return 0;
    }
    
    DIR *dir = opendir(path);
    if (!dir) {
        char error_msg[512];
        snprintf(error_msg, sizeof(error_msg), "[ERROR] Cannot open directory: %s", path);
        log_event(error_msg);
        return -1;
    }
    
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        if (strcmp(entry->d_name, ".") == 0 || strcmp(entry->d_name, "..") == 0) {
            continue;
        }
        
        char subpath[MAX_PATH_LEN];
        snprintf(subpath, sizeof(subpath), "%s/%s", path, entry->d_name);
        
        struct stat sub_stat;
        if (stat(subpath, &sub_stat) == 0 && S_ISDIR(sub_stat.st_mode)) {
            add_watch_recursive_enhanced(subpath);
        }
    }
    
    closedir(dir);
    return 0;
}

void handle_event_enhanced(struct inotify_event *event) {
    watch_entry_t *watch_entry = find_watch_by_wd(event->wd);
    if (!watch_entry) {
        log_event("[WARN] Event from unknown watch descriptor");
        return;
    }
    
    watch_entry->event_count++;
    stats.total_events++;
    
    if (watch_entry->event_count > stats.max_events_per_path) {
        stats.max_events_per_path = watch_entry->event_count;
        strncpy(stats.most_active_path, watch_entry->path, MAX_PATH_LEN - 1);
    }
    
    if (event->len > 0) {
        char full_path[MAX_PATH_LEN];
        snprintf(full_path, sizeof(full_path), "%s/%s", watch_entry->path, event->name);
        
        if (!should_monitor_file(event->name)) {
            return;
        }
        
        char log_msg[MAX_PATH_LEN + 100];
        
        if (event->mask & IN_CREATE) {
            snprintf(log_msg, sizeof(log_msg), "Created: %s", full_path);
            log_event(log_msg);
            
            if (event->mask & IN_ISDIR && recursive_mode) {
                add_watch_recursive_enhanced(full_path);
            }
        }
        if (event->mask & IN_DELETE) {
            snprintf(log_msg, sizeof(log_msg), "Deleted: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MODIFY) {
            snprintf(log_msg, sizeof(log_msg), "Modified: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MOVED_FROM) {
            snprintf(log_msg, sizeof(log_msg), "Moved from: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MOVED_TO) {
            snprintf(log_msg, sizeof(log_msg), "Moved to: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_OPEN) {
            snprintf(log_msg, sizeof(log_msg), "Opened: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_CLOSE) {
            snprintf(log_msg, sizeof(log_msg), "Closed: %s", full_path);
            log_event(log_msg);
        }
    }
}

// ===== ADVANCED MODE FUNCTIONS =====

char* calculate_file_hash(const char *filepath) {
    FILE *file = fopen(filepath, "rb");
    if (!file) return NULL;
    
    SHA256_CTX sha256;
    SHA256_Init(&sha256);
    
    unsigned char buffer[8192];
    int bytes;
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
    hex_string[HASH_SIZE - 1] = '\0';
    
    return hex_string;
}

int check_file_changed(const char *filepath) {
    if (!enable_checksum) return 1;
    
    pthread_mutex_lock(&hash_mutex);
    
    char *new_hash = calculate_file_hash(filepath);
    if (!new_hash) {
        pthread_mutex_unlock(&hash_mutex);
        return 1;
    }
    
    for (int i = 0; i < hash_count; i++) {
        if (strcmp(file_hashes[i].filepath, filepath) == 0) {
            int changed = (strcmp(file_hashes[i].hash, new_hash) != 0);
            if (changed) {
                strncpy(file_hashes[i].hash, new_hash, HASH_SIZE - 1);
                file_hashes[i].last_modified = time(NULL);
            }
            free(new_hash);
            pthread_mutex_unlock(&hash_mutex);
            return changed;
        }
    }
    
    if (hash_count >= hash_capacity) {
        hash_capacity = (hash_capacity == 0) ? 100 : hash_capacity * 2;
        file_hashes = realloc(file_hashes, sizeof(file_hash_info_t) * hash_capacity);
    }
    
    if (file_hashes) {
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
    return 1;
}

void rotate_log_file() {
    if (!log_file) return;
    
    fclose(log_file);
    
    char old_name[MAX_PATH_LEN];
    char new_name[MAX_PATH_LEN];
    
    for (int i = MAX_LOG_FILES - 1; i > 0; i--) {
        snprintf(old_name, sizeof(old_name), "%s.%d", LOG_FILE, i - 1);
        snprintf(new_name, sizeof(new_name), "%s.%d", LOG_FILE, i);
        
        if (access(old_name, F_OK) == 0) {
            if (i == MAX_LOG_FILES - 1) {
                unlink(old_name);
            } else {
                rename(old_name, new_name);
            }
        }
    }
    
    snprintf(new_name, sizeof(new_name), "%s.0", LOG_FILE);
    rename(LOG_FILE, new_name);
    
    if (enable_compression) {
        compress_old_log(new_name);
    }
    
    log_file = fopen(LOG_FILE, "a");
    if (log_file) {
        log_event("[INFO] Log file rotated successfully");
    }
}

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
    unlink(filename);
    
    char msg[512];
    snprintf(msg, sizeof(msg), "[INFO] Compressed log file: %s", gz_filename);
    log_event(msg);
}

void handle_event_advanced(struct inotify_event *event, const char *watch_path) {
    stats.total_events++;
    
    if (event->len > 0) {
        char full_path[MAX_PATH_LEN];
        snprintf(full_path, sizeof(full_path), "%s/%s", watch_path, event->name);
        
        if (!should_monitor_file(event->name)) {
            return;
        }
        
        char log_msg[MAX_PATH_LEN + 100];
        
        if (event->mask & IN_CREATE) {
            snprintf(log_msg, sizeof(log_msg), "Created: %s", full_path);
            log_event(log_msg);
            
            if (event->mask & IN_ISDIR && recursive_mode) {
                add_watch_recursive_basic(full_path);
            }
        }
        if (event->mask & IN_DELETE) {
            snprintf(log_msg, sizeof(log_msg), "Deleted: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MODIFY) {
            if (check_file_changed(full_path)) {
                snprintf(log_msg, sizeof(log_msg), "Modified (checksum changed): %s", full_path);
                log_event(log_msg);
            }
        }
        if (event->mask & IN_MOVED_FROM) {
            snprintf(log_msg, sizeof(log_msg), "Moved from: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_MOVED_TO) {
            snprintf(log_msg, sizeof(log_msg), "Moved to: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_OPEN) {
            snprintf(log_msg, sizeof(log_msg), "Opened: %s", full_path);
            log_event(log_msg);
        }
        if (event->mask & IN_CLOSE) {
            snprintf(log_msg, sizeof(log_msg), "Closed: %s", full_path);
            log_event(log_msg);
        }
    }
}

// ===== STATISTICS FUNCTIONS =====

void update_stats() {
    stats.last_update = time(NULL);
    
    FILE *status = fopen("/proc/self/status", "r");
    if (status) {
        char line[256];
        while (fgets(line, sizeof(line), status)) {
            if (strncmp(line, "VmRSS:", 6) == 0) {
                sscanf(line, "VmRSS: %lu kB", &stats.memory_usage_kb);
                break;
            }
        }
        fclose(status);
    }
    
    struct rusage usage;
    if (getrusage(RUSAGE_SELF, &usage) == 0) {
        long total_time = usage.ru_utime.tv_sec + usage.ru_stime.tv_sec;
        long elapsed_time = stats.last_update - stats.start_time;
        if (elapsed_time > 0) {
            stats.cpu_usage_percent = (double)total_time / elapsed_time * 100.0;
            stats.events_per_second = stats.total_events / elapsed_time;
        }
    }
}

void save_stats() {
    update_stats();
    
    json_object *stats_json = json_object_new_object();
    json_object_object_add(stats_json, "mode",
                          json_object_new_string(mode == MODE_BASIC ? "basic" :
                                                mode == MODE_ADVANCED ? "advanced" : "enhanced"));
    json_object_object_add(stats_json, "total_events",
                          json_object_new_int64(stats.total_events));
    
    if (mode == MODE_ENHANCED) {
        json_object_object_add(stats_json, "active_watches",
                              json_object_new_int64(watch_manager.count));
        json_object_object_add(stats_json, "watch_capacity",
                              json_object_new_int64(watch_manager.capacity));
        json_object_object_add(stats_json, "memory_reallocations",
                              json_object_new_int64(stats.memory_reallocations));
        json_object_object_add(stats_json, "most_active_path",
                              json_object_new_string(stats.most_active_path));
    } else {
        json_object_object_add(stats_json, "active_watches",
                              json_object_new_int64(watch_count));
    }
    
    json_object_object_add(stats_json, "memory_usage_kb",
                          json_object_new_int64(stats.memory_usage_kb));
    json_object_object_add(stats_json, "cpu_usage_percent",
                          json_object_new_double(stats.cpu_usage_percent));
    json_object_object_add(stats_json, "uptime_seconds",
                          json_object_new_int64(time(NULL) - stats.start_time));
    
    if (json_object_to_file(STATS_FILE, stats_json) != 0) {
        log_event("[ERROR] Failed to save statistics");
    }
    
    json_object_put(stats_json);
}

void* stats_thread_func(void* arg) {
    while (running) {
        sleep(30);
        if (running) {
            save_stats();
        }
    }
    return NULL;
}

// ===== MAIN PROGRAM =====

void print_usage(const char *program_name) {
    printf("Unified File Monitor v2.0\n");
    printf("Usage: %s [OPTIONS] <directory_path>\n\n", program_name);
    printf("Options:\n");
    printf("  --mode=MODE          Monitor mode: basic, advanced, or enhanced (default: basic)\n");
    printf("  -h, --help           Show this help message\n");
    printf("  --version            Show version information\n");
    printf("\nModes:\n");
    printf("  basic     - Simple file monitoring\n");
    printf("  advanced  - Monitoring with checksums and log compression\n");
    printf("  enhanced  - Monitoring with dynamic scaling (no watch limits)\n");
    printf("\nSignals:\n");
    printf("  SIGUSR1      - Show real-time statistics\n");
    printf("  SIGINT/TERM  - Graceful shutdown\n");
}

int main(int argc, char **argv) {
    setlocale(LC_ALL, "en_US.UTF-8");
    
    char *watch_path = NULL;
    
    // Parse arguments
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-h") == 0 || strcmp(argv[i], "--help") == 0) {
            print_usage(argv[0]);
            exit(0);
        } else if (strcmp(argv[i], "--version") == 0) {
            printf("Unified File Monitor v2.0\n");
            exit(0);
        } else if (strncmp(argv[i], "--mode=", 7) == 0) {
            char *mode_str = argv[i] + 7;
            if (strcmp(mode_str, "basic") == 0) {
                mode = MODE_BASIC;
            } else if (strcmp(mode_str, "advanced") == 0) {
                mode = MODE_ADVANCED;
            } else if (strcmp(mode_str, "enhanced") == 0) {
                mode = MODE_ENHANCED;
            } else {
                fprintf(stderr, "Error: Invalid mode '%s'\n", mode_str);
                print_usage(argv[0]);
                exit(1);
            }
        } else if (argv[i][0] != '-') {
            watch_path = argv[i];
        }
    }
    
    if (!watch_path) {
        fprintf(stderr, "Error: No directory path specified\n");
        print_usage(argv[0]);
        exit(1);
    }
    
    // Initialize statistics
    stats.start_time = time(NULL);
    strcpy(stats.most_active_path, "none");
    
    // Signal handlers
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGUSR1, signal_handler);
    
    // Open log file
    log_file = fopen(LOG_FILE, "a");
    if (!log_file) {
        fprintf(stderr, "[ERROR] Cannot open log file: %s\n", LOG_FILE);
        exit(1);
    }
    
    char start_msg[512];
    snprintf(start_msg, sizeof(start_msg), "[START] File Monitor starting in %s mode...",
            mode == MODE_BASIC ? "basic" : mode == MODE_ADVANCED ? "advanced" : "enhanced");
    log_event(start_msg);
    
    // Load configuration
    if (load_config() != 0) {
        log_event("[ERROR] Failed to load configuration");
        cleanup_and_exit(1);
    }
    
    // Initialize mode-specific structures
    if (mode == MODE_ENHANCED) {
        if (init_watch_manager() != 0) {
            log_event("[ERROR] Failed to initialize watch manager");
            cleanup_and_exit(1);
        }
    }
    
    // Initialize inotify
    inotify_fd = inotify_init1(IN_CLOEXEC);
    if (inotify_fd < 0) {
        log_event("[ERROR] Failed to initialize inotify");
        cleanup_and_exit(1);
    }
    
    // Start statistics thread
    if (pthread_create(&stats_thread, NULL, stats_thread_func, NULL) != 0) {
        log_event("[WARN] Failed to create statistics thread");
    }
    
    // Add initial watches
    int result;
    if (mode == MODE_ENHANCED) {
        result = add_watch_recursive_enhanced(watch_path);
    } else {
        result = add_watch_recursive_basic(watch_path);
    }
    
    if (result == -1) {
        cleanup_and_exit(1);
    }
    
    snprintf(start_msg, sizeof(start_msg),
            "[START] Monitoring started: %s (mode: %s, recursive: %s)",
            watch_path,
            mode == MODE_BASIC ? "basic" : mode == MODE_ADVANCED ? "advanced" : "enhanced",
            recursive_mode ? "yes" : "no");
    log_event(start_msg);
    
    // Main event loop
    char buffer[BUF_LEN];
    log_event("[INFO] Entering main event loop");
    
    while (running) {
        int length = read(inotify_fd, buffer, BUF_LEN);
        
        if (length < 0) {
            if (errno == EINTR) continue;
            log_event("[ERROR] Read from inotify failed");
            break;
        }
        
        if (length == 0) continue;
        
        int offset = 0;
        while (offset < length) {
            struct inotify_event *event = (struct inotify_event *)(buffer + offset);
            
            if (mode == MODE_ENHANCED) {
                handle_event_enhanced(event);
            } else if (mode == MODE_ADVANCED) {
                // Find watch path for advanced mode
                const char *path = NULL;
                for (int i = 0; i < watch_count; i++) {
                    if (watch_descriptors[i] == event->wd) {
                        path = watch_paths[i];
                        break;
                    }
                }
                if (path) {
                    handle_event_advanced(event, path);
                }
            } else {
                // Basic mode
                const char *path = NULL;
                for (int i = 0; i < watch_count; i++) {
                    if (watch_descriptors[i] == event->wd) {
                        path = watch_paths[i];
                        break;
                    }
                }
                if (path) {
                    handle_event_basic(event, path);
                }
            }
            
            offset += EVENT_SIZE + event->len;
        }
    }
    
    cleanup_and_exit(0);
    return 0;
}
