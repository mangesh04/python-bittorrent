from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QGroupBox,
    QScrollArea,
    QApplication
)


class TorrentInfoUi(QWidget):

    def __init__(self):
        super().__init__()

        main_layout = QVBoxLayout(self)

        # scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        # container inside scroll
        container = QWidget()
        self.info_layout = QVBoxLayout(container)

        scroll.setWidget(container)

        main_layout.addWidget(scroll)

    def update(self, info: dict, parent_layout=None):

        if parent_layout is None:
            parent_layout = self.info_layout

        info = self.decode(info)

        for key, value in info.items():

            if key in ['pieces', 'piece length']:
                continue

            # nested dictionary
            if isinstance(value, dict):

                group = QGroupBox(str(key))
                layout = QVBoxLayout(group)

                parent_layout.addWidget(group)

                self.update(value, layout)

                continue

            # normal values
            group = QGroupBox(str(key))
            layout = QVBoxLayout(group)

            label = QLabel(str(value))
            label.setWordWrap(True)

            layout.addWidget(label)

            parent_layout.addWidget(group)

    def decode(self, value):

        if isinstance(value, bytes):
            return value.decode(errors="ignore")

        elif isinstance(value, dict):
            return {
                self.decode(k): self.decode(v)
                for k, v in value.items()
            }

        elif isinstance(value, list):
            return [self.decode(i) for i in value]

        return value