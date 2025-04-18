import os
import yt_dlp as ytd
import threading
import pygame
import time
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QFileDialog, QHBoxLayout, QProgressBar, QLabel
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QIcon
from data_operations import insert_song, reading_parsed_json



# Class to manage download operations
class DownloadManager:
    def __init__(self, app, music_player):
        self.app = app
        self.music_player = music_player
        self.last_progress = {}

    def download_audio(self, audio_url, output_folder, thread_id, pause_event, stop_event):
        yt_opts = {
            'verbose': True,
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a'
            }],
            'ffmpeg_location': '/opt/homebrew/bin/ffmpeg',
            'progress_hooks': [lambda d: self.progress_hook(d, thread_id, pause_event, stop_event)],
            'writeinfojson': True,
            'writethumbnail': True
        }
        try:
            with ytd.YoutubeDL(yt_opts) as ydl:
                info_dict = ydl.extract_info(audio_url, download=True)
                if info_dict and 'title' in info_dict:
                    return os.path.join(output_folder, f"{info_dict['title']}.m4a")
                else:
                    raise ValueError("Failed to extract audio information")
        except Exception as e:
            return self.download_error(e, thread_id)

    def download_vid(self, vid_url, output_folder, thread_id, pause_event, stop_event):
        yt_opts = {
            'verbose': True,
            'format': 'bestvideo[height>=4320]+bestaudio/bestvideo+bestaudio/best',
            'outtmpl': os.path.join(output_folder, '%(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }],
            'ffmpeg_location': '/opt/homebrew/bin/ffmpeg',
            'progress_hooks': [lambda d: self.progress_hook(d, thread_id, pause_event, stop_event)],
            'writeinfojson': True,
            'writethumbnail': True
        }
        try:
            with ytd.YoutubeDL(yt_opts) as ydl:
                info_dict = ydl.extract_info(vid_url, download=True)
                if info_dict and 'title' in info_dict:
                    return os.path.join(output_folder, f"{info_dict['title']}.mp4")
                else:
                    raise ValueError("Failed to extract video information")
        except Exception as e:
            return self.download_error(e, thread_id)

    def download_audiolist(self, playlist_url, output_folder, thread_id, pause_event, stop_event):
        yt_opts = {
            'verbose': True,
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_folder, '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'm4a'
            }],
            'ffmpeg_location': '/opt/homebrew/bin/ffmpeg',
            'progress_hooks': [lambda d: self.progress_hook(d, thread_id, pause_event, stop_event)],
            'noplaylist': False,
            'writeinfojson': True,
            'writethumbnail': True
        }
        try:
            with ytd.YoutubeDL(yt_opts) as ydl:
                info_dict = ydl.extract_info(playlist_url, download=False)
                if info_dict and 'entries' in info_dict:
                    playlist_items = []
                    for entry in info_dict['entries']:
                        entry_url = entry['webpage_url']
                        if entry_result := ydl.extract_info(
                            entry_url, download=True
                        ):
                            base_filename = os.path.join(output_folder, info_dict['title'], f"{entry_result.get('playlist_index', '')} - {entry_result.get('title', '')}")
                            playlist_items.append({
                                'audio': f"{base_filename}.m4a",
                                'json': f"{base_filename}.info.json",
                                'thumbnail': f"{base_filename}.jpg"
                            })
                    return playlist_items
                else:
                    raise ValueError("Failed to extract playlist information")
        except Exception as e:
            return self.download_error(e, thread_id)


    def download_vidlist(self, playlist_url, output_folder, thread_id, pause_event, stop_event):
        yt_opts = {
            'verbose': True,
            'format': 'bestvideo[height>=4320]+bestaudio/bestvideo+bestaudio/best',
            'outtmpl': os.path.join(output_folder, '%(playlist)s/%(playlist_index)s - %(title)s.%(ext)s'),
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }],
            'ffmpeg_location': '/opt/homebrew/bin/ffmpeg',
            'progress_hooks': [lambda d: self.progress_hook(d, thread_id, pause_event, stop_event)],
            'noplaylist': False,
            'writeinfojson': True,
            'writethumbnail': True
        }
        try:
            with ytd.YoutubeDL(yt_opts) as ydl:
                info_dict = ydl.extract_info(playlist_url, download=False)
                if not info_dict or 'entries' not in info_dict:
                    raise ValueError("Failed to extract playlist information")
                playlist_items = []
                for entry in info_dict['entries']:
                    entry_url = entry['webpage_url']
                    if entry_result := ydl.extract_info(entry_url, download=True):
                        base_filename = os.path.join(output_folder, info_dict['title'], f"{entry_result.get('playlist_index', '')} - {entry_result.get('title', '')}")
                        playlist_items.append({
                            'video': f"{base_filename}.mp4",
                            'json': f"{base_filename}.info.json",
                            'thumbnail': f"{base_filename}.jpg"
                        })
                    else:
                        print(f"Failed to extract info for {entry_url}")
                return playlist_items
        except Exception as e:
            return self.download_error(e, thread_id)

    def download_error(self, e, thread_id):
        print(f"Error during download: {str(e)}")
        self.app.signals.dld_error.emit(f"Download Error: {str(e)}", thread_id)
        return None

    def progress_hook(self, d, thread_id, pause_event, stop_event):
        try:
            if d['status'] == 'finished':
                self.app.signals.dld_progress.emit(thread_id, 100)
                self.app.signals.dld_status.emit("Download finished, now converting...", thread_id)
                print(f"Thread {thread_id}: Download finished, now converting...")
            elif d['status'] == 'downloading':
                downloaded = d.get('downloaded_bytes', 0)
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                if total > 0:
                    percent = int(downloaded / total * 100)
                    self.app.signals.dld_progress.emit(thread_id, percent)
                    self.app.signals.dld_status.emit(f"Downloading: {percent}% complete", thread_id)
                    print(f"Thread {thread_id}: Downloading: {percent}% complete ({downloaded}/{total} bytes)")
                else:
                    self.app.signals.dld_status.emit(f"Downloading: {downloaded} bytes", thread_id)
                    print(f"Thread {thread_id}: Downloading: {downloaded} bytes (total unknown)")
            elif d['status'] == 'error':
                error_msg = d.get('error', 'Unknown error')
                self.app.signals.dld_error.emit(error_msg, thread_id)
                print(f"Thread {thread_id}: Error - {error_msg}")
            
            # Check for pause and stop events
            if pause_event.is_set():
                print(f"Thread {thread_id}: Pause event is set")
            else:
                print(f"Thread {thread_id}: Pause event is not set")
            
            if pause_event.is_set():
                print(f"Thread {thread_id}: Paused")
                while pause_event.is_set() and not stop_event.is_set():
                    time.sleep(0.1)
            if stop_event.is_set():
                print(f"Thread {thread_id}: Stopped by user")
                raise Exception("Download stopped by user")

        except Exception as e:
            print(f"Thread {thread_id}: Progress hook error - {str(e)}")
            self.app.signals.dld_error.emit(f"Progress hook error: {str(e)}", thread_id)
            
    def start_new_download(self, download_type, dld_func):
        url = self.app.url_entry.text()
        
        if output_folder := QFileDialog.getExistingDirectory(
            self.app, "Select Directory"
        ):
            thread_id = len(self.app.progress_bars) + 1
            pause_event = threading.Event()
            stop_event = threading.Event()
            pause_event.clear()

            self.app.pause_events[thread_id] = pause_event
            self.app.stop_events[thread_id] = stop_event

            # Set up progress bar and controls for the download
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            progress_bar.setValue(0)

            label = QLabel(f"Status: Downloading {download_type}...")

            pause_butt = QPushButton()
            pause_icon = QIcon("../images/pause.svg")
            play_icon = QIcon("../images/play.svg")
            pause_butt.setIcon(pause_icon)
            pause_butt.setIconSize(QSize(15, 15))

            stop_butt = QPushButton()
            stop_icon = QIcon("../images/stop.svg")
            stop_butt.setIcon(stop_icon)
            stop_butt.setIconSize(QSize(15, 15))

            control_layout = QHBoxLayout()
            control_layout.addWidget(pause_butt)
            control_layout.addWidget(stop_butt)

            progress_widget = QWidget()
            progress_widget_layout = QVBoxLayout(progress_widget)
            progress_widget_layout.addWidget(label)
            progress_widget_layout.addWidget(progress_bar)
            progress_widget_layout.addLayout(control_layout)
            self.app.progress_layout.addWidget(progress_widget)

            self.app.progress_bars[thread_id] = (progress_bar, label, pause_event, stop_event)

            pause_butt.clicked.connect(lambda: self.toggle_pause(thread_id, pause_butt))
            stop_butt.clicked.connect(lambda: self.stop_dld(thread_id))
            
            def download_callback(thread_id, result):
                if isinstance(result, dict):
                    audio_file = result.get('audio')
                    json_file = result.get('json')
                    thumbnail_file = result.get('thumbnail')
                    
                    if audio_file and json_file and download_type in ['Audio', 'Audio Playlist']:
                        # Parse JSON and insert song data into database
                        song_data = reading_parsed_json(json_file)
                        insert_song(
                            audio_file, 
                            json_file,
                            song_data['title'],
                            song_data['artist'],
                            song_data['album'],
                            song_data['genre'],
                            thumbnail_file,
                            song_data['track_number'],
                            song_data['release_year'],
                            song_data['album_type'],
                            song_data['duration']
                        )
                        
                        # Update UI
                        self.app.file_manager.add_file_to_list(audio_file)
                    elif download_type in ['Video', 'Video Playlist']:
                        print(f"Video download completed: {audio_file}")
                    else:
                        print(f"Unexpected download type: {download_type}")
                else:
                    print(f"Unexpected result format: {result}")
                    
            self.app.signals.dld_finished.connect(download_callback)

            # Start the download thread
            dld_thread = threading.Thread(target=self.dld, args=(dld_func, url, output_folder, thread_id, pause_event, stop_event))
            dld_thread.start()

            self.app.url_entry.clear()

    def dld(self, dld_func, url, output_folder, thread_id, pause_event, stop_event):
        try:
            if result := dld_func(
                url, output_folder, thread_id, pause_event, stop_event
            ):
                self.app.signals.dld_finished.emit(thread_id, result)
                self.app.signals.dld_status.emit("Download Complete!", thread_id)
                self.app.signals.dld_progress.emit(thread_id, 100)
            else:
                self.app.signals.dld_error.emit("Download failed", thread_id)
        except Exception as e:
            print(f"Download error: {str(e)} for thread_id: {thread_id}")
            self.app.signals.dld_error.emit(str(e), thread_id)

    def toggle_pause(self, thread_id, pause_butt=None):
        if thread_id not in self.app.pause_events:
            print(f"Warning: No pause event found for thread_id {thread_id}")
            return

        pause_event = self.app.pause_events[thread_id]
        if pause_event.is_set():
            pause_event.clear()
            if pause_butt:
                pause_butt.setIcon(QIcon("images/play.svg"))
        else:
            pause_event.set()
            if pause_butt:
                pause_butt.setIcon(QIcon("images/pause.svg"))
            # Note: Don't emit the signal here to avoid infinite recursion

    def stop_dld(self, thread_id):
        if thread_id in self.app.stop_events:
            self.app.stop_events[thread_id].set()
        if thread_id in self.app.progress_bars:
            progress_bar, label, _, _ = self.app.progress_bars[thread_id]
            progress_bar.setValue(100)
            label.setText(f"Status: Download Complete! File: {self.app.file_paths}")
        # print(f"Download finished for thread {thread_id}. File: {self.app.file_paths}")
        self.app.signals.dld_stopped.emit(thread_id)

    def update_progress_bar(self):
        if pygame.mixer.music.get_busy():
            if current_track_name := self.music_player.get_track_name_from_index(
                self.app.curr_track_index
            ):
                track_length = self.music_player.get_track_length()
                if track_length > 0:
                    progress = pygame.mixer.music.get_pos() / 1000.0
                    self.app.prog_bar.setMaximum(track_length)
                    self.app.prog_bar.setValue(int(progress))
        else:
            self.music_player.next_music()

    def dld_audio_gui(self):
        # Start audio download
        self.start_new_download('Audio', self.download_audio)

    def dld_audiolist_gui(self):
        # Start audio playlist download
        self.start_new_download('Audio Playlist', self.download_audiolist)

    def dld_vid_gui(self):
        # Start video download
        self.start_new_download('Video', self.download_vid)

    def dld_vidlist_gui(self):
        # Start video playlist download
        self.start_new_download('Video Playlist', self.download_vidlist)