from torrent_lib.bencode_decoder import bencode_decoder
from utils.essencial_funcs import create_peer_id
from torrent_lib.bencode_decoder import bencode_decoder


def create_tracker_request_url(torrent_info):

    peer_id=torrent_info.peer_id

    decoded_tf=torrent_info.decoded_tf

    bd=bencode_decoder()

    info_hash=bd.escaped_hash(torrent_info.info_hash)


    url_para={}


    url_para['announce'] =decoded_tf[b"announce"].decode()
    url_para['peer_id']=peer_id
    url_para['info_hash']=info_hash
    url_para['uploaded']=0
    url_para['downloaded']=0
    url_para['left']=bd.file_size(decoded_tf)
    url_para['port']=6889
    url_para['compact']=1
    url_para['event']='started'


    url=f"{url_para['announce']}?info_hash={url_para['info_hash']}&peer_id={url_para['peer_id']}&uploaded={url_para['uploaded']}&downloaded={url_para['downloaded']}&left={url_para['left']}&port={url_para['port']}&compact={url_para['compact']}&event={url_para['event']}"

    return url
