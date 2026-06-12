from PySide6.QtWidgets import (
     QWidget,
    QVBoxLayout,  QPushButton
)

class Controls(QWidget):
    """responsible for buttons"""
    def __init__(self, on_browse, on_start):
        super().__init__()
        layout = QVBoxLayout(self)

        browse_btn = QPushButton("Browse .torrent")
        browse_btn.clicked.connect(on_browse)

        start_btn = QPushButton("Start Download")
        start_btn.clicked.connect(on_start)

        layout.addWidget(browse_btn)
        layout.addWidget(start_btn)
