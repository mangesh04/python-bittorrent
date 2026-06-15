import asyncio

from utils.essencial_funcs import connect_server
from network.get_new_peers import get_new_peers
from peer.message_handler import handle

async def client(torrent):

    stats=torrent.stats
    peers=torrent.peers

    async def try_connect(peer_id_port):

        async with stats._connection_lock:
            if stats.connection_count >=   stats.connection_limit:
                return None
            stats.connection_count += 1
        try:
            reader, writer = await connect_server(peer_id_port[0], peer_id_port[1])
            peer_key = (peer_id_port[0],    peer_id_port[1])
            peer_id = peer_id_port[2] if len(peer_id_port) > 2 else None
            return peer_key, peer_id, reader, writer
        except Exception as e:
            async with stats._connection_lock:
                stats.connection_count -= 1
            print(f"something went wrong while  connecting with peer {peer_id_port[0]}   :{peer_id_port[1]} — {e}")
            return None

    while True:

        if torrent.dm.total_file_downloaded:
            print("complete file is downloaded stopping client")
            return

        new_peers = await get_new_peers(torrent.torrent_info)
        new_peers = new_peers.difference(peers.get_keys())
        stats.connection_limit = (
            stats.standard_connection_limit
            if stats.pieces_downloaded_count >= stats.  piece_count_to_shift_connection_limit
            else stats.initial_connection_limit
        )
        stats.number_of_all_peers = len(new_peers)

        results = await asyncio.gather(*[try_connect(p) for p in new_peers],return_exceptions=True)
        tasks = []
        to_close = []

        for result in results:
            if result is None or isinstance (result, Exception):
                continue
            peer_key, peer_id, reader, writer =  result
            if stats.connection_count >stats.connection_limit:
                to_close.append(writer)
                continue

            peer=peers.add_peer(peer_key)

            peer.set_peer_id(peer_id)
            peer.set_reader(reader)
            peer.set_writer(writer)

            # tasks.append(handle(torrent,peer_key))
            asyncio.create_task(handle(torrent, peer_key))


        for writer in to_close:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                print("Error closing connection")

        # await asyncio.gather(*tasks,return_exceptions=True)
        print("Waiting for next peerList from   tracker.")

        await asyncio.sleep(5)