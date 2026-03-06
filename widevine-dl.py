#!/usr/bin/env python3

import os
import shutil
import glob
import pathlib
import platform
import time
import subprocess
import re

FILE_DIRECTORY = str(pathlib.Path(__file__).parent.absolute())
TEMPORARY_PATH = os.path.join(FILE_DIRECTORY, "cache")
OUTPUT_PATH = os.path.join(FILE_DIRECTORY, "output")

# AUTO CREATE FOLDER
os.makedirs(TEMPORARY_PATH, exist_ok=True)
os.makedirs(OUTPUT_PATH, exist_ok=True)

# ==========================
# Utility
# ==========================

def osinfo():
    global PLATFORM
    PLATFORM = platform.system()

def divider():
    print('-' * shutil.get_terminal_size().columns)

def empty_folder(folder):
    files = glob.glob(os.path.join(folder, "*"))
    for f in files:
        os.remove(f)
    print("Emptied Temporary Files!")
    divider()
    quit()

def extract_key(prompt):
    global key, kid, keys
    key = prompt[30:62]
    kid = prompt[68:100]
    keys = f"{kid}:{key}"
    return key, kid, keys

# ==========================
# Download
# ==========================

def download_drm_content(mpd_url):

    divider()
    print("Processing Video Info..")

    subprocess.run([
        "yt-dlp",
        "--external-downloader", "aria2c",
        "--no-warnings",
        "--allow-unplayable-formats",
        "--no-check-certificate",
        "-F", mpd_url
    ], check=True)

    divider()

    VIDEO_ID = input("ENTER VIDEO_ID (Press Enter for Best): ").strip() or "bv"
    AUDIO_ID = input("ENTER AUDIO_ID (Press Enter for Best): ").strip() or "ba"

    divider()
    print("Downloading Encrypted Video from CDN..")

    subprocess.run([
        "yt-dlp",
        "-f", VIDEO_ID,
        "-o", os.path.join(TEMPORARY_PATH, "encrypted_video.%(ext)s"),
        "--no-warnings",
        "--external-downloader", "aria2c",
        "--allow-unplayable-formats",
        "--no-check-certificate",
        mpd_url
    ], check=True)

    print("Downloading Encrypted Audio from CDN..")

    subprocess.run([
        "yt-dlp",
        "-f", AUDIO_ID,
        "-o", os.path.join(TEMPORARY_PATH, "encrypted_audio.%(ext)s"),
        "--no-warnings",
        "--external-downloader", "aria2c",
        "--allow-unplayable-formats",
        "--no-check-certificate",
        mpd_url
    ], check=True)

# ==========================
# Decrypt
# ==========================

def decrypt_content():

    extract_key(KEY_PROMPT)

    divider()
    print("Decrypting WideVine DRM..")
    osinfo()

    if PLATFORM == "Windows":
        mp4decrypt_path = os.path.join(FILE_DIRECTORY, "mp4decrypt", "mp4decrypt_win.exe")
    elif PLATFORM == "Darwin":
        mp4decrypt_path = os.path.join(FILE_DIRECTORY, "mp4decrypt", "mp4decrypt_mac")
    elif PLATFORM == "Linux":
        mp4decrypt_path = os.path.join(FILE_DIRECTORY, "mp4decrypt", "mp4decrypt_linux")
    else:
        mp4decrypt_path = "mp4decrypt"

    video_files = glob.glob(os.path.join(TEMPORARY_PATH, "encrypted_video.*"))
    audio_files = glob.glob(os.path.join(TEMPORARY_PATH, "encrypted_audio.*"))

    if not video_files or not audio_files:
        print("ERROR: Encrypted files not found!")
        exit()

    video_in = video_files[0]
    audio_in = audio_files[0]

    video_out = os.path.join(TEMPORARY_PATH, "decrypted_video.mp4")
    audio_out = os.path.join(TEMPORARY_PATH, "decrypted_audio.m4a")

    subprocess.run([mp4decrypt_path, video_in, video_out, "--key", keys], check=True)
    subprocess.run([mp4decrypt_path, audio_in, audio_out, "--key", keys], check=True)

    print("Decryption Complete!")

# ==========================
# Detect Audio Offset
# ==========================

def get_audio_offset(audio_path):

    result = subprocess.run(
        ["ffmpeg", "-i", audio_path],
        stderr=subprocess.PIPE,
        text=True
    )

    match = re.search(r"start:\s*([0-9\.]+)", result.stderr)

    if match:
        return float(match.group(1))

    return 0.0

# ==========================
# Merge with Subtitle
# ==========================

def merge_content():

    divider()

    FILENAME = input("Enter File Name (with extension): \n> ").strip()

    divider()

    video_path = os.path.join(TEMPORARY_PATH, "decrypted_video.mp4")
    audio_path = os.path.join(TEMPORARY_PATH, "decrypted_audio.m4a")

    output_file = os.path.join(OUTPUT_PATH, FILENAME)

    if not os.path.exists(video_path):
        print("ERROR: decrypted_video.mp4 not found!")
        exit()

    if not os.path.exists(audio_path):
        print("ERROR: decrypted_audio.m4a not found!")
        exit()

    offset = get_audio_offset(audio_path)

    print(f"Detected audio offset: {offset}")

    add_sub = input("Add external subtitle? (y/n): ").strip().lower()

    cmd = [
        "ffmpeg",
        "-y",
        "-i", video_path,
        "-itsoffset", str(offset),
        "-i", audio_path,
    ]

    if add_sub == "y":

        sub_path = input("Enter subtitle file path: ").strip()
        lang = input("Enter language code (ex: ind, eng): ").strip() or "und"
        default_flag = input("Set as default? (y/n): ").strip().lower()

        cmd.extend(["-i", sub_path])

        cmd.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-map", "2:0",
            "-c:v", "copy",
            "-c:a", "copy",
            "-c:s", "mov_text",
            "-metadata:s:s:0", f"language={lang}"
        ])

        if default_flag == "y":
            cmd.extend(["-disposition:s:0", "default"])

    else:

        cmd.extend([
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c", "copy"
        ])

    cmd.append(output_file)

    subprocess.run(cmd, check=True)

    print("Merge Complete!")

# ==========================
# MAIN
# ==========================

divider()
print("**** Widevine-DL Ultimate Version ****")
divider()

MPD_URL = input("Enter MPD URL: \n> ").strip()
KEY_PROMPT = input("Enter WideVineDecryptor Prompt: \n> ").strip()

download_drm_content(MPD_URL)
decrypt_content()
merge_content()

divider()
print("Process Finished.")
divider()

delete_choice = input("Delete cache files? (y/n): ").strip().lower()

if delete_choice != "n":
    empty_folder(TEMPORARY_PATH)