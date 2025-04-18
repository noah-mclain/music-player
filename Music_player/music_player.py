import os
import pygame
import time
from functools import lru_cache
from pydub import AudioSegment
from PyQt5.QtWidgets import QWidget, QListWidgetItem, QProgressBar, QLabel
from PyQt5.QtCore import QTimer

from data_operations import insert_song, retrieve_song, update_song, delete_music, get_song_by_artist, get_song_by_album, get_song_by_genre, get_all_song, reading_parsed_json


# Class to manage music playback operations
class MusicPlayer(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.time_label = QLabel(self)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_prog_bar)
        self.update_interval = 100
        self.track_start_time = 0
        self.current_track_length = 0
        self.track_lengths = {}

    def start_progress_timer(self):
        print("Starting progress timer")
        self.timer.start(self.update_interval)
        self.last_update_time = time.time()

    def stop_progress_timer(self):
        print("Stopping progress timer")
        self.timer.stop()

    def reset_progress_timer(self):
        if isinstance(self.app.prog_bar, QProgressBar):
            self.app.prog_bar.setValue(0) # resetting the progress bar

    def update_prog_bar(self):
        if pygame.mixer.music.get_busy():
            current_time = pygame.mixer.music.get_pos() / 1000
            total_length = self.current_track_length  # Assuming total_length is stored when the track starts

            if total_length is not None and total_length > 0:
                progress = min(100, (current_time / total_length) * 100)
            else:
                progress = 0

            self.app.prog_bar.setValue(int(progress))
            
            # Update the time labels
            current_time_str = time.strftime('%M:%S', time.gmtime(current_time))
            total_time_str = time.strftime('%M:%S', time.gmtime(total_length))
            self.time_label.setText(f"{current_time_str} / {total_time_str}")

            # For debugging
            print(f"Progress: {progress:.2f}% (Current: {current_time:.2f}s, Total: {total_length:.2f}s)")

    def get_track_name_from_index(self, index):
        return self.app.tracks[index] if 0 <= index < len(self.app.tracks) else None

    @lru_cache(maxsize=None)
    def get_track_length(self, file_path):
        if file_path not in self.track_lengths:
            if os.path.exists(file_path):
                try:
                    audio = AudioSegment.from_file(file_path)
                    self.track_lengths[file_path] = len(audio) / 1000 
                except Exception as e:
                    print(f"Error getting track length: {e}")
                    self.track_lengths[file_path] = 0
            else:
                self.track_lengths[file_path] = 0
            return self.track_lengths[file_path]

    # def get_track_name_from_index(self, index):
    #     all_songs = get_all_song()
    #     return all_songs[index][2] if 0 <= index < len(all_songs) else None
    #     # if 0 <= index < len(self.app.tracks):
    #     #     return self.app.tracks[index]
    #     # return None

    def on_music_selected(self, item: QListWidgetItem):
        # Ensure the passed item is a QListWidgetItem
        if isinstance(item, QListWidgetItem):
            index = self.app.music_list.row(item)
            self.curr_track_index = index
            
    def play_selected_track(self, item: QListWidgetItem | None = None):
        if item is None:
            item = self.app.music_list.currentItem()

        if isinstance(item, QListWidgetItem):
            title = item.text()
            if song_data := retrieve_song({'title': title}):
                file_path = song_data[0][1] # Assuming file_path is the second column
                self.app.curr_playing_track = title

                print(f"Playing: {title}")

                if os.path.exists(file_path):
                    self.start_song(file_path)
                else:
                    print(f"File not found: {file_path}")
            else:
                print(f"No song data found for {title}")

    def start_song(self, file_path):
        pygame.mixer.music.load(file_path)
        pygame.mixer.music.play()
        self.current_track_length = self.get_track_length(file_path)
        self.reset_progress_timer()
        self.start_progress_timer()
        pygame.mixer.music.set_endevent(pygame.USEREVENT)
        self.app.paused = False
        self.app.play_butt.setIcon(self.app.pause_icon)

    # def play_selected_track(self, item: QListWidgetItem = None):
    #     # Play the selected track
    #     if item is None:
    #         item = self.app.music_list.currentItem()

    #     if isinstance(item, QListWidgetItem):
    #         index = self.app.music_list.row(item)
    #         self.app.curr_track_index = index
    #         title = item.text()
    #         file_path = self.app.file_paths.get(title, "")
    #         self.app.curr_playing_track = title

    #         print(f"Playing: {title}")

    #         if file_path:
    #             if os.path.exists(file_path):
    #                 pygame.mixer.music.load(file_path)
    #                 pygame.mixer.music.play()
    #                 self.current_track_length = self.get_track_length(file_path)
    #                 self.reset_progress_timer()
    #                 self.start_progress_timer()  # Start the timer when playing a track
    #                 pygame.mixer.music.set_endevent(pygame.USEREVENT)
    #                 self.app.paused = False
    #                 self.app.play_butt.setIcon(self.app.pause_icon)
    #             else:
    #                 print(f"File not found: {file_path}")
    #         else:
    #             print(f"File path not found for title: {title}")

    def play_pause_music(self, from_button_click=False, from_next_prev=False):
        if pygame.mixer.music.get_busy():
            if self.app.paused and not from_button_click:
                self.resume_music()
            elif not from_button_click and not from_next_prev:
                pygame.mixer.music.pause()
                self.stop_progress_timer()  # Stop the timer when pausing
                self.app.paused = True
                self.app.play_butt.setIcon(self.app.play_icon)
        elif self.app.paused:
            if not from_button_click:
                self.resume_music()
        else:
            self.play_selected_track()
            self.start_progress_timer()  # Start the timer when playing

    def resume_music(self):
        pygame.mixer.music.unpause()
        self.start_progress_timer()  # Restart the timer when unpausing
        self.app.paused = False
        self.app.play_butt.setIcon(self.app.pause_icon)

    def single_click_prev(self):
        self.rewind_track()
        self.reset_progress_timer()

    def rewind_track(self):
        pygame.mixer.music.rewind()

    def prev_music(self):
        # Play the previous track or restart the current track
        if self.app.double_click_timer.isActive():
            self.double_click_prev()
        else:
            # Single click, restart current song
            self.app.double_click_timer.start()
            self.rewind_track()
            self.reset_progress_timer()

    def double_click_prev(self):
        # Double click detected, play previous song
        self.app.double_click_timer.stop()
        all_songs = get_all_song()
        if not all_songs:
            print("No songs available")
            return 
        
        self.app.curr_track_index -= 1
        if self.app.curr_track_index < 0:
            self.app.curr_track_index = len(all_songs) - 1

        self.play_song(all_songs)
        
        # if self.app.double_click_timer.isActive():
        #     self.app.double_click_timer.stop()
        #     self.play_previous_track()
        # else:
        #     self.app.double_click_timer.start()

    def stop_music(self):
        pygame.mixer.music.stop()
        self.app.paused = False
        self.app.play_butt.setIcon(self.app.play_icon)
        self.stop_progress_timer()
        self.reset_progress_timer()

    def play_previous_track(self):
        # Play the previous track in the playlist
        self.app.curr_track_index -= 1
        if self.app.curr_track_index < 0:
            self.app.curr_track_index = self.app.music_list.count() - 1

        self.app.music_list.setCurrentRow(self.app.curr_track_index)
        self.play_selected_track()

    def next_music(self):
        # Play the next track in the playlist
        all_songs = get_all_song()
        if not all_songs:
            print("No songs available")
            return
        
        self.app.curr_track_index += 1
        if self.app.curr_track_index >= len(all_songs):
            self.app.curr_track_index = 0

        self.play_song(all_songs)

    def play_song(self, all_songs):
        if 0 <= self.app.curr_track_index < len(all_songs):
            curr_song = all_songs[self.app.curr_track_index]
            self.app.music_list.setCurrentRow(self.app.curr_track_index)
            self.play_selected_track(QListWidgetItem(curr_song[2]))
        else:
            print(f"Invalid track index: {self.app.curr_track_index}")
        # self.app.curr_track_index += 1
        # if self.app.curr_track_index >= self.app.music_list.count():
        #     self.app.curr_track_index = 0

        # self.app.music_list.setCurrentRow(self.app.curr_track_index)
        # self.play_selected_track()

    def set_volume(self, value):
        # Set the volume of the music player
        pygame.mixer.music.set_volume(value / 100.0)