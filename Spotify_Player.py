import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import io
import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading
import time
from tkinter import messagebox
import os
import subprocess
import psutil
import time

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id="9931b8f4d0784049bc7186cd74f57f79",
    client_secret="a89916ab849e43e5bdc2839979d072aa",
    redirect_uri="http://127.0.0.1:800",
    scope="user-library-read user-read-playback-state user-modify-playback-state playlist-read-private"
))

def launch_spotify_store_version():
    proc = subprocess.Popen(
        ['explorer.exe', 'shell:AppsFolder\\SpotifyAB.SpotifyMusic_zpdnekdrzrea0!Spotify'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    return proc  # Save this to close later

def wait_for_spotify_device(sp, timeout=30):
    print("⏳ Waiting for Spotify to activate as a playback device...")
    start = time.time()
    while time.time() - start < timeout:
        devices = sp.devices()
        if devices['devices']:
            print("✅ Spotify is ready!")
            return True
        time.sleep(1)
    print("❌ Timeout: No Spotify device found.")
    return False

def is_spotify_running():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and 'Spotify' in proc.info['name']:
            return True
    return False

def wait_for_spotify_process(timeout=15):
    print("⏳ Waiting for Spotify process to launch...")
    start = time.time()
    while time.time() - start < timeout:
        if is_spotify_running():
            print("✅ Spotify process detected.")
            return True
        time.sleep(1)
    print("❌ Timeout: Spotify process not found.")
    return False

def close_spotify():
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] and "Spotify.exe" in proc.info['name']:
            try:
                proc.terminate()
                print("✅ Spotify closed.")
            except Exception as e:
                print("⚠️ Could not close Spotify:", e)

def on_exit():
    close_spotify()  # Kill Spotify before quitting
    root.destroy()

root = tk.Tk()
root.title("Spotify Player")
root.geometry("400x350")
root.configure(bg="#3D413E")

# ---------------- NAVIGATION ----------------
def show_frame(frame):
    frame.tkraise()

# ---------------- HOME FRAME ----------------
home_frame = tk.Frame(root, bg="#3D413E")
home_frame.place(relwidth=1, relheight=1)

canvas = tk.Canvas(home_frame, bg="#3D413E")
scrollbar = tk.Scrollbar(home_frame, orient="vertical", command=canvas.yview)
scrollable_frame = tk.Frame(canvas, bg="#3D413E")

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Function to add each album/playlist row
def add_album_row(parent, name, image_url, uri):
    frame = tk.Frame(parent, bg="#3D413E")
    frame.pack(fill="x", pady=5)

    img_data = requests.get(image_url).content
    img = Image.open(io.BytesIO(img_data)).resize((60, 60))
    img_tk = ImageTk.PhotoImage(img)

    img_label = tk.Label(frame, image=img_tk, bg="white")
    img_label.image = img_tk
    img_label.pack(side="left", padx=5)

    name_label = tk.Label(frame, text=name, bg="white", font=("Helvetica", 12), anchor="w")
    name_label.pack(side="left", fill="x", expand=True)

    def play_and_go():
        devices = sp.devices()
        if devices['devices']:
            device_id = devices['devices'][0]['id']
            try:
                sp.transfer_playback(device_id, force_play=True)
                sp.start_playback(device_id=device_id, context_uri=uri)
                show_frame(now_frame)
            except spotipy.SpotifyException as e:
                print("Spotify error:", e)
                messagebox.showerror("Playback Error", "Failed to start playback. Try manually starting Spotify first.")
        else:
            messagebox.showinfo(
                "No Active Device",
                "Please open Spotify on your computer or phone and start playing a song briefly, then try again."
            )

    play_btn = tk.Button(frame, text="▶️", command=play_and_go)
    play_btn.pack(side="right", padx=5)

# Populate albums
albums = sp.current_user_saved_albums(limit=10)
for item in albums['items']:
    album = item['album']
    add_album_row(scrollable_frame, album['name'], album['images'][0]['url'], album['uri'])

# Populate playlists
playlists = sp.current_user_playlists(limit=10)
for item in playlists['items']:
    if item['images']:
        add_album_row(scrollable_frame, item['name'], item['images'][0]['url'], item['uri'])

# ---------------- NOW PLAYING FRAME ----------------
now_frame = tk.Frame(root, bg="#3D413E")
now_frame.place(relwidth=1, relheight=1)

song_label = tk.Label(now_frame, text="", font=("Helvetica", 14), bg="#3D413E", fg="white")
song_label.pack(pady=10)

artist_label = tk.Label(now_frame, text="", font=("Helvetica", 12), bg="#3D413E", fg="white")
artist_label.pack(pady=5)

cover_label = tk.Label(now_frame, bg="#3D413E")
cover_label.pack(pady=10)

progress = ttk.Scale(now_frame, from_=0, to=100, orient=tk.HORIZONTAL, length=300)
progress.pack(pady=10)

control_frame = tk.Frame(now_frame, bg="#3D413E")
control_frame.pack(pady=10)

def toggle_play_pause():
    playback = sp.current_playback()
    if playback and playback['is_playing']:
        sp.pause_playback()
    else:
        sp.start_playback()

tk.Button(control_frame, text="⏮️", command=lambda: sp.previous_track()).pack(side="left", padx=5)
tk.Button(control_frame, text="⏯️", command=toggle_play_pause).pack(side="left", padx=5)
tk.Button(control_frame, text="⏭️", command=lambda: sp.next_track()).pack(side="left", padx=5)

# 🔙 Back button
tk.Button(now_frame, text="⬅ Back", command=lambda: show_frame(home_frame)).pack(pady=10)

# ---------------- Update Now Playing Info ----------------
def update_now_playing():
    while True:
        try:
            track = sp.current_playback()
            if track and track['item']:
                name = track['item']['name']
                artist = track['item']['artists'][0]['name']
                song_label.config(text=f"{name}")
                artist_label.config(text=f"{artist}")

                cover_url = track['item']['album']['images'][0]['url']
                img_data = requests.get(cover_url).content
                img = Image.open(io.BytesIO(img_data)).resize((100, 100))
                img_tk = ImageTk.PhotoImage(img)
                cover_label.config(image=img_tk)
                cover_label.image = img_tk

                prog = (track['progress_ms'] / track['item']['duration_ms']) * 100
                progress.set(prog)
            else:
                song_label.config(text="No song playing")
                artist_label.config(text="")
                cover_label.config(image=None)
        except Exception as e:
            print("Error updating track:", e)
        time.sleep(3)

threading.Thread(target=update_now_playing, daemon=True).start()

launch_spotify_store_version()

if wait_for_spotify_process() and wait_for_spotify_device(sp):
    print("🚀 Launching your application now!")
    # Start on home screen
    show_frame(home_frame)
    root.protocol("WM_DELETE_WINDOW", on_exit)
    root.mainloop()
else:
    print("⚠️ Spotify not ready. Exiting or retry later.")