import asyncio


class peer:

    def __init__(self,peers):
        self.peers=peers
        self.peer_schema={
        "peer_id": None,
        "connection_side": "client",
        "reader": None,
        "writer": None,
        "recv_msg_queue": asyncio.Queue(),
        "cancel_queue": asyncio.Queue(),
        "bitfield": [False] * peers.bitfield_length,
        "inflight_requests": 0,     # how many request messages are in flight
        "peer_conn_try_count":0,
        "peer_conn_try_limit":3,
        "choked":False,
        "next_begin":0
        }

    def set_choked(self):
        self.peer_schema["choked"]=True

    def unset_choked(self):
        self.peer_schema["choked"]=False

    def is_choked(self):
        return self.peer_schema["choked"]

    def get_try_count_lim(self):
        return self.peer_schema["peer_conn_try_limit"]

    def set_try_count(self,num):
        self.peer_schema["peer_conn_try_count"]=num

    def get_try_count(self):
        return self.peer_schema["peer_conn_try_count"]

    def set_inflight_requests(self,num):
        self.peer_schema["inflight_requests"]=num
        return self.peer_schema["inflight_requests"]

    def get_inflight_requests(self):
        return self.peer_schema["inflight_requests"]

    def add_bitfield(self,bitfield):
        self.peer_schema["bitfield"]=bitfield
        self.peers.update_piece_availability(bitfield)

    def update_bitfield(self,piece_index):
        self.peer_schema["bitfield"][piece_index]=True
        self.peers.update_piece_availability(piece_index)

    def set_peer_id(self,peer_id):
        self.peer_schema["peer_id"]=peer_id

    def set_reader(self,reader):
        self.peer_schema["reader"]=reader

    def set_writer(self,writer):
        self.peer_schema["writer"]=writer

    def set_bitfield(self,bitfield):
        self.peer_schema["bitfield"]=bitfield

    def get_bitfield(self):
        return self.peer_schema["bitfield"]

    def get_reader(self):
        return self.peer_schema["reader"]

    def get_writer(self):
        return self.peer_schema["writer"]

    def get_connection_side(self):
        return self.peer_schema["connection_side"]

    def get_cancel_queue(self):
        return self.peer_schema["cancel_queue"]

    def get_recv_msg_queue(self):
        return self.peer_schema["recv_msg_queue"]

    def close_writer(self):
        self.peer_schema["writer"].close()

    def get_bitfield_length(self):
        return self.peers.bitfield_length

    def get_target_piece_info(self):

        pa = self.peers.get_piece_availability()
        bitfield = self.peer_schema['bitfield']

        candidates = [
        i for i, has in enumerate(bitfield)
        if has
        and i not in self.peers.piece_downloaded
        and i not in self.peers.piece_in_progress
        ]

        if not candidates:
            return None

        rarest = candidates[0]
        for i in candidates:
            if pa[i] < pa[rarest]:
                rarest = i

        return rarest


class Peers:

    def __init__(self,torrent):
        self.peers = {}
        self.piece_downloaded = set()
        self.piece_in_progress = set()
        self.bitfield_length=torrent.tor_info.bitfield_length
        self.piece_availability = [0] * self.bitfield_length

    def get_piece_availability(self):
        return self.piece_availability

    def get_keys(self):
        return self.peers.keys()

    def update_piece_availability(self,new_bitfield_or_piece_index):

        update=new_bitfield_or_piece_index

        if type(update)==list:

            for i in range(len(update)):

                self.piece_availability[i]+=update[i]

        if type(update)==int:

            self.piece_availability[update]+=1


    def add_peer(self,peer_key):

        self.peers[peer_key]=peer(self)

        return self.peers[peer_key]

    def peer(self,peer_key):
        return self.peers[peer_key]

    def get_peer(self,peer_key):
        return self.peers[peer_key]

    def destroy_peer(self,peer_key ):

            print(f"destroying peer {peer_key}")

            try:
                self.peers[peer_key].close_writer()
                del self.peers[peer_key]

            except Exception as e:
                print(f"error while destroying peer {peer_key}: {e}")