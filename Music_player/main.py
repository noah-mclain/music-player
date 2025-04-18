from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLineEdit, QListWidget, QHBoxLayout, QSlider, QProgressBar, QTabWidget, QSpacerItem, QSizePolicy, QLabel, QGridLayout, QScrollArea
from PyQt5.QtCore import Qt, QUrl, QSize, QTimer, QSettings
from PyQt5.QtGui import QIcon
from PyQt5.QtWebEngineWidgets import QWebEngineView
import sys
import platform
import ctypes
import pygame


# Component Imports
from download_manager import DownloadManager
from music_player import MusicPlayer
from file_manager import FileManager
from signals import DownloadSignals
from db_connection import get_db_connection

# from Foundation import NSObject
# from AppKit import NSApplicationDelegate

# class CustomDelegate(NSObject, NSApplicationDelegate):
#     def applicationSupportsSecureRestorableState_(self, application):
#         return objc.YES

class SecureApp(QApplication):
    def applicationSupportsSecureRestorableState(self):
        return True

# Main application class
class DownloaderApp(QWidget):
    def __init__(self):
        super().__init__()
        self.music_list = QListWidget()
        self.init_mixer()

        self.setWindowTitle("Music Player")

        # Initialize manager classes
        self.music_player = MusicPlayer(self)
        self.download_manager = DownloadManager(self, self.music_player)
        self.file_manager = FileManager(self, self.music_player, self.music_list)

         # Connect music list item events

        self.music_list.itemClicked.connect(self.music_player.on_music_selected)
        self.music_list.itemDoubleClicked.connect(self.music_player.play_selected_track)

        self.file_paths = self.file_manager.load_file_paths()
        self.paused = False
        self.tracks = list(self.file_paths.keys())

        # Timer for handling double-click on previous button
        self.double_click_timer = QTimer()
        self.double_click_timer.setInterval(300)
        self.double_click_timer.setSingleShot(True)
        self.double_click_timer.timeout.connect(self.music_player.single_click_prev)

        self.curr_playing_track = None

        self.bar_progress = 0

        # Timer for updating progress bar
        self.timer = QTimer()
        self.timer.timeout.connect(self.download_manager.update_progress_bar)

        self.file_manager.populate_music_list()
        self.music_list.currentRowChanged.connect(self.music_player.on_music_selected)


        # Music player state variables
        self.playback_positions = {}
        self.curr_track_index = -2

        self.initUI()

        # Dictionaries to manage downloads and their states
        self.download_counter = {}
        self.progress_bars = {}
        self.download_progress = {}
        self.pause_events = {}
        self.stop_events = {}

        # Initialize signals for download events
        self.signals = DownloadSignals()

        # Connect signals to slots
        self.signals.dld_progress.connect(self.update_progress)
        self.signals.dld_status.connect(self.update_status)
        self.signals.dld_finished.connect(self.download_manager.stop_dld)
        self.signals.dld_paused.connect(lambda thread_id: self.download_manager.toggle_pause(thread_id, None))
        self.signals.dld_resumed.connect(self.resume_dld)
        self.signals.dld_stopped.connect(self.download_manager.stop_dld)
        self.signals.dld_error.connect(self.show_download_error)

    def update_progress(self, thread_id, percent):
        if thread_id in self.progress_bars:
            progress_bar, _, _, _ = self.progress_bars[thread_id]
            progress_bar.setValue(percent)

    def update_status(self, thread_id, status):
        if thread_id in self.progress_bars:
            _, label, _, _ = self.progress_bars[thread_id]
            label.setText(f"Status: {status}")
        print(f"Status updated for thread {thread_id}: {status}")


    # def stop_dld(self, thread_id):
    #     if thread_id in self.stop_events:
    #         self.stop_events[thread_id].set()
    #     if thread_id in self.progress_bars:
    #         progress_bar, label, _, _ = self.progress_bars[thread_id]
    #         progress_bar.setValue(100)
    #         label.setText("Status: Download Stopped")

    # def pause_dld(self, thread_id):
    #     if thread_id in self.pause_events:
    #         self.pause_events[thread_id].clear()

    def resume_dld(self, thread_id):
        if thread_id in self.pause_events:
            self.pause_events[thread_id].set()

    def show_download_error(self, error_message, thread_id):
        if thread_id in self.progress_bars:
            _, label, _, _ = self.progress_bars[thread_id]
            label.setText(f"Error: {error_message}")
        # Emit the error to update the status
        self.signals.dld_status.emit(f"Download Error: {error_message}", thread_id)  # Fixed order

    def init_mixer(self):
        try:
            pygame.mixer.init()
            print("Pygame mixer initialized successfully.")
        except pygame.error as e:
            print(f"Error initializing Pygame mixer: {e}")

    def initUI(self):
        # Set up the main layout and tabs
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
            self.ui.restoreGeometry(geometry)
        if window_state:
            self.ui.restoreState(window_state)

    def save_window_settings(self):
        settings = QSettings('NadaAyman', 'MusicPlayer')
        settings.setValue('geometry', self.ui.saveGeometry())
        settings.setValue('windowState', self.ui.saveState())

    def init_dld_tab(self):
        # Set up the download tab UI
        layout = QVBoxLayout(self.dld_tab)
        self.setLayout(layout)

        self.url_entry = QLineEdit()
        layout.addWidget(self.url_entry)

        layout.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Fixed))
        
        self.dld_butt_container = QWidget()
        self.dld_buttons_layout = QGridLayout(self.dld_butt_container)
        layout.addWidget(self.dld_butt_container)

        # Create download buttons
        self.dld_audio_butt = QPushButton("Download Audio")
        self.dld_audio_butt.clicked.connect(self.download_manager.dld_audio_gui)
        self.dld_buttons_layout.addWidget(self.dld_audio_butt, 0, 0)

        self.dld_audiolist_butt = QPushButton("Download Audio Playlist")
        self.dld_audiolist_butt.clicked.connect(self.download_manager.dld_audiolist_gui)
        self.dld_buttons_layout.addWidget(self.dld_audiolist_butt, 0, 1)
        
        self.dld_vid_butt = QPushButton("Download Video")
        self.dld_vid_butt.clicked.connect(self.download_manager.dld_vid_gui)
        self.dld_buttons_layout.addWidget(self.dld_vid_butt, 0, 2)

        self.dld_vidlist_butt = QPushButton("Download Video Playlist")
        self.dld_vidlist_butt.clicked.connect(self.download_manager.dld_vidlist_gui)
        self.dld_buttons_layout.addWidget(self.dld_vidlist_butt, 0, 3)

        layout.addSpacerItem(QSpacerItem(20, 30, QSizePolicy.Minimum, QSizePolicy.Fixed))

        self.status_label = QLabel("Status: Idle")
        layout.addWidget(self.status_label)

        # Set up progress scroll area
        self.progress_scroll_area = QScrollArea(self)
        self.progress_scroll_area.setWidgetResizable(True)
        self.progress_widget = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_widget)
        self.progress_scroll_area.setWidget(self.progress_widget)
        layout.addWidget(self.progress_scroll_area)

        self.exit_butt = QPushButton("Exit")
        self.exit_butt.clicked.connect(self.exit_app)
        layout.addWidget(self.exit_butt)
        
    def exit_app(self):
        self.close()

    def init_music_player_tab(self):
        # Set up the music player tab UI
        layout = QVBoxLayout()
        self.music_player_tab.setLayout(layout)

        layout.addWidget(self.music_list)

        player_layout = QHBoxLayout()

        # Create player control buttons
        self.prev_butt = QPushButton()
        self.prev_icon = QIcon("../images/prev.svg")
        self.prev_butt.setIcon(self.prev_icon)
        self.prev_butt.setIconSize(QSize(50, 50))
        self.prev_butt.clicked.connect(self.music_player.prev_music)
        player_layout.addWidget(self.prev_butt)

        self.play_butt = QPushButton()
        self.play_icon = QIcon("../images/play.svg")
        self.pause_icon = QIcon("../images/pause.svg")
        self.play_butt.setIcon(self.play_icon)
        self.play_butt.setIconSize(QSize(50, 50))
        self.play_butt.clicked.connect(self.music_player.play_pause_music)
        player_layout.addWidget(self.play_butt)

        self.next_butt = QPushButton()
        self.next_icon = QIcon("../images/skip.svg")
        self.next_butt.setIcon(self.next_icon)
        self.next_butt.setIconSize(QSize(50, 50))
        self.next_butt.clicked.connect(self.music_player.next_music)
        player_layout.addWidget(self.next_butt)

        self.load_files_butt = QPushButton()
        self.load_icon = QIcon("../images/load.svg")
        self.load_files_butt.setIcon(self.load_icon)
        self.load_files_butt.setIconSize(QSize(50, 50))
        self.load_files_butt.clicked.connect(self.file_manager.load_files)
        player_layout.addWidget(self.load_files_butt)

        self.offload_files_butt = QPushButton()
        self.offload_icon = QIcon("../images/offload.svg")
        self.offload_files_butt.setIcon(self.offload_icon)
        self.offload_files_butt.setIconSize(QSize(50, 50))
        self.offload_files_butt.clicked.connect(self.file_manager.offload_files)
        player_layout.addWidget(self.offload_files_butt)

        layout.addLayout(player_layout)

        # Create volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(self.music_player.set_volume)
        layout.addWidget(self.volume_slider)

        # Create progress bar
        self.prog_bar = QProgressBar()
        self.prog_bar.setMinimum(0)
        self.prog_bar.setMaximum(100) 
        self.prog_bar.setTextVisible(False)
        layout.addWidget(self.prog_bar)

        self.download_manager.update_progress_bar()

        layout.update()
         # Ensure the layout is set and force an update
        self.music_player_tab.setLayout(layout)
        self.music_player_tab.updateGeometry()
            
    def init_browser_tab(self):
        # Set up the browser tab UI
        layout = QVBoxLayout()
        self.browser_tab.setLayout(layout)

        self.browser = QWebEngineView()
        self.browser.setUrl(QUrl("https://www.youtube.com"))
        layout.addWidget(self.browser)

    def closeEvent(self, event):
        # Save file paths and accept the close event
        self.file_manager.save_file_paths()
        event.accept()

if __name__ == '__main__' and platform.system() == "Darwin":
    ctypes.CDLL('/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices')
    app = SecureApp(sys.argv)

    get_db_connection()

    downloader = DownloaderApp()
    downloader.show()

    sys.exit(app.exec_())


