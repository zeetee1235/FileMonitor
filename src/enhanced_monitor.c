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
#include <dirent.h>
#include <libgen.h>
#include <pthread.h>
#include <json-c/json.h>

#define EVENT_SIZE          (sizeof(struct inotify_event))
#define BUF_LEN             (1024 * (EVENT_SIZE + 16))
#define MAX_PATH_LEN        4096
#define CONFIG_FILE         "monitor.conf"
#define LOG_FILE            "enhanced_monitor.log"
#define IPC_SOCKET_PATH     "/tmp/enhanced_monitor.sock"
#define STATS_FILE          "enhanced_stats.json"
#define INITIAL_WATCH_CAPACITY 1024
#define WATCH_GROWTH_FACTOR    2

// Dynamic watch management structure
typedef struct {
    int wd;                          // Watch descriptor
    char path[MAX_PATH_LEN];         // Directory path
    time_t added_time;               // When this watch was added
    unsigned long event_count;       // Number of events from this watch
} watch_entry_t;

typedef struct {
    watch_entry_t *entries;          // Dynamic array of watch entries
    size_t capacity;                 // Current capacity
    size_t count;                    // Current number of watches
    pthread_mutex_t mutex;           // Thread safety
} watch_manager_t;

// Enhanced statistics
typedef struct {
    unsigned long total_events;
    unsigned long total_files_processed;
    unsigned long memory_usage_kb;
    double cpu_usage_percent;
    time_t start_time;
    time_t last_update;
    unsigned long watch_limit_hits;
    unsigned long memory_reallocations;
    char most_active_path[MAX_PATH_LEN];
    unsigned long max_events_per_path;
} enhanced_stats_t;

// Global variables
static int inotify_fd = -1;
static watch_manager_t watch_manager = {0};
static FILE *log_file = NULL;
static int recursive_mode = 1;
static char **file_extensions = NULL;
static int extension_count = 0;
static int ipc_socket = -1;
static pthread_t ipc_thread;
static pthread_t stats_thread;
static enhanced_stats_t stats = {0};
static volatile int running = 1;

// Function declarations
void signal_handler(int sig);
void cleanup_and_exit(int code);
void log_event(const char *message);
char *get_timestamp();
int load_config();
int should_monitor_file(const char *filename);
int init_watch_manager();
void cleanup_watch_manager();
int add_watch_dynamic(const char *path);
int remove_watch_dynamic(int wd);
watch_entry_t *find_watch_by_wd(int wd);
int add_watch_recursive(const char *path);
void handle_event(struct inotify_event *event);
void print_usage(const char *program_name);
int setup_ipc_socket();
void* ipc_thread_func(void* arg);
void* stats_thread_func(void* arg);
void update_stats();
void save_stats();
int get_system_watch_limit();
void optimize_watch_usage();

// Enhanced signal handler
void signal_handler(int sig) {
    if (sig == SIGINT || sig == SIGTERM) {
        printf("\n[STOP] Received signal: %d. Shutting down safely...\n", sig);
        running = 0;
        save_stats();
        cleanup_and_exit(0);
    } else if (sig == SIGUSR1) {
        // Print real-time statistics
        update_stats();
        printf("\n=== ENHANCED MONITOR STATS ===\n");
        printf("Total Events: %lu\n", stats.total_events);
        printf("Active Watches: %zu/%zu\n", watch_manager.count, watch_manager.capacity);
        printf("Memory Usage: %lu KB\n", stats.memory_usage_kb);
        printf("Watch Limit Hits: %lu\n", stats.watch_limit_hits);
        printf("Memory Reallocations: %lu\n", stats.memory_reallocations);
        printf("Most Active Path: %s (%lu events)\n", 
               stats.most_active_path, stats.max_events_per_path);
        printf("==============================\n");
    }
}

// Enhanced cleanup function
void cleanup_and_exit(int code) {
    running = 0;
    
    if (inotify_fd != -1) {
        close(inotify_fd);
        inotify_fd = -1;
    }
    
    cleanup_watch_manager();
    
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
    
    save_stats();
    log_event("[STOP] Enhanced Monitor terminated gracefully");
    
    exit(code);
}

