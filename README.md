# Music Player

A modern, modular music player and downloader built with Python and PyQt5.  
Play music, download tracks with progress indicators, and manage playback in a clean, responsive interface.

---

## Features

- **Play/Pause/Stop Controls**  
  Control local audio playback with a simple, intuitive interface.

- **Download Manager**  
  Download music from URLs using yt-dlp with real-time progress bars and status updates.

- **Multithreaded Downloads**  
  Each download runs in its own thread to keep the UI responsive.

- **Persistent Metadata**  
  Store downloaded song metadata in a lightweight SQLite database.

- **FFmpeg Integration**  
  Ensures support for a wide range of audio formats.

- **Modular Codebase**  
  Cleanly separated components for easy extension and maintenance.

---

## Technologies Used

- Python 3.11+  
- PyQt5  
- yt-dlp  
- FFmpeg  
- SQLite  
- threading  
- requests

---

## Setup Instructions

1. **Clone the Repository**
   ```bash
   git clone https://github.com/noah-mclain/music-player.git
   cd music-player
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
3. **Install FFmpeg**
   [Download FFmpeg](https://ffmpeg.org/download.html) and add it to your system path.
   

4. **Run the App**
   ```bash
   python3 Music_player/main.py
   ```

---

## Folder Structure

music-player/
├── main.py               # Entry point
├── player.py             # Playback logic
├── downloader.py         # Download logic with threading
├── database/             # SQLite integration
├── ui/                   # UI layout and assets
└── README.md

---

## Future Improvements

	•	Playlist support
	•	Pause/resume downloads
	•	Drag-and-drop interface
	•	Album art display
	•	Song metadata editing

---

## License

MIT License

---

## Author

**Nada Mohamed**

