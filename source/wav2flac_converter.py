# -*- coding: utf-8 -*-
"""
Created on Tue Jul 23 14:39:54 2024

@author: salva
"""

####~ Requirements      ~####

####~ Modules recall    ~####
import os
from os.path import isdir, isfile, join, basename, splitext, dirname, exists
from pydub import AudioSegment
from tqdm import tqdm
import shutil
from unidecode import unidecode

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
    # if not basename(wav_path).isascii():
    #     wav_basename_ascii = unidecode(basename(wav_path))
    #     wav_path_ascii = join(dirname(wav_path), wav_basename_ascii)
    #     os.rename(wav_path, wav_path_ascii)
    #     wav_path = wav_path_ascii
    flac_path = splitext(wav_path)[0] + '.flac'
    song = AudioSegment.from_wav(wav_path)
    song.export(flac_path, format = "flac")
    
def fileconv(curr_path, remExsWav=True, moveMIDI=False, orig_path=os.getcwd()):
    success = False
    if isfile(curr_path):
        if basename(curr_path)[:2] == '._' or basename(curr_path) == '.DS_Store': # Stupid fake, hidden, and not necessary files (macos...)
            os.remove(curr_path)
            
        else:
            if splitext(curr_path)[1].lower() == '.wav':
                wav2flac(curr_path)
                if remExsWav:
                    os.remove(curr_path)
                else:
                    old_wav_pth_bs = join(dirname(curr_path), 'old_wav')
                    
                    if not(exists(old_wav_pth_bs)):
                        os.mkdir(old_wav_pth_bs)
                        
                    old_wav_pth_fl = join(old_wav_pth_bs, basename(curr_path))
                    shutil.move(curr_path, old_wav_pth_fl)
                    
                success = True
                
            elif splitext(curr_path)[1].lower() == '.asd' or splitext(curr_path)[1].lower() == '.reapeaks': # Analysis files of: Ableton, Reaper
                os.remove(curr_path)
                
            elif splitext(curr_path)[1].lower() == '.mid' and moveMIDI: # Move midi files to new MIDI folder, inside origin_scan_path
                comm_path_prfx = os.path.commonpath([curr_path, orig_path])
                rltv_path_sffx = os.path.relpath(dirname(curr_path), comm_path_prfx)
                
                new_move_path = join(comm_path_prfx, 'MIDI', rltv_path_sffx)
                
                if not(exists(new_move_path)):
                    os.makedirs(new_move_path) # To create nested directories
                    
                new_move_pth_fl = join(new_move_path, basename(curr_path))
                shutil.move(curr_path, new_move_pth_fl)
                
    return success
    
####~ Core              ~####
scan_path = [input(f'Samples folder ([{os.getcwd()}]): ') or os.getcwd()]
origin_scan_path = scan_path.copy()

rem_usr_in = input('Do you want to remove pre-existing wav files? ([y]/n): ' or 'y')
if rem_usr_in == 'y':
    rem_wav = True
elif rem_usr_in == 'n':
    rem_wav = False
    print('Inside each sub-folder that contains wav files, ' \
          'a new folder (old_wav) will be created and all ' \
          'the pre-existing samples will be moved there!')
else:
    raise Exception('Just "y" or "n", fucking asshole!')
    
move_midi_in = input('Do you want to move midi file in a separate MIDI folder? ([y]/n): ' or 'y')
if move_midi_in == 'y':
    move_mid = True
    print("A new folder (MIDI) will be created in: [" \
          f"{origin_scan_path[0]}] " \
          "and all midi files will be moved there!")
elif move_midi_in == 'n':
    move_mid = False
else:
    raise Exception('Just "y" or "n", fucking asshole!')
    
files_conv, fold_hidd_nr = list(), list()
while len(scan_path) >= 1:
    temp_sub_dirs, temp_files, temp_hidd = pthdirnav(scan_path[0])
    
    scan_path += temp_sub_dirs
    files_conv += temp_files
    fold_hidd_nr += temp_hidd
    
    scan_path.pop(0)
    
files_succ_conv = 0
files_err = list()
for idx in tqdm(range(len(files_conv))):
    curr_fl_pth = files_conv[idx]
    try:
        succ = fileconv(curr_fl_pth, remExsWav=rem_wav, moveMIDI=move_mid, orig_path=origin_scan_path[0])
        if succ:
            files_succ_conv += 1
    except:
        # print('Error with sample: '+curr_fl_pth)
        files_err.append(curr_fl_pth)

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
            f.write('\nThe following hidden folders were not deleted (please check file permission): \n')
            for line in fold_hidd_nr:
                f.write(f"{unidecode(line)}\n")
    f.close()
    
print(f"Succesfully coverted {files_succ_conv} (of {files_succ_conv+len(files_err)}) wav files into flac")

input('Press Enter to exit...')