import asyncio
import sys
import threading
from ui.controls import Controls
from ui.torrent_info_ui import TorrentInfoUi
from ui.dashboard import TorrentDashboard

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout,  QFileDialog
)

from torrent import Torrent

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Torrent Client")
        self.setMinimumSize(600, 400)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.info = TorrentInfoUi()
        self.controls = Controls(self.browse, self.start)

        layout.addWidget(self.info)
        layout.addWidget(self.controls)

    def browse(self):

        try:

            path, _ = QFileDialog.getOpenFileName(self, "Pick a torrent", "",   "Torrent files (*.torrent)")

            if path:
                self.torrent = Torrent(path)

                self.info.update(self.torrent.torrent_info.decoded_tf)

        except Exception as e:
            print("something wrong with torrent file info class",{e})


    def start(self):

        self.dashboard = TorrentDashboard(self.torrent)

        self.setCentralWidget(self.dashboard)

        threading.Thread(
            target=lambda: asyncio.run(self.torrent.run_torrent()),
            daemon=True
            ).start()





app = QApplication(sys.argv)
win = MainWindow()
win.show()
sys.exit(app.exec())