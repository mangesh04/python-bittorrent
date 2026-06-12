import random
import os
import math
import asyncio

def create_peer_id(client_id):
    return f"{client_id}{''.join([str(random.randint(0,9)) for _ in range(12)])}"


#TODO delete these 2 functions if not essential
def bytes_to_bits(size, unit):
    unit=unit.upper()
    units_in_bits = {
        'B': 1,  # Bytes to bits
        'KB': 1024,
        'MB': 1024 * 1024,
        'GB': 1024 * 1024 * 1024,
        'TB': 1024 * 1024 * 1024 * 1024
    }

    if unit in units_in_bits:
        return size * units_in_bits[unit]
    else:
        raise ValueError("Unknown unit")



def choose_piece_size(file_size):

    piece_size = bytes_to_bits(256 ,"kb") # minimum piece size

    number_of_pieces=file_size / piece_size
    while  number_of_pieces > 1000 and piece_size <= bytes_to_bits(512,"mb"):
        piece_size *= 2
    return piece_size




async def connect_server(host,port):
    return  await asyncio.open_connection(host, port)





def bools_to_bytes(bitfield):
    bits = 0
    byte_array = bytearray()

    for i, bit in enumerate(bitfield):
        bits = (bits << 1) | int(bit)
        # Every 8 bits, store the byte
        if (i + 1) % 8 == 0:
            byte_array.append(bits)
            bits = 0

    # Handle remaining bits (if num_pieces not divisible by 8)
    remaining = len(bitfield) % 8
    if remaining:
        bits <<= (8 - remaining)
        byte_array.append(bits)

    return bytes(byte_array)

def bytes_to_bools(data, num_pieces):
    result = []
    for byte in data:
        for i in range(7, -1, -1):  # MSB first
            result.append((byte >> i) & 1 == 1)
    return result[:num_pieces]  # Trim padding



def parse_handshake(data: bytes):
    if len(data) < 68:
        raise ValueError("Incomplete handshake")

    pstrlen = data[0]
    protocol = data[1:20]
    reserved = data[20:28]
    info_hash = data[28:48]
    peer_id = data[48:68]

    return {
        "pstrlen": pstrlen,
        "protocol": protocol,
        "reserved": reserved,
        "info_hash": info_hash,
        "peer_id": peer_id
    }

import aiohttp

async def httpRequest(url):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as stream:
                data = await stream.content.read()
            return data

    except aiohttp.ClientResponseError as e:
        print(f"HTTP error {e.status}: {e.message} for URL: {url}")
    except aiohttp.ClientConnectionError as e:
        print(f"Connection error: {e} for URL: {url}")
    except aiohttp.ClientTimeout:
        print(f"Request timed out for URL: {url}")
    except aiohttp.ClientError as e:
        print(f"Client error: {e} for URL: {url}")

    return None  # Explicit None on failure



def extract_bitfield(decoded_tf):
    info = decoded_tf[b'info']

    if b'length' in info:
        total_length = info[b'length']
    else:
        total_length = sum(f[b'length'] for f in info[b'files'])

    bitfield_length = math.ceil(total_length / info[b'piece length'])
    return [False] * bitfield_length


def bytes_to_ip(bytes):
    ip_bytes = bytes[:4]
    ip = ".".join(str(b) for b in ip_bytes)
    return ip

#these function are not really utils

def verify_handshake(response, expected_info_hash):
    if len(response) != 68:
        return False, {"error": f"Invalid length: {len(response)}, expected 68"}
    pstrlen   = response[0]
    pstr      = response[1:20]
    reserved  = response[20:28]
    info_hash = response[28:48]
    peer_id   = response[48:68]
    if pstrlen != 19:
        return False, {"error": f"Invalid pstrlen: {pstrlen}, expected 19"}
    if pstr != b"BitTorrent protocol":
        return False, {"error": f"Invalid protocol: {pstr}"}
    if info_hash != expected_info_hash:
        return False, {"error": f"Info hash mismatch: got {info_hash.hex()}, expected {expected_info_hash.hex()}    "}
    return True, {
        "pstr":      pstr.decode(),
        "reserved":  reserved.hex(),
        "info_hash": info_hash.hex(),
        "peer_id":   peer_id.decode(errors="replace"),
    }
