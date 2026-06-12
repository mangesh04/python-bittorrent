import asyncio

from torrent_lib.connection_stat import ConnectionStat
from core.client import client
# from core.server import server
from download.download_manager import DownloadManager
from torrent_lib.torrent_info import TorrentInfo
from peer.peers import Peers

class Torrent:

    def __init__(self, torrent_file):

        self.torrent_info=TorrentInfo(torrent_file)

        self.stats=ConnectionStat()

        self.dm=DownloadManager(self)

        self.peers=Peers(self)

    def run_torrent(self):
        async def main():
            await client(self)
            # await asyncio.gather(client(self), server(self))

        asyncio.run(main())


if __name__ == "__main__":
    torrent = Torrent("C:/Users/veerbhadra/Desktop/code/bittorrent/tests/big-buck-bunny.torrent")
