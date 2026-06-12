import asyncio
import struct
from torrent_lib.dynamic_messages import msg_request
from constants.message_lengths import *
import math

async def send_have_message(peers,piece_index):
    for peer_key in peers.get_keys():
        writer=peers.peer(peer_key).get_writer()
        have_message=struct.pack('!IBI',5,4,piece_index)
        writer.write(have_message)
        await writer.drain()


async def request_next_blocks(
    writer: asyncio.StreamWriter,
    piece_index: int,
    begin: int,
    piece_length: int,
    file_size:int,
    n: int=5,
    block_length: int = DEFAULT_BLOCK_LENGTH

) -> int:
    """
    Pipeline n block requests for a single piece without waiting for responses.

    Sends up to n REQUEST messages back-to-back, stopping early if the
    piece boundary is reached. The caller should await the corresponding
    responses separately (producer/consumer pattern).

    Args:

        writer: asyncio stream to the peer.
        piece_index: Index of the piece being downloaded.
        begin: Byte offset within the piece to start from.
        piece_length: Total length of the piece in bytes.
        file_length:size of file in bytes

        n: Number of requests to pipeline in this batch (default = 5).
        block_length: Size of each block request (default 2^14 = 16 KiB).

    Returns:
        The updated begin offset after all sent requests.
        Pass this back in on the next call to continue pipelining.

    Example:
        begin = 0
        while begin < piece_length:
            begin = await request_next_blocks(
                n=5,
                writer=writer,
                piece_index=3,
                begin=begin,
                piece_length=piece_length,
            )
    """
    print("begin : ",begin)
    print("index",piece_index)
    total_pieces = math.ceil(file_size / piece_length)
    last_index = total_pieces - 1

    if last_index==piece_index:
        piece_length = file_size % piece_length or piece_length


    piece_complete=False
    inflight=0

    for _ in range(n):
        if begin >= piece_length:
            piece_complete=True
            return (piece_complete,0,inflight)

        actual_length = min(block_length, piece_length - begin)
        writer.write(msg_request(piece_index, begin, actual_length))
        inflight+=1

        begin +=actual_length

    await writer.drain()

    print("is_complete : ",piece_complete)
    return (piece_complete,begin,inflight)