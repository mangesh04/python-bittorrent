import asyncio

class ConnectionStat:
    def __init__(self):
        self.pieces_downloaded_count=0

        self.download_connections_limit=5
        self.download_connections=0

        self.upload_connections_limit=3
        self.upload_connections=0

        self.connection_count = 0
        self._connection_lock = asyncio.Lock()

        self.successful_handshakes=0

        self.choke_count=0
        self.unchoke_count=0

        self.initial_connection_limit=50

        self.piece_count_to_shift_connection_limit=4

        self.standard_connection_limit=20
        self.connection_limit = self.initial_connection_limit
        self.number_of_all_peers=0