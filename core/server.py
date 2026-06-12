import asyncio



class Server:
    def __init__(self,mh):
        self.host = "localhost"
        self.port = 8888
        self.mh=mh

    async def on_client_connect(self,reader, writer):
        self.mh.add_peer(reader, writer, "server")

        addr = writer.get_extra_info("peername")

        ip = addr[0]
        port = addr[1]

        peer_key = (ip, port)

        self.mh.peers[peer_key] = {
        "peer_id": None,
        "ip": ip,
        "port": port,
        "connection_side": "client"
        }

        self.mh.peers[peer_key]["reader"] = reader
        self.mh.peers[peer_key]["writer"] = writer

        self.mh.handle(peer_key)

    async def main(self):
        server = await asyncio.start_server(self.on_client_connect,self.host,self.port)
        await server.serve_forever()


if __name__ == "__main__":
    server = Server()
    asyncio.run(server.main())