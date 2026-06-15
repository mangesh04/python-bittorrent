import asyncio
from peer.process_messages import process_recv_msgs
from peer.receive_messages import receive_messages
from peer.initial_steps import run_initial_steps

async def handle(torrent, peer_key):

    result = await run_initial_steps(torrent, peer_key)

    if not result:
        return

    print("initial stpes done")

    peer=torrent.peers.get_peer(peer_key)

    try:
        await asyncio.gather(receive_messages(torrent,peer_key),process_recv_msgs(torrent,peer_key))
    except Exception as e:
        import traceback
        traceback.print_exc()  # instead of just print(e)
        print(f"peer connection failed  {e}")

    torrent.peers.destroy_peer(peer_key)
