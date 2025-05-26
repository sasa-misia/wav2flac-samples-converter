# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 14:39:54 2024

@author: salva
"""

####~ Modules recall    ~####
import os
from os.path import isdir, isfile, join, basename, splitext, dirname, exists
from pydub import AudioSegment
from tqdm import tqdm
import shutil
from unidecode import unidecode
import unicodedata
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

####~ Requirements      ~####
if shutil.which('ffmpeg') == None:
    raise Exception('You must have ffmpeg installed! Otherwise flac files will be corrupted!')

####~ ASCII Conversion Maps and Functions ~####
# Character mapping for non-ASCII to ASCII conversion (same as C++ version)
ascii_conversion_map = {
    # Latin characters with diacritics
    'à': 'a', 'á': 'a', 'â': 'a', 'ã': 'a', 'ä': 'a', 'å': 'a', 'æ': 'ae',
    'ç': 'c', 'è': 'e', 'é': 'e', 'ê': 'e', 'ë': 'e', 'ì': 'i', 'í': 'i',
    'î': 'i', 'ï': 'i', 'ð': 'd', 'ñ': 'n', 'ò': 'o', 'ó': 'o', 'ô': 'o',
    'õ': 'o', 'ö': 'o', 'ø': 'o', 'ù': 'u', 'ú': 'u', 'û': 'u', 'ü': 'u',
    'ý': 'y', 'þ': 'th', 'ÿ': 'y',
    # Uppercase variants
    'À': 'A', 'Á': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A', 'Å': 'A', 'Æ': 'AE',
    'Ç': 'C', 'È': 'E', 'É': 'E', 'Ê': 'E', 'Ë': 'E', 'Ì': 'I', 'Í': 'I',
    'Î': 'I', 'Ï': 'I', 'Ð': 'D', 'Ñ': 'N', 'Ò': 'O', 'Ó': 'O', 'Ô': 'O',
    'Õ': 'O', 'Ö': 'O', 'Ø': 'O', 'Ù': 'U', 'Ú': 'U', 'Û': 'U', 'Ü': 'U',
    'Ý': 'Y', 'Þ': 'TH',
    # German umlauts and sharp s
    'ß': 'ss',
    # Eastern European characters
    'ą': 'a', 'ć': 'c', 'ę': 'e', 'ł': 'l', 'ń': 'n', 'ś': 's', 'ź': 'z', 'ż': 'z',
    'Ą': 'A', 'Ć': 'C', 'Ę': 'E', 'Ł': 'L', 'Ń': 'N', 'Ś': 'S', 'Ź': 'Z', 'Ż': 'Z',
    # Czech/Slovak
    'č': 'c', 'ď': 'd', 'ň': 'n', 'ř': 'r', 'š': 's', 'ť': 't', 'ž': 'z',
    'Č': 'C', 'Ď': 'D', 'Ň': 'N', 'Ř': 'R', 'Š': 'S', 'Ť': 'T', 'Ž': 'Z',
    # Hungarian
    'ő': 'o', 'ű': 'u', 'Ő': 'O', 'Ű': 'U',
    # Common symbols
    '\u2013': '-', '—': '-', ''': "'", ''': "'", '"': '"', '"': '"', # \u2013 is – (en dash)
    '«': '"', '»': '"', '…': '...', '•': '*'
}

def contains_non_ascii(text):
    """Check if string contains non-ASCII characters"""
    return any(ord(char) > 127 for char in text)

def convert_to_ascii(text):
    """Convert non-ASCII characters to ASCII equivalents"""
    if not contains_non_ascii(text):
        return text
    
    result = []
    for char in text:
        if ord(char) <= 127:
            result.append(char)
        elif char in ascii_conversion_map:
            result.append(ascii_conversion_map[char])
        else:
            # Try Unicode normalization as fallback
            normalized = unicodedata.normalize('NFD', char)
            ascii_char = ''.join(c for c in normalized if ord(c) <= 127)
            result.append(ascii_char if ascii_char else '*')
    
    return ''.join(result)

def generate_unique_ascii_name(directory, base_name, extension):
    """Generate a unique ASCII filename if collision occurs"""
    ascii_name = convert_to_ascii(base_name)
    candidate = join(directory, ascii_name + extension)
    
    counter = 1
    while exists(candidate):
        ascii_name = convert_to_ascii(base_name) + "_" + str(counter)
        candidate = join(directory, ascii_name + extension)
        counter += 1
    
    return ascii_name + extension

class RenameTracker:
    """Thread-safe tracker for rename operations"""
    def __init__(self):
        self.renamed_files = []
        self.renamed_folders = []
        self.rename_errors = []
        self.lock = threading.Lock()
    
    def add_renamed_file(self, old_path, new_path):
        with self.lock:
            self.renamed_files.append((old_path, new_path))
    
    def add_renamed_folder(self, old_path, new_path):
        with self.lock:
            self.renamed_folders.append((old_path, new_path))
    
    def add_error(self, error_msg):
        with self.lock:
            self.rename_errors.append(error_msg)

def convert_names_to_ascii(root_path, rename_tracker):
    """Convert all non-ASCII file and folder names to ASCII equivalents"""
    folders_to_rename = []
    files_to_rename = []
    
    # Collect all folders and files that need renaming
    try:
        for root, dirs, files in os.walk(root_path):
            # Collect folders
            for d in dirs:
                folder_path = join(root, d)
                if contains_non_ascii(d):
                    folders_to_rename.append(folder_path)
            
            # Collect files
            for f in files:
                file_path = join(root, f)
                if contains_non_ascii(f):
                    files_to_rename.append(file_path)
    
    except Exception as e:
        rename_tracker.add_error(f"Error scanning directory: {str(e)}")
        return
    
    # Sort folders by depth (deepest first) to avoid path conflicts
    folders_to_rename.sort(key=lambda x: x.count(os.sep), reverse=True)
    
    # Rename folders first
    for folder_path in folders_to_rename:
        try:
            original_name = basename(folder_path)
            ascii_name = convert_to_ascii(original_name)
            parent = dirname(folder_path)
            new_path = join(parent, ascii_name)
            
            # Handle potential name collisions
            counter = 1
            while exists(new_path) and new_path != folder_path:
                ascii_name = convert_to_ascii(original_name) + "_" + str(counter)
                new_path = join(parent, ascii_name)
                counter += 1
            
            if new_path != folder_path:
                os.rename(folder_path, new_path)
                rename_tracker.add_renamed_folder(folder_path, new_path)
        
        except Exception as e:
            rename_tracker.add_error(f"Failed to rename folder [{folder_path}]: {str(e)}")
    
    # Re-scan for files after folder renaming
    files_to_rename = []
    try:
        for root, dirs, files in os.walk(root_path):
            for f in files:
                file_path = join(root, f)
                if contains_non_ascii(f):
                    files_to_rename.append(file_path)
    except Exception as e:
        rename_tracker.add_error(f"Error re-scanning files after folder rename: {str(e)}")
    
    # Rename files
    for file_path in files_to_rename:
        try:
            original_name = splitext(basename(file_path))[0]
            extension = splitext(file_path)[1]
            parent = dirname(file_path)
            
            new_filename = generate_unique_ascii_name(parent, original_name, extension)
            new_path = join(parent, new_filename)
            
            # Copy file to new location with ASCII name
            shutil.copy2(file_path, new_path)
            
            # Verify the copy was successful
            if exists(new_path) and os.path.getsize(new_path) == os.path.getsize(file_path):
                # Remove original file only after successful copy
                os.remove(file_path)
                rename_tracker.add_renamed_file(file_path, new_path)
            else:
                rename_tracker.add_error(f"Copy verification failed for: {file_path}")
        
        except Exception as e:
            rename_tracker.add_error(f"Failed to rename file [{file_path}]: {str(e)}")

####~ Core functions ~####
def pthdirnav(path_start):
    list_pth_el = os.listdir(path_start)
    full_paths = [join(path_start, i) for i in list_pth_el]
    list_sub_pths, list_files, list_machidd = list(), list(), list()
    for curr_path in full_paths:
        if isdir(curr_path):
            if basename(curr_path).lower() == '__macosx': # Path full of hidden files, not meaningful for windows. If you have macOS it will be rebuilt
                try:
                    shutil.rmtree(curr_path)
                except:
                    list_machidd.append(curr_path)
                    list_sub_pths.append(curr_path)
            else:
                list_sub_pths.append(curr_path)
        else:
            list_files.append(curr_path)
    return list_sub_pths, list_files, list_machidd

def wav2flac(wav_path):
    flac_path = splitext(wav_path)[0] + '.flac'
    wav_sampl = AudioSegment.from_wav(wav_path)
    wav_sampl.export(flac_path, format = "flac")
    
def gaudio2flac(gaudio_path):
    flac_path = splitext(gaudio_path)[0] + '.flac'
    gad_sampl = AudioSegment.from_file(gaudio_path)
    gad_sampl.export(flac_path, format = "flac")
    
def filepathinfo(curr_path, base_path):
    file_basenm = basename(curr_path)
    file_extens = splitext(curr_path)[1].lower()
    path_prefix = os.path.commonpath([curr_path, base_path])
    path_suffix = os.path.relpath(dirname(curr_path), path_prefix)
    return file_basenm, file_extens, path_prefix, path_suffix
    
def movewsub(curr_path, base_path, new_fold):
    file_basenm, _, path_prefix, path_suffix = filepathinfo(curr_path, base_path)
    
    # Continue only if the file is not already in the target folder
    if not path_suffix.startswith(new_fold):
        new_move_path = join(path_prefix, new_fold, path_suffix)
        
        if not exists(new_move_path):
            os.makedirs(new_move_path)  # Create nested directories if needed
            
        new_move_pth_fl = join(new_move_path, file_basenm)
        shutil.move(curr_path, new_move_pth_fl)

def fileconv(curr_path, remExsWav=True, moveMIDI=False, moveBanks=True, orig_path=os.getcwd()):
    success = False
    if isfile(curr_path):
        file_bsn, file_ext, comm_path_prfx, rltv_path_sffx = filepathinfo(curr_path, orig_path)
        
        lssless_fldnm = '_old_wav_check'
        unrecog_fldnm = '_Unrecognized'
        docu_fldnm    = '_Documentation'
        midi_fldnm    = '_MIDI'
        arturia_fldnm = '_Arturia Banks'
        serum_fldnm   = '_Serum Banks'
        vital_fldnm   = '_Vital Banks'
        ableton_fldnm = '_Ableton Banks'
        natinst_fldnm = '_NI Banks'
        archive_fldnm = '_Archives'
        
        lssless_extns = ['.wav', '.aif', '.aiff']
        analsys_extns = ['.asd', '.reapeaks']
        unrecog_extns = ['.dat', '']
        docu_extns    = ['.html', '.docx', '.doc', '.pdf', '.jpg', '.jpeg', '.png', '.txt', '.rtf', '.xml', '.asc', '.msg', '.wpd', '.wps', '.url']
        midi_extns    = ['.mid', '.midi']
        arturia_extns = ['.labx', '.jupx', '.prox', '.junx', '.minix', '.pgtx']
        serum_extns   = ['.fxp']
        vital_extns   = ['.vitalbank', '.vital', '.vitalskin']
        ableton_extns = ['.abl', '.ablbundle', '.adg', '.agr', '.adv', '.alc', '.alp', '.als', '.ams', '.amxd', '.ask', '.cfg', '.xmp']
        natinst_extns = ['.nmsv', '.nksf', '.bnk', '.ksd', '.ngrr']
        archive_extns = ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz']
        
        if file_bsn[:2] == '._' or file_bsn == '.DS_Store': # Stupid fake, hidden, and not necessary files (macos...)
            os.remove(curr_path)
            
        elif rltv_path_sffx.startswith(lssless_fldnm):  # Use startswith for clarity
            success = True # The process is skipped because the current file is in the Old Wav Path (no conversion needed)
            
        else:
            try:
                if any([x == file_ext for x in lssless_extns]):
                    gaudio2flac(curr_path)
                    
                    if remExsWav:
                        os.remove(curr_path)
                    else:
                        movewsub(curr_path, orig_path, lssless_fldnm)
                        
                    success = True
                    
                elif any([x == file_ext for x in analsys_extns]): # Analysis files of: Ableton, Reaper
                    os.remove(curr_path)
                    
                elif any([x == file_ext for x in unrecog_extns]): # Move unrecognized files to new _Unrecognized folder, inside orig_path
                    movewsub(curr_path, orig_path, unrecog_fldnm)
                
                elif any([x == file_ext for x in docu_extns]): # Move documentation files to new _Documentation folder, inside orig_path
                    movewsub(curr_path, orig_path, docu_fldnm)
                    
                elif any([x == file_ext for x in midi_extns]) and moveMIDI: # Move midi files to new MIDI folder, inside orig_path
                    movewsub(curr_path, orig_path, midi_fldnm)
                    
                elif any([x == file_ext for x in arturia_extns]) and moveBanks: # Move arturia files to new _Arturia Banks folder, inside orig_path
                    movewsub(curr_path, orig_path, arturia_fldnm)
                    
                elif any([x == file_ext for x in serum_extns]) and moveBanks: # Move serum files to new _Serum Banks folder, inside orig_path
                    movewsub(curr_path, orig_path, serum_fldnm)
                
                elif any([x == file_ext for x in vital_extns]) and moveBanks: # Move vital files to new _Vital Banks folder, inside orig_path
                    movewsub(curr_path, orig_path, vital_fldnm)
                
                elif any([x == file_ext for x in ableton_extns]) and moveBanks: # Move ableton files to new _Ableton Banks folder, inside orig_path
                    movewsub(curr_path, orig_path, ableton_fldnm)
                
                elif any([x == file_ext for x in natinst_extns]) and moveBanks: # Move native instruments files to new _NI Banks folder, inside orig_path
                    movewsub(curr_path, orig_path, natinst_fldnm)
                
                elif any([x == file_ext for x in archive_extns]): # Move archive files to new _Archives folder, inside orig_path
                    movewsub(curr_path, orig_path, archive_fldnm)

            except Exception as e:
                print(f"Error processing file {curr_path}: {e}")
                
    return success

####~ Core              ~####
scan_path = [input(f'Samples main folder (default is [{os.getcwd()}]): ') or os.getcwd()]
origin_scan_path = scan_path.copy()
all_paths = scan_path.copy()

prmpt_msg = 'Just "y" or "n", fucking asshole!'

# ASCII conversion prompt
ascii_usr_in = input('Convert non-ASCII filenames and folder names to ASCII equivalents? (y/[n]): ') or 'n'
if ascii_usr_in == 'y':
    convert_ascii = True
elif ascii_usr_in == 'n':
    convert_ascii = False
else:
    raise ValueError(prmpt_msg)

if convert_ascii:
    print("Note: Files and folders with non-ASCII characters will be renamed to ASCII equivalents.")
    print("Original files will be replaced with ASCII-named copies.")
    print("Converting names to ASCII...")
    
    rename_tracker = RenameTracker()
    convert_names_to_ascii(origin_scan_path[0], rename_tracker)
    
    print("ASCII conversion completed.")

rem_usr_in = input('Do you want to remove pre-existing wav files? (y/[n]): ') or 'n'
if rem_usr_in == 'y':
    rem_wav = True
elif rem_usr_in == 'n':
    rem_wav = False
    print("A new folder (_old_wav_check) will be created and " \
          "all the pre-existing samples will be moved there!")
else:
    raise ValueError(prmpt_msg)

move_midi_in = input('Do you want to move midi file in a separate MIDI folder? ([y]/n): ') or 'y'
if move_midi_in == 'y':
    move_mid = True
elif move_midi_in == 'n':
    move_mid = False
else:
    raise ValueError(prmpt_msg)

move_banks_in = input('Do you want to move banks file in separate folders? ([y]/n): ') or 'y'
if move_banks_in == 'y':
    move_bnk = True
elif move_banks_in == 'n':
    move_bnk = False
else:
    raise ValueError(prmpt_msg)

if move_mid:
    print("Note 1: a new folder (_MIDI) will be created in: [" \
          f"{origin_scan_path[0]}] " \
          "and all midi files will be moved there!")

if move_bnk:
    print("Note 2: new folders (ex: _Arturia Banks) will be created in: [" \
          f"{origin_scan_path[0]}] " \
          "and all bank files will be moved there!")
    
files_conv, fold_hidd_nr = list(), list()
while len(scan_path) >= 1:
    temp_sub_dirs, temp_files, temp_hidd = pthdirnav(scan_path[0])
    
    scan_path += temp_sub_dirs
    all_paths += temp_sub_dirs
    files_conv += temp_files
    fold_hidd_nr += temp_hidd
    
    scan_path.pop(0)
    
files_succ_conv = 0
files_err = list()
for idx in tqdm(range(len(files_conv))):
    curr_fl_pth = files_conv[idx]
    try:
        succ = fileconv(curr_fl_pth, remExsWav=rem_wav, moveMIDI=move_mid, moveBanks=move_bnk, orig_path=origin_scan_path[0])
        if succ:
            files_succ_conv += 1
    except Exception as e:
        print(f"Error with sample {curr_fl_pth}: {e}")
        files_err.append(curr_fl_pth)

some_fld_empty = True
remvd_flds = list()
while some_fld_empty:
    some_fld_empty = False
    for curr_fold in all_paths:
        if exists(curr_fold) and (len(os.listdir(curr_fold)) == 0):
            try:
                os.rmdir(curr_fold)
                remvd_flds.append(curr_fold)
                some_fld_empty = True
            except Exception as e:
                print(f"Error deleting folder {curr_fold}: {e}")
                fold_hidd_nr.append(curr_fold)

# Display ASCII conversion results
if convert_ascii:
    if rename_tracker.renamed_files:
        print(f"\nRenamed {len(rename_tracker.renamed_files)} files to ASCII:")
        for old_path, new_path in rename_tracker.renamed_files[:10]:  # Show first 10
            print(f"  {old_path} -> {new_path}")
        if len(rename_tracker.renamed_files) > 10:
            print(f"  ... and {len(rename_tracker.renamed_files) - 10} more files")
    
    if rename_tracker.renamed_folders:
        print(f"\nRenamed {len(rename_tracker.renamed_folders)} folders to ASCII:")
        for old_path, new_path in rename_tracker.renamed_folders:
            print(f"  {old_path} -> {new_path}")
    
    if rename_tracker.rename_errors:
        print(f"\nASCII conversion errors ({len(rename_tracker.rename_errors)}):")
        for error in rename_tracker.rename_errors[:5]:  # Show first 5
            print(f"  {error}")
        if len(rename_tracker.rename_errors) > 5:
            print(f"  ... and {len(rename_tracker.rename_errors) - 5} more errors")

if len(remvd_flds) > 0:
    print(f"{len(remvd_flds)} folders were empty -> deleted! (check deleted_folders.txt for info)")
    
del_report_filename = join(origin_scan_path[0],'deleted_folders.txt')
if exists(del_report_filename):
    os.remove(del_report_filename)

if len(remvd_flds) > 0:
    with open(del_report_filename, 'w', encoding='utf-8') as d:
        d.write('The following folders were deleted because empty: \n')
        for line in remvd_flds:
            d.write(f"{unidecode(line)}\n")

err_report_filename = join(origin_scan_path[0],'conversion_errors.txt')
if exists(err_report_filename):
    os.remove(err_report_filename)

# Write comprehensive error log
if len(files_err) > 0 or len(fold_hidd_nr) > 0 or (convert_ascii and rename_tracker.rename_errors):
    with open(err_report_filename, 'w', encoding='utf-8') as f:
        if len(files_err) > 0:
            f.write('=== CONVERSION ERRORS (consider ASCII renaming) ===\n')
            for line in files_err:
                f.write(f"{unidecode(line)}\n")
            f.write('\n')
        if len(fold_hidd_nr) > 0:
            f.write('=== FOLDER DELETION ERRORS (check permissions) ===\n')
            for line in fold_hidd_nr:
                f.write(f"{unidecode(line)}\n")
            f.write('\n')

        if convert_ascii and rename_tracker.rename_errors:
            f.write('=== ASCII CONVERSION ERRORS ===\n')
            for error in rename_tracker.rename_errors:
                f.write(f"{error}\n")

print(f"Successfully converted {files_succ_conv} (of {files_succ_conv+len(files_err)}) audio files into flac")

if convert_ascii:
    print(f"Files renamed to ASCII: {len(rename_tracker.renamed_files)}")
    print(f"Folders renamed to ASCII: {len(rename_tracker.renamed_folders)}")
    if rename_tracker.rename_errors:
        print(f"ASCII conversion errors: {len(rename_tracker.rename_errors)}")

if len(files_err) > 0 or len(fold_hidd_nr) > 0 or (convert_ascii and rename_tracker.rename_errors):
    print("Error details saved in conversion_errors.txt")

input('Press Enter to exit...')