#include <iostream>
#include <filesystem>
#include <vector>
#include <string>
#include <thread>
#include <mutex>
#include <atomic>
#include <chrono>
#include <sstream>
#include <algorithm>
#include <fstream>

namespace fs = std::filesystem;

// Structure to hold conversion state
struct ConversionState {
    std::atomic<int> total_files{0};
    std::atomic<int> processed{0};
    std::atomic<int> errors{0};
    std::vector<std::string> error_messages;
    std::mutex log_mutex;
    bool stop_requested{false};
};

// Define folder names
const std::string old_wav_folder_name = "_old_wav_check";
const std::string midi_folder_name = "_MIDI";
const std::string arturia_folder_name = "_Arturia Banks";
const std::string serum_folder_name = "_Serum Banks";
const std::string vital_folder_name = "_Vital Banks";
const std::string ableton_folder_name = "_Ableton Banks";
const std::string natinst_folder_name = "_NI Banks";
const std::string unrecognized_folder_name = "_Unrecognized";
const std::string documentation_folder_name = "_Documentation";

// Define file extension categories
const std::vector<std::string> lossless_extensions = {".wav", ".aiff", ".aif"};
const std::vector<std::string> midi_extensions = {".mid", ".midi"};
const std::vector<std::string> arturia_extensions = {".labx", ".jupx", ".prox", ".junx", ".minix", ".pgtx"};
const std::vector<std::string> serum_extensions = {".fxp"};
const std::vector<std::string> vital_extensions = {".vitalbank", ".vital", ".vitalskin"};
const std::vector<std::string> ableton_extensions = {".abl", ".ablbundle", ".adg", ".agr", ".adv", ".alc", ".alp", ".als", ".ams", ".amxd", ".ask", ".cfg", ".xmp"};
const std::vector<std::string> natinst_extensions = {".nmsv", ".nksf", ".bnk", ".ksd", ".ngrr"};
const std::vector<std::string> analysis_extensions = {".asd", ".reapeaks"};
const std::vector<std::string> unrecognized_extensions = {".dat", ""};
const std::vector<std::string> documentation_extensions = {".html", ".docx", ".doc", ".pdf", ".jpg", ".jpeg", ".png", ".txt", ".rtf", ".xml", ".asc", ".msg", ".wpd", ".wps", ".url"};

// Helper function to check if an extension belongs to a category
bool has_extension(const std::string& extension, const std::vector<std::string>& extensions) {
    return std::find(extensions.begin(), extensions.end(), extension) != extensions.end();
}

