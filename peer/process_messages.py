import struct
from constants.message_id import message_id
from constants.const_messages import *

from peer.send_message_functions import request_next_blocks,send_have_message

async def process_recv_msgs(torrent,peer_key):

    peers=torrent.peers

    peer=peers.peer(peer_key)

    writer=peer.get_writer()

    cancel_queue=peer.get_cancel_queue()

    recv_msg_queue=peer.get_recv_msg_queue()

    piece_length=torrent.torrent_info.piece_length

    file_size=torrent.torrent_info.file_size

    dm=torrent.dm

    stat=torrent.stats

    while True:

        if not cancel_queue.empty():
            while not cancel_queue.empty():
                cancel_message = cancel_queue.get_nowait()

                temp = []
                while not recv_msg_queue.empty():
                    msg = recv_msg_queue.get_nowait()
                    if not (
                    cancel_message["piece_index"] == msg.get("piece_index") and
                    cancel_message["piece_begin"] == msg.get("piece_begin") and
                    cancel_message["piece_length"] == msg.get("piece_length")
                    ):
                        temp.append(msg)

                for msg in temp:
                    recv_msg_queue.put_nowait(msg)

        recv_msg= await recv_msg_queue.get()


        if recv_msg["length"] == -1:#something went wrong at receive message
            writer.close()
            break

        if recv_msg["length"] == 0:#keep-alive
            continue

        if  recv_msg["id"]==message_id["bitfield"]:

            ##its already parsed to bools list
            peer.set_bitfield(recv_msg['bitfield'])

            writer.write(MSG_INTERESTED)
            await writer.drain()

        if recv_msg["id"]==message_id["choke"]:
            peer.set_choked()
            print("peer choked us, keeping connection alive but not sending any request until we get unchoke recv_msg")
            writer.write(MSG_KEEPALIVE)
            await writer.drain()


        if  recv_msg["id"]==message_id["piece"]:

            print("piece_message_received")

            piece_index=recv_msg["piece_index"]
            piece_begin=recv_msg["piece_begin"]
            piece_block=recv_msg["piece_block"]

            buff=dm.buffers[piece_index]

            buff.add_block(begin=piece_begin, block_data=piece_block)

            print("added in buff")

            if buff.complete and not buff.verified:
                peers.piece_in_progress.discard(piece_index)
                raise Exception

            if buff.complete and buff.verified:

                peers.piece_in_progress.discard(piece_index)
                peers.piece_downloaded.add(piece_index)
                print("is problem here before sending have message")
                await send_have_message(peers,piece_index)

                print("piece completed looking for new piece")
                #next rare piece
                rare_piece_index,offset=peer.get_target_piece_info()

                if rare_piece_index == None:
                    continue
                else:
                    piece_index=rare_piece_index

                print("in piece rare_piece_index",rare_piece_index)
                peers.piece_in_progress.add(rare_piece_index)
                print("inflight requests",peer.get_inflight_requests())

            #we are asking multiple chucks(5) in one functioin call
            peer.set_inflight_requests(peer.get_inflight_requests()-1)

            if peer.get_inflight_requests() <= 0:

                ##while send a request message piece_length is also needed but have default value for that in this func.

                next_begin = peer.peer_schema["next_begin"]

                is_complete,next_begin,inflight = await request_next_blocks(writer, piece_index, next_begin, piece_length,file_size)

                peer.set_inflight_requests(inflight)

                #if piece is complete next_begin automatically be zero

                peer.peer_schema["next_begin"]=next_begin

        if recv_msg["id"]==message_id["unchoke"] :
            peer.unset_choked()
            print("peer unchoked us, we can start sending request recv_msgs")

            if stat.download_connections>=stat.download_connections_limit:
                continue

            rare_piece_index,offset=peer.get_target_piece_info()

            if rare_piece_index == None:
                continue

            print("unchoked rare_piece_index",rare_piece_index)
            peers.piece_in_progress.add(rare_piece_index)


            is_complete,next_begin,inflight= await request_next_blocks(writer, rare_piece_index, 0, piece_length,file_size)

            peer.peer_schema["next_begin"]=next_begin
            peer.set_inflight_requests(inflight)


        if recv_msg["id"]==message_id["interested"]:#intrested

            if stat.upload_connections>= stat.upload_connections_limit:
                writer.write(MSG_CHOKE)
                await writer.drain()
            else:
                print("peer is interested in our pieces, we can start sending piece recv_msgs")
                writer.write(MSG_UNCHOKE)
                await writer.drain()

        if recv_msg["id"]==message_id["not interested"]:#not intrested
            pass#it means they dont want anything , dont think we have to do anything   here,but it does help to understand

        if recv_msg["id"]==message_id["have"]:#have
            index=recv_msg["piece_index"]
            peer.update_bitfield(index)

        if recv_msg["id"] == message_id["request"]:

            piece_index = recv_msg["piece_index"]
            piece_begin = recv_msg["piece_begin"]
            block_length = recv_msg["piece_length"]

            if not torrent.torrent_info.bitfield[piece_index]:
                continue

            data_block=dm.get_piece_block(piece_index,piece_begin,block_length)

            piece_msg = struct.pack('!IBII', 9 + len(data_block), 7, piece_index, piece_begin) + data_block

            writer.write(piece_msg)
            await writer.drain()