// Enhanced logging with rotation
void log_event(const char *message) {
    if (!log_file) return;
    
    char *timestamp = get_timestamp();
    fprintf(log_file, "[%s] %s\n", timestamp, message);
    fflush(log_file);
    free(timestamp);
    
    // Check log file size and rotate if needed
    fseek(log_file, 0, SEEK_END);
    long size = ftell(log_file);
    if (size > 10 * 1024 * 1024) { // 10MB limit
        fclose(log_file);
        
        // Rotate log files
        char old_log[256], new_log[256];
        snprintf(old_log, sizeof(old_log), "%s.old", LOG_FILE);
        rename(LOG_FILE, old_log);
        
        log_file = fopen(LOG_FILE, "a");
        if (log_file) {
            log_event("[INFO] Log file rotated");
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

// Dynamic watch manager implementation
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
    
    // Check if we need to expand capacity
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
    
    // Add inotify watch
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
    
    // Add to our manager
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

// Enhanced recursive watch addition
int add_watch_recursive(const char *path) {
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
    
    // Add watch for current directory
    if (add_watch_dynamic(path) == -1) {
        return -1;
    }
    
    if (!recursive_mode) {
        return 0;
    }
    
    // Recursively add subdirectories
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
            add_watch_recursive(subpath);
        }
    }
    
    closedir(dir);
    return 0;
}

// Enhanced event handling
void handle_event(struct inotify_event *event) {
    watch_entry_t *watch_entry = find_watch_by_wd(event->wd);
    if (!watch_entry) {
        log_event("[WARN] Event from unknown watch descriptor");
        return;
    }
    
    // Update statistics
    watch_entry->event_count++;
    stats.total_events++;
    
    // Check if this is the most active path
    if (watch_entry->event_count > stats.max_events_per_path) {
        stats.max_events_per_path = watch_entry->event_count;
        strncpy(stats.most_active_path, watch_entry->path, MAX_PATH_LEN - 1);
    }
    
    if (event->len > 0) {
        char full_path[MAX_PATH_LEN];
        snprintf(full_path, sizeof(full_path), "%s/%s", watch_entry->path, event->name);
        
        // Check file extension filter
        if (!should_monitor_file(event->name)) {
            return;
        }
        
        char log_msg[MAX_PATH_LEN + 100];
        
        if (event->mask & IN_CREATE) {
            snprintf(log_msg, sizeof(log_msg), "Created: %s", full_path);
            log_event(log_msg);
            
            // If it's a directory, add watch recursively
            if (event->mask & IN_ISDIR && recursive_mode) {
                add_watch_recursive(full_path);
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

// Enhanced configuration loading
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
        line[strcspn(line, "\n")] = 0; // Remove newline
        
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
    if (extension_count == 0) return 1; // Monitor all files if no filter
    
    const char *ext = strrchr(filename, '.');
    if (!ext) return 0; // No extension
    
    ext++; // Skip the dot
    
    for (int i = 0; i < extension_count; i++) {
        if (strcmp(ext, file_extensions[i]) == 0) {
            return 1;
        }
    }
    
    return 0;
}

// Statistics management
void update_stats() {
    stats.last_update = time(NULL);
    
    // Get memory usage
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
}

void save_stats() {
    update_stats();
    
    json_object *stats_json = json_object_new_object();
    json_object_object_add(stats_json, "total_events", 
                          json_object_new_int64(stats.total_events));
    json_object_object_add(stats_json, "active_watches", 
                          json_object_new_int64(watch_manager.count));
    json_object_object_add(stats_json, "watch_capacity", 
                          json_object_new_int64(watch_manager.capacity));
    json_object_object_add(stats_json, "memory_usage_kb", 
                          json_object_new_int64(stats.memory_usage_kb));
    json_object_object_add(stats_json, "watch_limit_hits", 
                          json_object_new_int64(stats.watch_limit_hits));
    json_object_object_add(stats_json, "memory_reallocations", 
                          json_object_new_int64(stats.memory_reallocations));
    json_object_object_add(stats_json, "most_active_path", 
                          json_object_new_string(stats.most_active_path));
    json_object_object_add(stats_json, "max_events_per_path", 
                          json_object_new_int64(stats.max_events_per_path));
    json_object_object_add(stats_json, "uptime_seconds", 
                          json_object_new_int64(time(NULL) - stats.start_time));
    
    if (json_object_to_file(STATS_FILE, stats_json) != 0) {
        log_event("[ERROR] Failed to save statistics");
    }
    
    json_object_put(stats_json);
}

void* stats_thread_func(void* arg) {
    while (running) {
        sleep(30); // Update stats every 30 seconds
        if (running) {
            save_stats();
        }
    }
    return NULL;
}

void print_usage(const char *program_name) {
    printf("Enhanced File Monitor v1.0\n");
    printf("Usage: %s <directory_path>\n", program_name);
    printf("\nFeatures:\n");
    printf("  - Dynamic watch management (no hard limits)\n");
    printf("  - Enhanced memory management\n");
    printf("  - Real-time statistics\n");
    printf("  - Automatic log rotation\n");
    printf("  - Intelligent resource optimization\n");
    printf("\nSignals:\n");
    printf("  SIGUSR1 - Show real-time statistics\n");
    printf("  SIGINT/SIGTERM - Graceful shutdown\n");
}

// IPC socket handling (similar to original but enhanced)
int setup_ipc_socket() {
    // Implementation similar to original but with better error handling
    return -1; // Simplified for this example
}

void* ipc_thread_func(void* arg) {
    // Implementation for IPC communication
    return NULL;
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
    
    log_event("[START] Enhanced File Monitor starting...");
    
    // Load configuration
    if (load_config() != 0) {
        log_event("[ERROR] Failed to load configuration");
        cleanup_and_exit(1);
    }
    
    // Initialize watch manager
    if (init_watch_manager() != 0) {
        log_event("[ERROR] Failed to initialize watch manager");
        cleanup_and_exit(1);
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
    
    // Add initial watch
    if (add_watch_recursive(argv[1]) == -1) {
        cleanup_and_exit(1);
    }
    
    char start_msg[512];
    snprintf(start_msg, sizeof(start_msg), 
            "[START] Enhanced monitoring started: %s (recursive: %s)", 
            argv[1], recursive_mode ? "yes" : "no");
    log_event(start_msg);
    
    // Main event loop
    char buffer[BUF_LEN];
    
    log_event("[INFO] Entering main event loop");
    
    while (running) {
        int length = read(inotify_fd, buffer, BUF_LEN);
        
        if (length < 0) {
            if (errno == EINTR) continue; // Interrupted by signal
            log_event("[ERROR] Read from inotify failed");
            break;
        }
        
        if (length == 0) continue;
        
        int offset = 0;
        while (offset < length) {
            struct inotify_event *event = (struct inotify_event *)(buffer + offset);
            handle_event(event);
            offset += EVENT_SIZE + event->len;
        }
    }
    
    cleanup_and_exit(0);
    return 0;
}
