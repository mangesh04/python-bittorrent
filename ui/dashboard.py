from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QScrollArea,
    QProgressBar
)
from PySide6.QtGui import QPainter,QColor


class PieceMap(QWidget):
    def __init__(self, num_pieces):
        super().__init__()
        self.num_pieces = num_pieces
        self.downloaded = set()
        self.in_progress=set()
        self.square_size = 5
        self.gap = 1

    def paintEvent(self, event):
        painter = QPainter(self)
        cols = self.width() // (self.square_size + self.gap)

        for i in range(self.num_pieces):
            row = i // cols
            col = i % cols
            x = col * (self.square_size + self.gap)
            y = row * (self.square_size + self.gap)

            if i in self.downloaded:
                painter.fillRect(x, y, self.square_size, self.square_size, QColor("#a5d6a7"))  # green
            elif i in self.in_progress:
                painter.fillRect(x, y, self.square_size, self.square_size, QColor("#F5A623"))  # green
            else:
                painter.fillRect(x, y, self.square_size, self.square_size, QColor("#444444"))  # gray

    def update_pieces(self,in_progress, downloaded):
        self.downloaded = downloaded
        self.in_progress=in_progress
        self.update()  # triggers repaint

class DashLable(QLabel):

    def __init__(self,string):
        super().__init__()
        self.setFixedHeight(30)
        self.setText(string)


class TorrentDashboard(QWidget):

    """responsible for displaying torrent info and controls"""

    def __init__(self, torrent):
        super().__init__()

        self.torrent = torrent
        self.stats = torrent.stats

        self.layout = QVBoxLayout(self)

        self.layout.addWidget(DashLable(f"Number of peers ip,port we have: {self.stats.number_of_all_peers}"))

        self.layout.addWidget(DashLable(f"Number of peers we connected: {self.stats.connection_count}"))
        self.layout.addWidget(DashLable(f"Number of successful handshakes: {self.stats.successful_handshakes}"))
        self.layout.addWidget(DashLable(f"download connections : {self.stats.download_connections}"))
        self.layout.addWidget(DashLable(f"Pieces downloaded : {self.stats.pieces_downloaded_count}"))

        self.piece_map=PieceMap(torrent.torrent_info.bitfield_length)
        self.layout.addWidget(self.piece_map)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def update_stats(self):

        def set_label(index, text, value, color):

            widget = self.layout.itemAt(index).widget()

            widget.setText(text)

            widget.setStyleSheet(f"color: {color};" if value > 0 else "")

        set_label(0, f"Number of peers ip,port we have: {self.stats.number_of_all_peers}",
                  self.stats.number_of_all_peers, "#4fc3f7")

        set_label(1, f"Number of peers we connected: {self.stats.connection_count}",
                  self.stats.connection_count, "#ce93d8")

        set_label(2, f"Number of successful handshakes: {self.stats.successful_handshakes}",
                  self.stats.successful_handshakes, "#80cbc4")

        set_label(3, f"download connections: {self.stats.download_connections}",
                  self.stats.download_connections, "#ffb74d")

        set_label(4, f"Pieces downloaded : {len(self.torrent.peers.piece_downloaded)}/{self.torrent.torrent_info.total_pieces}",
                  len(self.torrent.peers.piece_downloaded), "#a5d6a7")

        self.piece_map.update_pieces(self.torrent.peers.piece_in_progress,self.torrent.peers.piece_downloaded)
