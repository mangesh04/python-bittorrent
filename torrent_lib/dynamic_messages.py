import struct

# dynamic — functions
def msg_have(index):    return struct.pack('!IBI', 5, 4, index)

#i=piece index b=begin l=length
def msg_request(i, b, l): return struct.pack('!IBIII', 13, 6, i, b, l)

def msg_bitfield(bf):   return struct.pack('!IB', len(bf)+1, 5) + bf

def msg_cancel(i, b, l): return struct.pack('!IBIII', 13, 8, i, b, l)


def create_handshake(torrent_info):

    peer_id=torrent_info.peer_id
    info_hash=torrent_info.info_hash
    info_hash_bytes=torrent_info.info_hash_bytes
    peer_id_bytes=torrent_info.peer_id_bytes

    protocol_string = b"BitTorrent protocol"
    pstrlen = len(protocol_string)
    # Create the reserved bytes (8 bytes)
    reserved =bytearray(8)
    reserved[7] |= 0x01  # signals DHT support
    # Ensure the peer_id and info_hash are 20bytes long
    if len(peer_id_bytes) != 20 or len(info_hash) !=20:
        raise ValueError("peer_id and info_hashmust be 20 bytes long.")
    # Construct the handshake message
    handshake = (
        struct.pack('B', pstrlen) +   # pstrlen(1 byte)
        protocol_string +              # pstr(19 bytes)
        bytes(reserved) +              #reserved (8 bytes)
        info_hash_bytes +         #info_hash (20 bytes)
        peer_id_bytes             #peer_id (20 bytes)
    )

    return handshake