from constants.const_messages import *
from constants.message_lengths import INTEGER_LENGTH
from utils.essencial_funcs import bytes_to_bools
from constants.message_id import message_id

import struct
import asyncio

async def receive_messages(torrent,peer_key):

    peer=torrent.peers.peer(peer_key)

    reader=peer.get_reader()

    cancel_queue=peer.get_cancel_queue()
    recv_msg_queue=peer.get_recv_msg_queue()

    print(f"message receiver started for some peer")

    while True:

        if torrent.dm.total_file_downloaded:
            recv_msg["length"] = -1
            recv_msg_queue.put_nowait(dict(recv_msg))
            break


        recv_msg = dict()

        try:
            length_bytes = await asyncio.wait_for(reader.readexactly(INTEGER_LENGTH), timeout=120)
            peer.set_try_count(0)  # reset on any successful read

            recv_msg["length"] = struct.unpack('!I', length_bytes)[0]

            if recv_msg["length"] == 0:  # keep-alive
                recv_msg_queue.put_nowait({"length": 0})
                continue

            id_bytes = await reader.readexactly(1)
            recv_msg["id"] = struct.unpack('!B', id_bytes)[0]

            print(recv_msg["id"])

            if recv_msg["id"] > 3:
                await asyncio.wait_for(read_message_content(recv_msg, peer), timeout=120)

            if recv_msg["id"] == message_id["cancel"]:
                cancel_queue.put_nowait(dict(recv_msg))
            else:
                recv_msg_queue.put_nowait(dict(recv_msg))

        except asyncio.TimeoutError:
            if peer.is_choked():
                # alive but choked — send keep-alive and wait
                writer = peer.get_writer()
                writer.write(MSG_KEEPALIVE)
                await writer.drain()
                continue  # keep looping, don't increment try count
            else:

                # not choked but timed out — peer is dead
                peer.set_try_count(peer.get_try_count() + 1)
                if peer.get_try_count() >= peer.get_try_count_lim():
                    recv_msg["length"] = -1
                    recv_msg_queue.put_nowait(dict(recv_msg))
                    break

        except (asyncio.IncompleteReadError, ConnectionResetError):
            recv_msg["length"] = -1
            recv_msg_queue.put_nowait(dict(recv_msg))
            break

async def read_message_content(recv_msg,peer):

    reader=peer.get_reader()

    if recv_msg["id"]==message_id["have"]:

        piece_index_bytes=await reader.readexactly(recv_msg["length"]-1)

        recv_msg["piece_index"]=struct.unpack('!I',piece_index_bytes)[0]

    if recv_msg["id"]==message_id["bitfield"]:

        bitfield_bytes=await reader.readexactly(recv_msg["length"]-1)
        ##list of bools.
        recv_msg["bitfield"]=bytes_to_bools(bitfield_bytes,peer.get_bitfield_length())


    if recv_msg["id"]==message_id["request"] or recv_msg["id"]==message_id["cancel"]:

        index=await reader.readexactly(INTEGER_LENGTH)
        begin=await reader.readexactly(INTEGER_LENGTH)
        length=await reader.readexactly(INTEGER_LENGTH)
        recv_msg["piece_index"]=struct.unpack('!I',index)[0]
        recv_msg["piece_begin"]=struct.unpack('!I',begin)[0]
        recv_msg["piece_length"]=struct.unpack('!I',length)[0]

    if recv_msg["id"]==message_id["piece"]:

        index=await reader.readexactly(INTEGER_LENGTH)
        begin=await reader.readexactly(INTEGER_LENGTH)
        recv_msg["piece_index"]=struct.unpack('!I',index)[0]
        recv_msg["piece_begin"]=struct.unpack('!I',begin)[0]
        ## we can use it as it is
        recv_msg["piece_block"]=await reader.readexactly(recv_msg["length"]-9)

    if recv_msg["id"]==message_id["port"]:
        port_bytes=await reader.readexactly(INTEGER_LENGTH)

        try:
            recv_msg["port"] = struct.unpack('!H', port_bytes)[0]
        except struct.error:
            print("problem with port message")
            pass
