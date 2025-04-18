from pydub import AudioSegment
import os
import json
from PyQt5.QtWidgets import QFileDialog, QMenu, QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QMessageBox
import PyQt5.QtCore 

from data_operations import insert_song, retrieve_song, get_all_song, delete_music, reading_parsed_json, update_song

# Class to manage file operations
class FileManager:
    def __init__(self, app, music_player, music_list):
        self.app = app
        self.music_player = music_player
        self.music_list = music_list
        self.setup_context_menu()

    def load_file_paths(self):          
        try:
            with open('file_paths.json', 'r', encoding='utf-8') as f:
                self.app.file_paths = json.load(f)
                self.populate_music_list()
                return self.app.file_paths
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Error loading file paths: {e}")
            return {}
    
    def populate_music_list(self):
        if not hasattr(self, 'music_list'):
            print("music_list is not initialized.")
            return
        
        self.music_list.clear()  # Clear existing items
        
        songs = get_all_song()
        for song in songs:
            self.music_list.addItem(song[2])
            
        # Confirm population
        print(f"Number of items in music_list after populating: {self.music_list.count()}")
    

    def save_file_paths(self):
        # with open('file_paths.json', 'w', encoding='utf-8') as f:
        #     json.dump(self.app.file_paths, f, indent=4, ensure_ascii=False)
        # print("File paths saved")
        pass

    def load_files(self):
        # Load audio files into the playlist
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.ExistingFiles)
        file_dialog.setNameFilter("Audio Files (*.m4a *.mp3 *.wav *.ogg *.flac *.alac *.wma)")

        if file_dialog.exec_():
            self.add_files_to_list(file_dialog)

    def add_files_to_list(self, file_dialog):
        selected_files = file_dialog.selectedFiles()
        for file_path in selected_files:
            file_name_exten = os.path.basename(file_path)
            file_name, file_exten = os.path.splitext(file_name_exten)
            base_path = os.path.splitext(file_path)[0]

            print(f"Loading file: {file_name} ({file_exten})")
            
            # Check for metadata JSON file and webp thumbnail
            json_path = f"{base_path}.info.json"
            thumbnail_path = f"{base_path}.webp"

            # Convert M4A files to WAV if needed
            actual_file_path = file_path
            if file_exten.lower() == '.m4a':
                if wav_file_path := self.convert_to_wav(file_path):
                    actual_file_path = wav_file_path
                else:
                    print(f"Conversion unsuccessful for {file_name}")
                    continue

            # Insert into database
            success = False
            if not os.path.exists(json_path):
                print(f"No JSON metadata found for {file_name}, adding with basic info")
                success = insert_song(
                    actual_file_path, 
                    None,
                    file_name,
                    "",
                    "",
                    "",
                    None,
                    None,
                    None,
                    None,
                    None
                )
            else:
                song_data = reading_parsed_json(json_path)
                success = insert_song(
                    actual_file_path,
                    json_path,
                    song_data['title'],
                    song_data['artist'],
                    song_data['album'],
                    song_data['genre'],
                    thumbnail_path if os.path.exists(thumbnail_path) else None,
                    song_data['track_number'],
                    song_data['release_year'],
                    song_data['album_type'],
                    song_data['duration']
                )

            if success:
                # Only update UI and file_paths if database insert was successful
                self.app.file_paths[file_name] = actual_file_path
                print(f"Adding {file_name} to music list")
                self.music_list.addItem(file_name)
            else:
                print(f"Failed to add {file_name} to database")


    def offload_files(self):
        # Remove selected files from the playlist
        selected_items = self.music_list.selectedItems()

        if not selected_items:
            print("No song selected for removal")
            return

        for item in selected_items:
            song_name = item.text()
            print(f"Attempting to remove: {song_name}")

            # Get song data from database
            song_data = retrieve_song({'title': song_name})
            if song_data and len(song_data) > 0:
                song_id = song_data[0][0]
                
                if delete_music(song_id):
                    row.self.music_list.row(item)
                    self.music_list.takeItem(row)
                    
                    if song_name in self.app.file_paths:
                        del self.app.file_paths[song_name]
                        
                    print(f"Successfully removed: {song_name}")
                else:
                    print(f"Failed to remove {song_name}")
            else:
                print(f"Song not found in database: {song_name}")
            
            # Remove from UI
            row = self.music_list.row(item)
            self.music_list.takeItem(row)
            print(f"Removing {song_name} from music list")

            # Stop playback if this was the current song
            if song_name == self.music_player.get_track_name_from_index(self.app.curr_track_index):
                self.music_player.stop_music()
                print(f"Stopped playing {song_name} because it is being offloaded.")

        self.save_file_paths()

    def convert_to_wav(self, file_path):
        # Convert m4a files to wav format
        audio = AudioSegment.from_file(file_path, format='m4a')
        file_path = file_path.replace('m4a', 'wav')
        audio.export(file_path, format='wav')
        return file_path
    
    def setup_context_menu(self):
        self.music_list.setContextMenuPolicy(PyQt5.QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        self.music_list.customContextMenuRequested.connect(self.show_context_menu)

    def show_context_menu(self, position):
        menu = QMenu()
        edit_action = menu.addAction("Edit Details")
        
        action = menu.exec_(self.music_list.mapToGlobal(position))
        
        if action == edit_action:
            current_item = self.music_list.itemAt(position)
            if current_item:
                self.show_edit_dialog(current_item.text())

    def show_edit_dialog(self, song_title):
        # Get current song details
        song_data = retrieve_song({'title': song_title})
        if not song_data or len(song_data) == 0:
            QMessageBox.warning(self.music_list, "Error", "Could not find song details") 
            return

        song = song_data[0]  # Get first matching song
        # Create dialog
        dialog = QDialog(self.music_list)
        dialog.setWindowTitle("Edit Song Details")
        layout = QVBoxLayout()

        # Create input fields for all song details
        fields = {
            'File Path': (QLineEdit(song[1]), 'file_path'),  # song[1] is file_path
            'Title': (QLineEdit(song[2]), 'title'),  # song[2] is title
            'Artist': (QLineEdit(song[3]), 'artist'),  # song[3] is artist
            'Album': (QLineEdit(song[4]), 'album'),  # song[4] is album
            'Genre': (QLineEdit(song[5]), 'genre'),  # song[5] is genre
            'Track Number': (QLineEdit(str(song[7]) if song[7] else ''), 'track_number'),  # song[7] is track_number
            'Total Tracks': (QLineEdit(str(song[11]) if song[11] else ''), 'total_tracks'), # song[11] is total_tracks
            'Release Year': (QLineEdit(str(song[8]) if song[8] else ''), 'release_year'),  # song[8] is release_year
            'Album Type': (QLineEdit(song[9] if song[9] else ''), 'album_type'),  # song[9] is album_type
            'Duration': (QLineEdit(str(song[10]) if song[10] else ''), 'duration')  # song[10] is duration
        }

        # Add widgets to layout
        input_widgets = {}
        for label_text, (widget, field_name) in fields.items():
            label = QLabel(f"{label_text}:")
            layout.addWidget(label)
            layout.addWidget(widget)
            input_widgets[field_name] = widget

        # Add save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(lambda: self.save_song_details(
            song[0],  # song ID
            {field: widget.text() for field, widget in input_widgets.items()},
            dialog
        ))
        layout.addWidget(save_button)

        dialog.setLayout(layout)
        dialog.exec_()

    def save_song_details(self, song_id, new_values, dialog):
        try:
            # Prepare updates for different tables
            song_updates = {}
            album_updates = {}
            
            # Process numeric fields
            if new_values['track_number']:
                try:
                    song_updates['track_number'] = int(new_values['track_number'])
                except ValueError:
                    song_updates['track_number'] = None
                    
            if new_values['total_tracks']:
                try:
                    song_updates['total_tracks'] = int(new_values['total_tracks'])
                except ValueError:
                    song_updates['total_tracks'] = None
                    
            if new_values['duration']:
                try:
                    song_updates['duration'] = float(new_values['duration'])
                except ValueError:
                    song_updates['duration'] = None

            # Process text fields
            song_updates.update({
                'file_path': new_values['file_path'],
                'title': new_values['title']
            })

            # Album-related updates
            if new_values['album']:
                album_updates['album'] = new_values['album']
            if new_values['release_year']:
                try:
                    album_updates['release_year'] = int(new_values['release_year'])
                except ValueError:
                    album_updates['release_year'] = None
            if new_values['album_type']:
                album_updates['album_type'] = new_values['album_type']

            # Update song details in database
            update_song(
                song_id,
                title=new_values['title'],
                artist=new_values['artist'],
                album=new_values['album'],
                genre=new_values['genre'],
                file_path=new_values['file_path'],
                track_number=song_updates.get('track_number'),
                total_tracks=album_updates.get('total_tracks'),
                duration=song_updates.get('duration'),
                release_year=album_updates.get('release_year'),
                album_type=album_updates.get('album_type')
            )
            
            # Update UI
            current_item = self.music_list.currentItem()
            if current_item:
                current_item.setText(new_values['title'])
                
            # Update file_paths dictionary if title changed
            old_title = current_item.text()
            if old_title in self.app.file_paths:
                file_path = self.app.file_paths[old_title]
                del self.app.file_paths[old_title]
                self.app.file_paths[new_values['title']] = new_values['file_path']

            dialog.accept()
            QMessageBox.information(self.music_list, "Success", "Song details updated successfully")
        except Exception as e:
            QMessageBox.warning(self.music_list, "Error", f"Failed to update song details: {str(e)}")