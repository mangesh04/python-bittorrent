import socket
import struct
import random

from torrent_lib.create_tracker_request_url import create_tracker_request_url
from utils.essencial_funcs import httpRequest,bytes_to_ip,create_peer_id
from torrent_lib.bencode_decoder  import bencode_decoder

from network.dht import dht_get_peers
from urllib.parse import urlparse



def udp_get_peers(url,torrent_info):

    info_hash=torrent_info.info_hash

    peer_id=create_peer_id('-MT0001-')


    parsed = urlparse(url)

    tracker_host = parsed.hostname
    tracker_port = parsed.port


    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(5)

    # Step 1: Connect
    transaction_id = random.randint(0, 0xFFFFFFFF)
    connect_req = struct.pack(">QII", 0x41727101980, 0, transaction_id)

    print("HOST:", tracker_host)
    print("PORT:", tracker_port)


    sock.sendto(connect_req, (tracker_host, tracker_port))

    data, _ = sock.recvfrom(1024)
    action, txn, connection_id = struct.unpack(">IIQ", data)
    assert action == 0 and txn == transaction_id

    # Step 2: Announce
    transaction_id = random.randint(0, 0xFFFFFFFF)
    announce_req = struct.pack(
        ">QII20s20sQQQIIIiH",
        connection_id,
        1,                      # action: announce
        transaction_id,
        info_hash,              # 20-byte SHA1
        peer_id.encode(),       # 20-byte peer ID
        0,                      # downloaded
        0,                      # left (set appropriately)
        0,                      # uploaded
        2,                      # event: started
        0,                      # ip: default
        random.randint(0, 0xFFFFFFFF),  # key
        -1,                     # num_want: default
        6881                    # port
    )
    sock.sendto(announce_req, (tracker_host, tracker_port))

    data, _ = sock.recvfrom(4096)
    action, txn, interval, leechers, seeders = struct.unpack(">IIIII", data[:20])

    # Parse peer list (6 bytes each: 4 IP + 2 port)
    peers = []
    for i in range(20, len(data), 6):
        ip = socket.inet_ntoa(data[i:i+4])
        port = struct.unpack(">H", data[i+4:i+6])[0]
        peers.append((ip, port))

    return peers



def parse_peers(peers_data):
    peers = []

    # compact format — raw bytestring
    if isinstance(peers_data, bytes):
        for i in range(0, len(peers_data), 6):
            chunk = peers_data[i:i+6]
            ip = ".".join(str(b) for b in chunk[:4])
            port = struct.unpack("!H", chunk[4:6])[0]
            peers.append((ip, port))

    # verbose format — list of dicts
    elif isinstance(peers_data, list):
        for peer in peers_data:
            ip = peer[b"ip"].decode()
            port = peer[b"port"]
            peers.append((ip, port))

    return peers



async def get_new_peers(torrent_info):

    bd=bencode_decoder()

    tracker_domains = [tracker.decode() for tier in torrent_info.decoded_tf[b"announce-list"] for tracker in tier]

    new_peers=set()

    for domain in tracker_domains:

        if domain.startswith("http://"):

            tracker_url = create_tracker_request_url(torrent_info)
            res = await httpRequest(tracker_url)
            res=bd.decode(res)

            if res is None:
                break

            elif not b"peers" in res:

                print("response don't have peers in it : ")
                bd.print_in_format(res)
                print()
                break

            elif res == b'':
                print("Received empty response from tracker.")
                break

            peers_list = parse_peers(res[b'peers'])

            new_peers.update(peers_list)

        if domain.startswith("udp://"):

            try:
                new_peers.update(udp_get_peers(domain, torrent_info))

            except Exception as e:
                print("UDP tracker failed:", domain, e)

    dht_peers = await dht_get_peers(torrent_info.info_hash)

    new_peers.update(dht_peers)

    return new_peers


# "https://torrent.ubuntu.com/announce?info_hash=%01%C17%28%7Do%0E%D0ZVt-%AEyOc%2Cy%FF%3D&peer_id=i%28%F0%7B%0E%B9%08%5ESG%2B%2B%B6%EE%E49%B3%95%B3%22&port=6881&uploaded=0&downloaded=0&left=6655619072&compact=1&event=started"

# "https://torrent.ubuntu.com/announce?info_hash=%01%C17%28%7Do%0E%D0ZVt-%AEyOc%2Cy%FF%3D&peer_id=-MT0001-503923196555&uploaded=0&downloaded=0&left=6655619072&port=6889&compact=1&event=started"