from utils.essencial_funcs import create_placeholder_file

import hashlib

from collections import defaultdict
import os


class PieceBuffer:

    def __init__(self, index, piece_length, expected_hash, file_path):
        self.index = index
        self.piece_length = piece_length
        self.expected_hash = expected_hash
        self.file_path = file_path
        self.buffer = bytearray(piece_length)
        self.received = set()
        self.complete = False
        self.verified = False

    def add_block(self, begin, block_data):

        self.buffer[begin:begin + len(block_data)] = block_data
        self.received.add((begin, len(block_data)))

        print("blocks gathered",len(self.received))

        total = sum(length for _, length in self.received)
        if total < self.piece_length:
            return

        self.complete = True
        self.verified = hashlib.sha1(bytes(self.buffer)).digest() == self.expected_hash

        if not self.verified:
            self.buffer = bytearray(self.piece_length)
            self.received.clear()
            self.complete = False
            return

        piece_offset = self.piece_length * self.index
        with open(self.file_path, 'r+b') as f:
            f.seek(piece_offset)
            f.write(self.buffer)

        self.buffer = None
        self.received.clear()


class DownloadManager:

    def __init__(self, torrent):
        self.tor_info = torrent.tor_info
        self.piece_length = torrent.tor_info.piece_length
        self.num_pieces = torrent.tor_info.bitfield_length
        self.raw_hashes = torrent.tor_info.decoded_tf[b'info'][b'pieces']

        self.download_path="download"
        self.buffers = self.create_buffers_list()

        self.create_placeholder_file()


    def create_placeholder_file(self):


        if self.tor_info.is_multi_file:
            files=self.tor_info.files
            folder_path=os.path.join(self.download_path,self.tor_info.folder_name)

            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            for file_path in files.keys():

                file_size=files[file_path]["length"]

                with open(file_path, 'wb') as f:
                    f.truncate(file_size)

        else:

            file_path=os.path.join(self.download_path,self.tor_info.file_name)
            file_size=self.tor_info.file_size

            if os.path.exists(file_path):
                print("file to download already exist")
                return

            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            with open(file_path, 'wb') as f:
                f.truncate(file_size)


    def write_piece(file_path, piece_index, piece_data, piece_size):
        """
        Writes a piece to its correct position in the file.

        Args:
        file_path (str): Path to the target file.
        piece_index (int): Index of the piece (0-based).
        piece_data (bytes): The actual piece data.
        piece_size (int): Expected size of each piece.
        """
        offset = piece_index * piece_size
        with open(file_path, 'r+b') as f:
            f.seek(offset)
            f.write(piece_data)


    def create_buffers_list(self):
        pieces_list = []
        for i in range(self.num_pieces):
            expected_hash = self.raw_hashes[i*20:(i+1)*20]
            pieces_list.append(PieceBuffer(i, self.piece_length, expected_hash, self.file_path))
        return pieces_list

    def get_piece_block(self, piece_index, piece_begin, block_length):

        piece_block=None

        with open(self.file_path, "rb") as f:
            f.seek((piece_index * self.piece_length) + piece_begin)
            piece_block=f.read(block_length)

        return piece_block
