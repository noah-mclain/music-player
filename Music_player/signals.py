from PyQt5.QtCore import pyqtSignal, QObject


class DownloadSignals(QObject):
    dld_progress = pyqtSignal(int, int)  # signal to indicate download progress
    dld_status = pyqtSignal(str, int)
    dld_finished = pyqtSignal(int, str)  # signal to indicate that download finished
    dld_paused = pyqtSignal(int)
    dld_resumed = pyqtSignal(int)
    dld_stopped = pyqtSignal(int)
    dld_error = pyqtSignal(str, int)