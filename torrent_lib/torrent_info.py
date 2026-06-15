from torrent_lib.bencode_decoder import bencode_decoder
from utils.essencial_funcs import create_peer_id,extract_bitfield
import os
import math


class TorrentInfo:
    def __init__(self,file_path):

        bd = bencode_decoder()

        self.file_path = file_path

        self.decoded_tf = bd.decode_file(file_path)

        self.info=self.decoded_tf[b"info"]

        self.is_multi_file=False

        # as we downloding multiple file as one single file , we'll store sum all all file size and use that
        self.file_size=0
        self.file_name=None
        self.folder_name=None
        self.files={}

        if b"files" in self.info:
            self.is_multi_file = True
            self.folder_name = self.info[b"name"].decode()

            offset = 0
            for file in self.info[b"files"]:   # iterate the original list
                full_path = os.path.join(*[p.decode() for p in file[b"path"]])
                self.files[full_path] = {"length": file[b"length"], "offset": offset}
                offset += file[b"length"]
                self.file_size+=file[b"length"]
        else:

            self.file_size=self.info[b"length"]
            self.file_name=self.info[b'name'].decode()

        self.info_hash=bd.extract_info_hash(self.decoded_tf)

        self.peer_id=create_peer_id('-MT0001-')

        # Pre-compute bytes forms for handshake
        self.info_hash_bytes = bytes.fromhex(self.info_hash) if isinstance(self.info_hash, str) else self.info_hash

        self.peer_id_bytes = self.peer_id.encode('utf-8') if isinstance(self.peer_id, str) else self.peer_id

        self.piece_length=self.decoded_tf[b'info'][b'piece length']


        self.total_pieces = math.ceil(self.file_size / self.piece_length)
        self.last_piece_index = self.total_pieces - 1
        self.last_piece_length=self.file_size % self.piece_length or self.piece_length

        ##gets bitfield as array/list [false]*bitfield length
        self.bitfield=extract_bitfield(self.decoded_tf)

        self.bitfield_length=len(self.bitfield)


        self.decoded_tf["piece_length"]=self.piece_length
        self.decoded_tf["last_piece_length"]=self.last_piece_length

        self.decoded_tf["total pieces"]=self.total_pieces
        self.decoded_tf["last_piece_index"]=self.last_piece_index