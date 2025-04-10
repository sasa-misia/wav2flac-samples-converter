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

####~ Requirements      ~####
if shutil.which('ffmpeg') == None:
    raise Exception('You must have ffmpeg installed! Otherwise flac files will be corrupted!')

####~ Functions         ~####
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

            except Exception as e:
                print(f"Error processing file {curr_path}: {e}")
                
    return success
    
####~ Core              ~####
scan_path = [input(f'Samples main folder (default is [{os.getcwd()}]): ') or os.getcwd()]
origin_scan_path = scan_path.copy()
all_paths = scan_path.copy()

prmpt_msg = 'Just "y" or "n", fucking asshole!'

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

if len(remvd_flds) > 0:
    print(f"{len(remvd_flds)} folders were empty -> deleted! (check deleted_folders.txt for info)")
    
del_report_filename = join(origin_scan_path[0],'deleted_folders.txt')
if exists(del_report_filename):
    os.remove(del_report_filename)

if len(remvd_flds) > 0:
    with open(del_report_filename, 'w') as d:
        d.write('The following folders were deleted because empty: \n')
        for line in remvd_flds:
            d.write(f"{unidecode(line)}\n")

err_report_filename = join(origin_scan_path[0],'wav_errors.txt')
if exists(err_report_filename):
    os.remove(err_report_filename)
    
if len(files_err) > 0 or len(fold_hidd_nr) > 0:
    with open(err_report_filename, 'w') as f:
        if len(files_err) > 0:
            f.write('The following files were not converted (please consider renaming): \n')
            for line in files_err:
                f.write(f"{unidecode(line)}\n")
        if len(fold_hidd_nr) > 0:
            f.write('\nThe following hidden (or empty) folders were not deleted (please check file permission): \n')
            for line in fold_hidd_nr:
                f.write(f"{unidecode(line)}\n")


print(f"Successfully converted {files_succ_conv} (of {files_succ_conv+len(files_err)}) audio files into flac")

input('Press Enter to exit...')