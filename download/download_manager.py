import hashlib
from pathlib import Path
import json

class PieceBuffer:

    def __init__(self, index, piece_length, expected_hash):
        self.index = index
        self.piece_length = piece_length
        self.expected_hash = expected_hash
        self.buffer = bytearray(piece_length)
        self.received = set()
        self.complete = False
        self.verified = False



class DownloadManager:

    def __init__(self, torrent):
        self.tor_info = torrent.torrent_info
        self.piece_length = self.tor_info.piece_length

        self.last_piece_index=self.tor_info.last_piece_index
        self.last_piece_length=self.tor_info.last_piece_length

        self.total_pieces = self.tor_info.total_pieces
        self.raw_hashes = self.tor_info.decoded_tf[b'info'][b'pieces']

        self.download_path="downloads"
        self.buffers = self.create_buffers_list()

        self.piece_downloaded = set()
        self.piece_in_progress = set()

        self.create_placeholder_file()
        self._load_state()
        self.total_file_downloaded=False
        self.check_if_downloaded()

    def check_if_downloaded(self):
        if  len(self.piece_downloaded)==self.total_pieces:
            self.total_file_downloaded=True

    def _get_state_path(self):

        if self.tor_info.is_multi_file:
            folder_path=Path(self.download_path)/self.tor_info.folder_name
            self.state_file_path=folder_path/f"{self.tor_info.folder_name}.state.json"
        else:
            file_path=Path(self.download_path)/self.tor_info.file_name
            self.state_file_path=Path(file_path)/f"{self.tor_info.file_name}.state.json"



    def _load_state(self):

        self._get_state_path()

        path = self.state_file_path

        if path.exists():
            self.piece_downloaded = set(json.loads(path.read_text()))

    def _update_state(self):

        tmp = self.state_file_path.with_suffix(".tmp")   # "abc123.state.tmp"
        tmp.write_text(json.dumps(list(self.piece_downloaded)))              # write here first
        tmp.replace(self.state_file_path)                # rename to "abc123.state.json"


    def create_placeholder_file(self):


        if self.tor_info.is_multi_file:

            files=self.tor_info.files
            folder_path=Path(self.download_path)/self.tor_info.folder_name
            self.state_file_path=folder_path/f"{self.tor_info.folder_name}.state.json"


            for file_path in files.keys():

                complete_path=Path(folder_path)/file_path

                if complete_path.exists():
                    print("file to download already exist")
                    return

                complete_path.parent.mkdir(parents=True, exist_ok=True)

                file_size=files[file_path]["length"]

                with open(complete_path, 'wb') as f:
                    f.truncate(file_size)


        else:

            file_path=Path(self.download_path)/self.tor_info.file_name
            file_size=self.tor_info.file_size
            self.state_file_path=Path(file_path)/f"{self.tor_info.file_name}.state.json"

            if file_path.exists():
                print("file to download already exist")
                return

            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as f:
                f.truncate(file_size)



    def add_block(self,piece_index, begin, block_data):

        buffer=self.buffers[piece_index]

        buffer.buffer[begin:begin + len(block_data)] = block_data
        buffer.received.add((begin, len(block_data)))

        print("blocks gathered",len(buffer.received))

        total = sum(length for _, length in buffer.received)

        print("inAdd piece_index",piece_index)
        print("inAdd last_piece_index",self.tor_info.last_piece_index)
        print("inAdd piece_length",self.last_piece_length)
        print("inAdd total gatherd" , total)

        if total < buffer.piece_length and not (piece_index == self.last_piece_index and total >= self.last_piece_length):
            print("returned after gathring block not complete")
            return

        buffer.complete = True
        buffer.verified = hashlib.sha1(bytes(buffer.buffer)).digest() == buffer.expected_hash
        print("block completes piece")
        if not buffer.verified:
            print("piece_not_verified")
            buffer.buffer = bytearray(buffer.piece_length)
            buffer.received.clear()
            buffer.complete = False
            return

        print("piece_verified")

        piece_offset = buffer.piece_length * piece_index


        if self.tor_info.is_multi_file:
            files = self.tor_info.files
            folder_path = Path(self.download_path)/ self.tor_info.folder_name

            piece_start = piece_offset
            piece_end = piece_offset + len(buffer.buffer)  # use actual buffer length, not self.piece_length (last piece is shorter)

            for file_path, file_info in files.items():
                file_start = file_info["offset"]
                file_end   = file_info["offset"] + file_info["length"]

                # overlap in the flat stream
                overlap_start = max(piece_start, file_start)
                overlap_end   = min(piece_end,   file_end)

                if overlap_start >= overlap_end:
                    continue

                # where in buffer.buffer does this overlap begin?
                buf_slice_start = overlap_start - piece_start
                buf_slice_end   = overlap_end   - piece_start

                # where in the file do we write?
                file_seek_pos = overlap_start - file_start

                complete_path = Path(folder_path)/ file_path

                with open(complete_path, 'r+b') as f:
                    f.seek(file_seek_pos)
                    f.write(buffer.buffer[buf_slice_start:buf_slice_end])

        else:

            file_path=Path(self.download_path)/self.tor_info.file_name

            with open(file_path, 'r+b') as f:
                f.seek(piece_offset)
                f.write(buffer.buffer[piece_index])

        buffer = None

        print("piece written ")

        self.piece_downloaded.add(piece_index)

        self._update_state()

        self.buffers[piece_index].received.clear()

        if len(self.piece_downloaded)==self.total_pieces:
            print("last piece downloaded in dm")
            self.total_file_downloaded=True


    def create_buffers_list(self):
        pieces_list = []
        for i in range(self.total_pieces):
            expected_hash = self.raw_hashes[i*20:(i+1)*20]

            piece_length=self.last_piece_length if i==self.last_piece_index else self.piece_length

            pieces_list.append(PieceBuffer(i,piece_length, expected_hash))

        return pieces_list

    def get_piece_block(self, piece_index, piece_begin, block_length):

        piece_block=None

        with open(self.file_path, "rb") as f:
            f.seek((piece_index * self.piece_length) + piece_begin)
            piece_block=f.read(block_length)

        return piece_block
