import asyncio
from peer.message_handler import handle


class Server:
    def __init__(self,torrent):
        self.host = "localhost"
        self.port = 8888
        self.torrent=torrent

    async def on_client_connect(self,reader, writer):

        addr = writer.get_extra_info("peername")

        ip = addr[0]
        port = addr[1]

        peer_key = (ip, port)

        self.torrent.peers.add_peer(peer_key)

        self.torrent.peer.set_reader(reader)
        self.torrent.peer.set_writer(writer)

        asyncio.create_task(handle(self.torrent, peer_key))

    async def main(self):
        server = await asyncio.start_server(self.on_client_connect,self.host,self.port)
        await server.serve_forever()


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.main())