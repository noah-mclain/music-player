from PyQt5.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLineEdit, QHBoxLayout, QSlider, QProgressBar, QTabWidget, QSpacerItem, QSizePolicy, QLabel, QGridLayout, QScrollArea, QListWidget
from PyQt5.QtCore import Qt, QUrl, QSize, QSettings, QTimer
from PyQt5.QtGui import QIcon, QKeyEvent
from PyQt5.QtWebEngineWidgets import QWebEngineView
import json
from pydub import AudioSegment
from signals import DownloadSignals
from download_manager import DownloadManager
from file_manager import FileManager
from music_player import MusicPlayer
import pygame

class UIComponents(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize GUI components
        self.music_list = QListWidget()
        self.prog_bar = QProgressBar()
        self.play_butt = QPushButton("Play")  # Assuming play_butt is a button

        # Initialize MusicPlayer with required arguments
        self.mp = MusicPlayer(self)

        # Initialize Signals and Download Manager
        self.signals = DownloadSignals()
        self.download_manager = DownloadManager(self.signals)
        
        # Initialize FileManager with `self` and then proceed with UI setup
        self.fm = FileManager(self)
        
        # Initialize the UI components and mixer
        self.init_ui()
        self.mp.init_mixer()
        
        self.file_paths = self.fm.load_file_paths()
        self.tracks = list(self.file_paths.keys())

        # Timers
        self.double_click_timer = QTimer()
        self.double_click_timer.setInterval(300)
        self.double_click_timer.setSingleShot(True)
        self.double_click_timer.timeout.connect(self.mp.single_click_prev)

        self.timer = QTimer()
        self.timer.timeout.connect(self.mp.update_progress_bar)

        # Populate music list and connect signals
        self.fm.populate_music_list()
        self.music_list.currentRowChanged.connect(self.mp.on_music_selected)
        self.music_list.itemClicked.connect(self.mp.on_music_selected)

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.music_player_tab = QWidget()
        self.dld_tab = QWidget()
        self.browser_tab = QWidget()
    
        self.tabs.addTab(self.music_player_tab, "Music Player")
        self.tabs.addTab(self.dld_tab, "Download")
        self.tabs.addTab(self.browser_tab, "Browser")

        self.init_music_player_tab()
        self.init_dld_tab()
        self.init_browser_tab()

        self.load_window_settings()

    def load_window_settings(self):
        settings = QSettings('NadaAyman', 'MusicPlayer')
        geometry = settings.value('geometry')
        window_state = settings.value('windowState')

        if geometry:
            self.restoreGeometry(geometry)
        if window_state:
            self.restoreState(window_state)

    def save_window_settings(self):
        settings = QSettings('NadaAyman', 'MusicPlayer')
        settings.setValue('geometry', self.saveGeometry())
        settings.setValue('windowState', self.saveState())

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_Escape:
            self.showNormal()

    def closeEvent(self, event):
        self.save_window_settings()
        event.accept()

    def init_music_player_tab(self):
        layout = QVBoxLayout()
        self.music_player_tab.setLayout(layout)

        layout.addWidget(self.music_list)

        player_layout = QHBoxLayout()

        self.prev_butt = QPushButton()
        self.prev_icon = QIcon("images/prev.svg")
        self.prev_butt.setIcon(self.prev_icon)
        self.prev_butt.setIconSize(QSize(50, 50))
        self.prev_butt.clicked.connect(self.mp.prev_music)
        player_layout.addWidget(self.prev_butt)

        self.play_butt = QPushButton()
        self.play_icon = QIcon("images/play.svg")
        self.pause_icon = QIcon("images/pause.svg")
        self.play_butt.setIcon(self.play_icon)
        self.play_butt.setIconSize(QSize(50, 50))
        self.play_butt.clicked.connect(self.mp.play_pause_music)
        player_layout.addWidget(self.play_butt)

        self.next_butt = QPushButton()
        self.next_icon = QIcon("images/skip.svg")
        self.next_butt.setIcon(self.next_icon)
        self.next_butt.setIconSize(QSize(50, 50))
        self.next_butt.clicked.connect(self.mp.next_music)
        player_layout.addWidget(self.next_butt)

        self.load_files_butt = QPushButton()
        self.load_icon = QIcon("images/load.svg")
        self.load_files_butt.setIcon(self.load_icon)
        self.load_files_butt.setIconSize(QSize(50, 50))
        self.load_files_butt.clicked.connect(self.fm.load_files)
        player_layout.addWidget(self.load_files_butt)

        self.offload_files_butt = QPushButton()
        self.offload_icon = QIcon("images/offload.svg")
        self.offload_files_butt.setIcon(self.offload_icon)
        self.offload_files_butt.setIconSize(QSize(50, 50))
        self.offload_files_butt.clicked.connect(self.fm.offload_files)
        player_layout.addWidget(self.offload_files_butt)

        layout.addLayout(player_layout)

        # volume slider
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self.set_volume)
        layout.addWidget(self.volume_slider)

        # progress bar
        self.prog_bar = QProgressBar()
        # setting default values for the progress bar
        self.prog_bar.setMinimum(0)
        self.prog_bar.setMaximum(100) 
        self.prog_bar.setTextVisible(False)
        layout.addWidget(self.prog_bar)

        self.mp.update_progress_bar()

        layout.update()
        self.music_player_tab.layout().invalidate()


    def start_progress_timer(self):
        print("Starting progress timer")
        self.timer.start(100) # update every 10th of a second

    def stop_progress_timer(self):
        print("Stopping progress timer")
        self.timer.stop()

    def reset_progress_timer(self):
        if isinstance(self.prog_bar, QProgressBar):
            self.prog_bar.setValue(0) # resetting the progress bar

    def get_track_name_from_index(self, index):
        if 0 <= index < len(self.tracks):
            return self.tracks[index]
        return None

    def get_track_length(self):
        if self.mp.curr_playing_track:
            file_path = self.file_paths.get(self.mp.curr_playing_track, "")
            if file_path:
                try:
                    audio = AudioSegment.from_file(file_path)
                    return len(audio) // 1000  # Convert milliseconds to seconds
                except Exception as e:
                    print(f"Error getting track length: {e}")
                    return 300  # Default length in seconds
        return 300

    def set_volume(self, value):
        pygame.mixer.music.set_volume(value / 100.0)

    def init_dld_tab(self):
        layout = QVBoxLayout(self.dld_tab)
        self.setLayout(layout)  # Set the layout for the main window

        self.url_entry = QLineEdit()
        layout.addWidget(self.url_entry)

        # Spacer to ensure no overlap between URL entry and buttons
        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        
        # create a container for the download buttons
        self.dld_butt_container = QWidget()
        self.dld_buttons_layout = QGridLayout(self.dld_butt_container)
        layout.addWidget(self.dld_butt_container)

        # adding button to download a single audio file from a yt video
        self.dld_audio_butt = QPushButton("Download Audio")
        self.dld_audio_butt.clicked.connect(self.dld_audio_gui)
        self.dld_buttons_layout.addWidget(self.dld_audio_butt, 0, 0)

        # adding button to download a playlist of audio files from a playlist of yt videos
        self.dld_audiolist_butt = QPushButton("Download Audio Playlist")
        self.dld_audiolist_butt.clicked.connect(self.dld_audiolist_gui)
        self.dld_buttons_layout.addWidget(self.dld_audiolist_butt, 0, 1)
        
        # adding button to download a single yt video
        self.dld_vid_butt = QPushButton("Download Video")
        self.dld_vid_butt.clicked.connect(self.dld_vid_gui)
        self.dld_buttons_layout.addWidget(self.dld_vid_butt, 0, 2)

        # add button to download playlist of yt videos
        self.dld_vidlist_butt = QPushButton("Download Video Playlist")
        self.dld_vidlist_butt.clicked.connect(self.dld_vidlist_gui)
        self.dld_buttons_layout.addWidget(self.dld_vidlist_butt, 0, 3)

        layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed))

        # add download progress and status indicators
        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)

        # Scroll area for the progress bars
        self.progress_scroll_area = QScrollArea(self)
        self.progress_scroll_area.setWidgetResizable(True)
        self.progress_widget = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_widget)
        self.progress_scroll_area.setWidget(self.progress_widget)
        layout.addWidget(self.progress_scroll_area)


        # # add a spacer to push the exit button down to make room for dld progress
        # layout.addSpacerItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Expanding))
    
        # adding an exit button for the user to exit the program
        self.exit_butt = QPushButton("Exit")
        self.exit_butt.clicked.connect(self.close)
        layout.addWidget(self.exit_butt)

    def init_browser_tab(self):
        layout = QVBoxLayout()
        self.browser_tab.setLayout(layout)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://www.youtube.com"))
        layout.addWidget(self.browser)

    def dld_audio_gui(self):
        self.start_new_download('Audio', self.download_audio)

    def dld_audiolist_gui(self):
        self.start_new_download('Audio Playlist', self.download_audiolist)

    def dld_vid_gui(self):
        self.start_new_download('Video', self.download_vid)

    def dld_vidlist_gui(self):
        self.start_new_download('Video Playlist', self.download_vidlist)

    def save_file_paths(self):
        # Save the file paths dictionary to file_paths.json
        with open('file_paths.json', 'w', encoding='utf-8') as f:
            json.dump(self.file_paths, f, indent=4, ensure_ascii=False)
        
        print("File paths saved")

    def closeEvent(self, event):
        self.save_file_paths()
        event.accept()

