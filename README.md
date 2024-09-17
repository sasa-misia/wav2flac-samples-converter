# wav2flac_sample_converter
 Automatic audio converter. From wav (or aif) to flac, for all your directory and subdirectories content

Hello clochard!
Are you a music producer? 
Do you have too audio samples? 
Do you want to save hdd space? 

Well, this is the solution for you, motherf*cker!!!

This program will automatically convert all your wav samples into flac files, to save storage but without losing quality. 
If you are lucky, you can save up to 70% of storage!

You can use it as an exe file with Windows or as a script from python.

Link to exe file: https://mega.nz/folder/ZK0QkKwB#z4Ihm6bcjdk8dUJKeYOHWw

In order to use it as an executable, you have to move the wav2flac_converter.exe and ffmpeg.exe files to your samples folder (or also a different folder but with both exe files in the same location), then you just need to run it and the program will do the hard work for you, while you're eating fat and crispy chips on your sofa...

If you prefer to mod the script or run it with python, well, just run it but first remember to download all the modules required: os, pydub, tqdm, shutil, and unidecode. 

PLEASE NOTE (1): if you run it with python, then you need also to have installed ffmpeg in your pc! Please install it with pip or conda, depending on your environment (or with the exe file in the link above).

PLEASE NOTE (2): you can decide if you want to remove your wav files or maintain them. 
- If you opt for the 1st option **YOUR OLD WAV SAMPLES WILL BE REMOVED DIRECTLY, WITHOUT PASSING FROM THE TRASH**! 
Anyway, this is not a problem, since flac is lossless and you can revert them to wav, without losing quality. 
- If you opt for the 2nd option (default), then it will be created a new folder, called '_old_wav_check', and all your wav files of each subfolder will be moved there. 
As you can guess, you will end up with the same structure of before, but moved into '_old_wav_check' folder! 
It is just to avoid to delete wav files directly, and to let you check first (not recommended if you have a big collection of samples).

PLEASE NOTE (3): Unfortunately, it can happen sometimes that some samples cannot be converted, due to several issues.
For instance, if you have your samples synced in the cloud (like OneDrive), some of them are not physical files but a sort of alias, then the conversion will fail.
But... don't worry darling! At the end of the conversion, a report file (wav_errors.txt) is created and it will tell you where are those samples! Sometimes, a simple renaming is effective. Alternatively, you can consider to move just those samples in a new temporary location, where run again the program.

Extra goodies: 
- all your ._ wav files (supplementary to the original wav files, with no relevant extra info) will be automatically removed from your folders! These files are normally 4kB in size, ignored by the system, and hidden, but if you are a windows user you know what I am talking about... disgusting and dummy files...
- all your documentation files (.txt, .jpg, etc.) will be moved in a separate folder called _Documentation, which preserves the same structure of your sample folder.
- all unrecognized files (no extension or .dat) will be moved in a separate folder called _Unrecognized, which preserves the same structure of your sample folder.
- you can decide to move all your midi files into a new folder called MIDI, which preserves the same structure (subfolders) for each midi file in the original location.
- you can decide to move all your banks (Arturia, Serum, etc.) into new separate folders (ex: _Arturia Banks), which preserve the same structure (subfolders) for each file in the original location.
- it works also with aiff samples!

If you appreciate it, please let me know something, or consider to support my work.
Maybe grabbing a f*cking beat from my studio?
2Musicians Studio 
https://2musicians-studio.com/

Cheers ;)
