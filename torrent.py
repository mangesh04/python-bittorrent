import asyncio

from torrent_lib.connection_stat import ConnectionStat
from core.client import client
# from core.server import server
from download.download_manager import DownloadManager
from torrent_lib.torrent_info import TorrentInfo
from peer.peers import Peers
from core.server import Server

class Torrent:

    def __init__(self, torrent_file):

        self.torrent_info=TorrentInfo(torrent_file)

        self.stats=ConnectionStat()

        self.dm=DownloadManager(self)

        self.peers=Peers(self)

        self.server=Server(self)

    def run_torrent(self):

        async def main():

            client_task = asyncio.create_task(client(self))
            server_task = asyncio.create_task(self.server.main())

            await client_task  # download finishes
                # server keeps running → you're now seeding
            await server_task

        asyncio.run(main())


if __name__ == "__main__":
    torrent = Torrent("C:/Users/veerbhadra/Desktop/code/bittorrent/tests/big-buck-bunny.torrent")
