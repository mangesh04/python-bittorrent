import struct

# static prefixes — truly fixed
MSG_KEEPALIVE  = struct.pack('!I', 0)
MSG_CHOKE      = struct.pack('!IB', 1, 0)
MSG_UNCHOKE    = struct.pack('!IB', 1, 1)
MSG_INTERESTED = struct.pack('!IB', 1, 2)
MSG_NOT_INTERESTED = struct.pack('!IB', 1, 3)