// Function to execute shell commands with timeout
bool execute_command(const std::string& cmd, int timeout_seconds = 30) {
    auto start = std::chrono::steady_clock::now();
    std::string full_cmd = cmd + " 2>&1";
    FILE* pipe = popen(full_cmd.c_str(), "r");
    if (!pipe) return false;

    char buffer[128];
    std::ostringstream output;
    while (std::chrono::steady_clock::now() - start < std::chrono::seconds(timeout_seconds)) {
        if (fgets(buffer, sizeof(buffer), pipe) != nullptr) {
            output << buffer;
        } else if (feof(pipe)) {
            break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }

    if (std::chrono::steady_clock::now() - start >= std::chrono::seconds(timeout_seconds)) {
        pclose(pipe);
        return false;
    }

    return pclose(pipe) == 0;
}

// Conversion function WAV -> FLAC
bool convert_file(const fs::path& input_path, const fs::path& output_path, ConversionState& state) {
    try {
        std::string quoted_input = "\"" + input_path.string() + "\"";
        std::string quoted_output = "\"" + output_path.string() + "\"";
        
        std::string cmd = "ffmpeg -v error -y -i " + quoted_input + 
                         " -c:a flac -compression_level 12 " + quoted_output;

        if (!execute_command(cmd)) {
            std::lock_guard<std::mutex> lock(state.log_mutex);
            state.error_messages.push_back("Conversion failed: " + input_path.string());
            return false;
        }
        return true;
    }
    catch (...) {
        std::lock_guard<std::mutex> lock(state.log_mutex);
        state.error_messages.push_back("Exception with: " + input_path.string());
        return false;
    }
}

// Function to move files while preserving directory structure relative to the entry point
void move_file_with_relative_structure(const fs::path& file, const fs::path& base_path, const fs::path& target_folder) {
    fs::path relative_path = fs::relative(file.parent_path(), base_path);

    // Check if the file is already in the target folder
    if (relative_path.string().find(target_folder.filename().string()) != 0) {
        fs::path target_path = target_folder / relative_path;
        fs::create_directories(target_path);
        fs::rename(file, target_path / file.filename());
    }
}

// Updated worker thread function
void process_batch(const std::vector<fs::path>& batch, 
                  ConversionState& state, 
                  bool delete_original, 
                  const fs::path& base_path,
                  const fs::path& old_wav_folder, 
                  const fs::path& midi_folder,
                  const fs::path& arturia_folder,
                  const fs::path& serum_folder,
                  const fs::path& vital_folder,
                  const fs::path& ableton_folder,
                  const fs::path& natinst_folder,
                  const fs::path& unrecognized_folder,
                  const fs::path& documentation_folder) {
    for (const auto& file : batch) {
        if (state.stop_requested) return;

        std::string extension = file.extension().string();
        std::transform(extension.begin(), extension.end(), extension.begin(), ::tolower);

        if (file.filename().string().rfind("._", 0) == 0 || file.filename() == ".DS_Store") {
            try { fs::remove(file); }
            catch (...) {
                std::lock_guard<std::mutex> lock(state.log_mutex);
                state.error_messages.push_back("Failed to delete hidden file: " + file.string());
            }
            continue;
        }

        if (has_extension(extension, analysis_extensions)) {
            try { fs::remove(file); }
            catch (...) {
                std::lock_guard<std::mutex> lock(state.log_mutex);
                state.error_messages.push_back("Failed to delete analysis file: " + file.string());
            }
            continue;
        }

        if (has_extension(extension, unrecognized_extensions)) {
            move_file_with_relative_structure(file, base_path, unrecognized_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
            continue;
        }

        if (has_extension(extension, documentation_extensions)) {
            move_file_with_relative_structure(file, base_path, documentation_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
            continue;
        }

        if (has_extension(extension, lossless_extensions)) {
            fs::path output_path = file;
            output_path.replace_extension(".flac");

            if (convert_file(file, output_path, state)) {
                if (delete_original) {
                    try { fs::remove(file); }
                    catch (...) {
                        std::lock_guard<std::mutex> lock(state.log_mutex);
                        state.error_messages.push_back("Delete failed: " + file.string());
                    }
                } else {
                    move_file_with_relative_structure(file, base_path, old_wav_folder);
                }
                state.processed.fetch_add(1, std::memory_order_relaxed);
            } else {
                state.errors.fetch_add(1, std::memory_order_relaxed);
            }
        } else if (has_extension(extension, midi_extensions)) {
            move_file_with_relative_structure(file, base_path, midi_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
        } else if (has_extension(extension, arturia_extensions)) {
            move_file_with_relative_structure(file, base_path, arturia_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
        } else if (has_extension(extension, serum_extensions)) {
            move_file_with_relative_structure(file, base_path, serum_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
        } else if (has_extension(extension, vital_extensions)) {
            move_file_with_relative_structure(file, base_path, vital_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
        } else if (has_extension(extension, ableton_extensions)) {
            move_file_with_relative_structure(file, base_path, ableton_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
        } else if (has_extension(extension, natinst_extensions)) {
            move_file_with_relative_structure(file, base_path, natinst_folder);
            state.processed.fetch_add(1, std::memory_order_relaxed);
        }
    }
}

// Progress bar function
void display_progress(ConversionState& state) {
    const int bar_width = 50;
    while (state.processed < state.total_files && !state.stop_requested) {
        float progress = static_cast<float>(state.processed.load(std::memory_order_relaxed)) / state.total_files;
        int pos = bar_width * progress;
        
        std::cout << "[";
        for (int i = 0; i < bar_width; ++i) {
            if (i < pos) std::cout << "=";
            else if (i == pos) std::cout << ">";
            else std::cout << " ";
        }
        std::cout << "] " << int(progress * 100.0) << "% "
                << state.processed.load(std::memory_order_relaxed) << "/" << state.total_files << "\r";
        std::cout.flush();
        
        std::this_thread::sleep_for(std::chrono::milliseconds(200));
    }
    std::cout << std::endl; // Ensure the progress bar ends cleanly
}

// Function to delete empty folders
void delete_empty_folders(const fs::path& root_path, std::vector<fs::path>& deleted_folders) {
    for (const auto& entry : fs::directory_iterator(root_path)) {
        if (fs::is_directory(entry)) {
            delete_empty_folders(entry, deleted_folders);
            if (fs::is_empty(entry)) {
                try {
                    fs::remove(entry);
                    deleted_folders.push_back(entry);
                } catch (const std::exception& e) {
                    std::cerr << "Error deleting folder " << entry << ": " << e.what() << "\n";
                }
            }
        }
    }
}

int main() {
    // Verify ffmpeg installation
    if (system("ffmpeg -version > NUL 2>&1") != 0) { // Suppress output
        std::cerr << "FFmpeg not installed or not present in PATH!\n";
        std::cerr << "Please copy ffmpeg.exe in [" << fs::current_path() << "] or add it to the PATH...\n";
        std::cout << "Press Enter to exit...";
        std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
        return 1;
    }

    // Initial configuration
    ConversionState state;
    fs::path root_path = fs::current_path();
    unsigned int thread_count = std::max(std::thread::hardware_concurrency(), 1u);
    bool delete_original = false;

    // User interface for directory path
    std::cout << "Samples main folder (default is [" << root_path << "]): ";
    std::string user_input;
    std::getline(std::cin, user_input);
    
    if (!user_input.empty()) {
        root_path = fs::path(user_input);
        if (!fs::exists(root_path)) {
            std::cerr << "Invalid path! [" << root_path << "]\n";
            std::cout << "Press Enter to exit...";
            std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
            return 1;
        }
    }

    // Default: do not delete original files
    std::cout << "Delete original files after conversion? (y/[n]): ";
    char response;
    std::cin.get(response);
    delete_original = (tolower(response) == 'y');
    if (response != '\n') std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n'); // Clear input buffer

    if (!delete_original) {
        std::cout << "Note: All WAV files will be moved to: [" << (root_path / old_wav_folder_name) << "]\n";
    }

    // Default: move MIDI files
    std::cout << "Do you want to move MIDI files to a separate folder? ([y]/n): ";
    char move_midi_response;
    std::cin.get(move_midi_response);
    bool move_midi = (tolower(move_midi_response) != 'n');
    if (move_midi_response != '\n') std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n'); // Clear input buffer

    if (move_midi) {
        std::cout << "Note: all MIDI files will be moved to: [" << (root_path / midi_folder_name) << "]\n";
    }

    // Default: move bank files
    std::cout << "Do you want to move bank files to separate folders? ([y]/n): ";
    char move_banks_response;
    std::cin.get(move_banks_response);
    bool move_banks = (tolower(move_banks_response) != 'n');
    if (move_banks_response != '\n') std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n'); // Clear input buffer

    if (move_banks) {
        std::cout << "Note: all bank files will be moved to separate folders, like for instance: [" << (root_path / arturia_folder_name) << "]\n";
    }

    // Prepare folders for old WAV files, MIDI files, and other categories
    fs::path old_wav_folder = root_path / old_wav_folder_name;
    fs::path midi_folder = root_path / midi_folder_name;
    fs::path arturia_folder = root_path / arturia_folder_name;
    fs::path serum_folder = root_path / serum_folder_name;
    fs::path vital_folder = root_path / vital_folder_name;
    fs::path ableton_folder = root_path / ableton_folder_name;
    fs::path natinst_folder = root_path / natinst_folder_name;
    fs::path unrecognized_folder = root_path / unrecognized_folder_name;
    fs::path documentation_folder = root_path / documentation_folder_name;

    // Grouping files by extension
    std::vector<fs::path> audio_files;
    for (const auto& entry : fs::recursive_directory_iterator(root_path)) {
        if (entry.is_regular_file()) {
            std::string extension = entry.path().extension().string();
            std::transform(extension.begin(), extension.end(), extension.begin(), ::tolower);
            if (has_extension(extension, lossless_extensions) || 
                (move_midi && has_extension(extension, midi_extensions)) ||
                (move_banks && (has_extension(extension, arturia_extensions) ||
                                has_extension(extension, serum_extensions) ||
                                has_extension(extension, vital_extensions) ||
                                has_extension(extension, ableton_extensions) ||
                                has_extension(extension, natinst_extensions))) ||
                has_extension(extension, analysis_extensions) ||
                has_extension(extension, unrecognized_extensions) ||
                has_extension(extension, documentation_extensions) ||
                entry.path().filename().string().rfind("._", 0) == 0 ||
                entry.path().filename() == ".DS_Store") {
                audio_files.push_back(entry.path());
            }
        }
    }
    
    if (audio_files.empty()) {
        std::cout << "No audio files found!\n";
        std::cout << "Press Enter to exit...";
        std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');
        return 0;
    }

    state.total_files = audio_files.size();
    
    // Partitioning files into batches for threads
    std::vector<std::vector<fs::path>> batches(thread_count);
    for (size_t i = 0; i < audio_files.size(); ++i) {
        batches[i % thread_count].push_back(audio_files[i]);
    }

    // Start threads for processing
    std::vector<std::thread> workers;
    for (auto& batch : batches) {
        if (!batch.empty()) {
            workers.emplace_back(process_batch, std::ref(batch), std::ref(state), delete_original, 
                                 root_path, old_wav_folder, midi_folder, arturia_folder, serum_folder, 
                                 vital_folder, ableton_folder, natinst_folder, unrecognized_folder, documentation_folder);
        }
    }

    // Start progress display
    std::thread progress_thread(display_progress, std::ref(state));
    
    // Waiting for threads to finish
    for (auto& worker : workers) {
        worker.join();
    }
    
    state.stop_requested = true;
    progress_thread.join();

    // Analyze and delete empty folders
    std::vector<fs::path> deleted_folders;
    delete_empty_folders(root_path, deleted_folders);

    if (!deleted_folders.empty()) {
        std::cout << "\nDeleted empty folders:\n";
        for (const auto& folder : deleted_folders) {
            std::cout << folder << "\n";
        }
    }

    // Final report
    std::cout << "\n\nConversion completed!\n";
    std::cout << "Files converted: " << state.processed << "\n";
    std::cout << "Errors: " << state.errors << "\n";
    
    if (!state.error_messages.empty()) {
        std::ofstream error_log("conversion_errors.log");
        for (const auto& msg : state.error_messages) {
            error_log << msg << "\n";
        }
        std::cout << "Error details saved in conversion_errors.log\n";
    }

    std::cout << "Press Enter to exit...";
    std::cin.ignore(std::numeric_limits<std::streamsize>::max(), '\n');

    return 0;
}