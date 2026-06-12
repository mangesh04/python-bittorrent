##it'll just figuire out what this instanceA is running as client/server and perform some steps which are little ddifferent for them.

from utils.essencial_funcs import bools_to_bytes,verify_handshake
from torrent_lib.dynamic_messages import create_handshake
from constants.message_lengths import HANDSHAKE_LENGTH
from constants.const_messages import *


async def run_initial_steps(torrent , peer_key):

    bitfield=torrent.torrent_info.bitfield
    peers=torrent.peers
    info_hash=torrent.torrent_info.info_hash

    # Client initiates handshake
    writer = peers.peer(peer_key).get_writer()
    reader = peers.peer(peer_key).get_reader()

    connection_side=peers.peer(peer_key).get_connection_side()

    try:
        #send handshake
        if connection_side=='client':

            writer.write(create_handshake(torrent.torrent_info))
            await writer.drain()
            #recv handshake
            handshake_res=await reader.read(HANDSHAKE_LENGTH)
            #checking handshakek
            is_valid, data = verify_handshake(handshake_res, info_hash)

            writer.write(MSG_INTERESTED)
            await writer.drain()
        else:

            handshake_res=await reader.read(HANDSHAKE_LENGTH)
            is_valid, data = verify_handshake(handshake_res, info_hash)

            writer.write(create_handshake(torrent.torrent_info))
            await writer.drain()
            #recv handshake
            #checking handshakek

        if not is_valid:
            raise ValueError(data["error"])

        print(data["peer_id"])
        torrent.stats.successful_handshakes+=1
        print("handshake varification successful, opening connection")

    except Exception as e:
        print("handshake problem")
        print(e)
        print("handshake varification failed, closing connection")
        peers.destroy_peer(peer_key)
        return False

    #sending bitfield if we have any piece

    if any(bitfield):
        try:
            ##boolarray to bytearray and sending
            writer.write(bools_to_bytes(bitfield))
            await writer.drain()
            print("bitfield sent ")
        except Exception as e:
            print("something went wrong while sending bitfield ")
            print(e)
            peers.destroy_peer(peer_key)
            return False
    else:
        print("we don't have any piece, skipping bitfield sending")

    return True