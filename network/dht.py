import asyncio
import socket
import struct
import random
import os
from torrent_lib.bencode_decoder import bencode_decoder
# ─────────────────────────────────────────────
#  BEP 5 DHT Implementation
#  Usage: call dht_get_peers(info_hash) from get_new_peers.py
# ─────────────────────────────────────────────

BOOTSTRAP_NODES = [
    ("router.bittorrent.com", 6881),
    ("router.utorrent.com",   6881),
    ("dht.transmissionbt.com", 6881),
]

K     = 8   # max nodes per k-bucket
ALPHA = 3   # concurrency factor for iterative lookups


# ── Helpers ───────────────────────────────────

def generate_node_id() -> bytes:
    return os.urandom(20)


def xor_distance(a: bytes, b: bytes) -> int:
    return int.from_bytes(a, "big") ^ int.from_bytes(b, "big")


def encode_nodes(nodes: list) -> bytes:
    """Encode [(node_id, ip, port), ...] into 26-byte compact format."""
    result = b""
    for node_id, ip, port in nodes:
        result += node_id + socket.inet_aton(ip) + struct.pack(">H", port)
    return result


def decode_nodes(data: bytes) -> list:
    """Decode compact node info into [(node_id, ip, port), ...]."""
    nodes = []
    for i in range(0, len(data) - 25, 26):
        chunk   = data[i : i + 26]
        node_id = chunk[:20]
        ip      = socket.inet_ntoa(chunk[20:24])
        port    = struct.unpack(">H", chunk[24:26])[0]
        nodes.append((node_id, ip, port))
    return nodes


def decode_peers(data: bytes) -> list:
    """Decode compact peer info into [(ip, port), ...]."""
    peers = []
    for i in range(0, len(data) - 5, 6):
        chunk = data[i : i + 6]
        ip    = socket.inet_ntoa(chunk[:4])
        port  = struct.unpack(">H", chunk[4:6])[0]
        peers.append((ip, port))
    return peers



# ── Routing table ─────────────────────────────

class KBucket:
    """Holds up to K nodes, evicting the oldest when full."""

    def __init__(self):
        self.nodes: list = []   # [(node_id, ip, port), ...]

    def add(self, node_id: bytes, ip: str, port: int):
        # Move to tail if already present (freshness update)
        self.nodes = [(n, i, p) for n, i, p in self.nodes if n != node_id]
        self.nodes.append((node_id, ip, port))
        if len(self.nodes) > K:
            self.nodes.pop(0)   # evict least-recently-seen

    def get_all(self) -> list:
        return list(self.nodes)


class RoutingTable:
    def __init__(self, own_node_id: bytes):
        self.own_id  = own_node_id
        self.buckets = [KBucket() for _ in range(160)]

    def _bucket_index(self, node_id: bytes) -> int:
        dist = xor_distance(self.own_id, node_id)
        return max(0, dist.bit_length() - 1)

    def add_node(self, node_id: bytes, ip: str, port: int):
        if node_id == self.own_id:
            return
        idx = self._bucket_index(node_id)
        self.buckets[idx].add(node_id, ip, port)

    def closest_nodes(self, target_id: bytes, count: int = K) -> list:
        all_nodes = [n for bucket in self.buckets for n in bucket.get_all()]
        all_nodes.sort(key=lambda n: xor_distance(n[0], target_id))
        return all_nodes[:count]


# ── asyncio UDP protocol ──────────────────────

class DHTProtocol(asyncio.DatagramProtocol):
    def __init__(self, node):
        self.node      = node
        self.transport = None

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data: bytes, addr):
        asyncio.ensure_future(self.node._handle_message(data, addr))

    def error_received(self, exc):
        print(f"[DHT] UDP error: {exc}")

    def connection_lost(self, exc):
        pass


# ── Main DHT node ─────────────────────────────

class DHTNode:
    """
    A minimal BEP-5 DHT node.

    Typical usage:
        node = DHTNode(info_hash)
        await node.start()          # bind UDP + bootstrap
        peers = await node.find_peers()
        node.stop()
    """

    def __init__(self, info_hash: bytes, port: int = 6882):
        self.node_id       = generate_node_id()
        self.info_hash     = info_hash
        self.port          = port
        self.routing_table = RoutingTable(self.node_id)
        self.transport     = None
        self._pending: dict = {}    # tid -> asyncio.Future
        self.found_peers: set = set()

    # ── Low-level send / receive ──────────────

    def _send(self, msg: dict, addr: tuple):
        bd=bencode_decoder()
        if self.transport:
            try:
                self.transport.sendto(bd.encode(msg), addr)
            except Exception as e:
                print(f"[DHT] Send error: {e}")

    async def _query(self, addr: tuple, q: bytes, a: dict, timeout: float = 3.0):
        """Send a query and await its response dict, or None on timeout."""
        tid    = os.urandom(2)
        future = asyncio.get_event_loop().create_future()
        self._pending[tid] = future

        self._send({b"t": tid, b"y": b"q", b"q": q, b"a": a}, addr)

        try:
            return await asyncio.wait_for(asyncio.shield(future), timeout=timeout)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            self._pending.pop(tid, None)
            return None

    async def _handle_message(self, data: bytes, addr: tuple):
        try:
            msg = bencode_decoder().decode(data)
            if not isinstance(msg, dict):
                return

            y = msg.get(b"y")
            t = msg.get(b"t")

            if y == b"r":                           # ← response to our query
                if t in self._pending and not self._pending[t].done():
                    self._pending[t].set_result(msg.get(b"r", {}))
                self._pending.pop(t, None)

            elif y == b"q":                         # ← incoming query from network
                await self._handle_incoming_query(msg, addr)

        except Exception:
            pass   # malformed packets are common in DHT; silently ignore

    async def _handle_incoming_query(self, msg: dict, addr: tuple):
        """Respond to ping / find_node / get_peers from other nodes."""
        q   = msg.get(b"q")
        tid = msg.get(b"t", b"")
        a   = msg.get(b"a", {})

        # Always add the querying node to our routing table
        sender_id = a.get(b"id", b"")
        if len(sender_id) == 20:
            self.routing_table.add_node(sender_id, addr[0], addr[1])

        if q == b"ping":
            self._send({b"t": tid, b"y": b"r",
                        b"r": {b"id": self.node_id}}, addr)

        elif q == b"find_node":
            target  = a.get(b"target", b"")
            closest = self.routing_table.closest_nodes(target)
            self._send({b"t": tid, b"y": b"r",
                        b"r": {b"id": self.node_id,
                               b"nodes": encode_nodes(closest)}}, addr)

        elif q == b"get_peers":
            closest = self.routing_table.closest_nodes(a.get(b"info_hash", b""))
            token   = os.urandom(4)
            self._send({b"t": tid, b"y": b"r",
                        b"r": {b"id":    self.node_id,
                               b"token": token,
                               b"nodes": encode_nodes(closest)}}, addr)

    # ── High-level DHT queries ────────────────

    async def ping(self, addr: tuple):
        return await self._query(addr, b"ping", {b"id": self.node_id})

    async def find_node(self, addr: tuple, target: bytes):
        return await self._query(addr, b"find_node",
                                 {b"id": self.node_id, b"target": target})

    async def get_peers(self, addr: tuple):
        return await self._query(addr, b"get_peers",
                                 {b"id": self.node_id,
                                  b"info_hash": self.info_hash})

    async def announce_peer(self, addr: tuple, token: bytes):
        return await self._query(addr, b"announce_peer",
                                 {b"id":          self.node_id,
                                  b"info_hash":   self.info_hash,
                                  b"port":        self.port,
                                  b"token":       token,
                                  b"implied_port": 0})

    # ── Bootstrap ─────────────────────────────

    async def bootstrap(self):
        """
        Contact the well-known bootstrap nodes, run find_node for our own ID,
        and populate the routing table with the closest nodes they return.
        """
        print("[DHT] Bootstrapping...")
        tasks = []
        for host, port in BOOTSTRAP_NODES:
            try:
                ip = socket.gethostbyname(host)
                tasks.append(self.find_node((ip, port), self.node_id))
            except socket.gaierror:
                continue

        results = await asyncio.gather(*tasks, return_exceptions=True)

        count = 0
        for res in results:
            if isinstance(res, dict) and b"nodes" in res:
                for node_id, ip, port in decode_nodes(res[b"nodes"]):
                    self.routing_table.add_node(node_id, ip, port)
                    count += 1

        print(f"[DHT] Bootstrap done — {count} nodes added to routing table.")

    # ── Iterative get_peers lookup ─────────────

    async def find_peers(self, max_iterations: int = 12) -> set:
        """
        Kademlia-style iterative lookup for peers that have self.info_hash.

        Each round we query the K closest nodes we know and have not yet queried.
        If a response contains 'values', we extract the peers.
        If it contains 'nodes', we add them as candidates for the next round.
        We also announce ourselves to nodes that gave us a token.
        """
        queried  : set  = set()
        tokens   : dict = {}   # addr -> token, collected for announce_peer

        candidates = self.routing_table.closest_nodes(self.info_hash, K)
        if not candidates:
            print("[DHT] Routing table is empty — did bootstrap succeed?")
            return self.found_peers

        for iteration in range(max_iterations):
            # Pick up to ALPHA unqueried candidates
            batch = []
            for node_id, ip, port in candidates:
                if (ip, port) not in queried:
                    batch.append((node_id, ip, port))
                if len(batch) >= ALPHA:
                    break

            if not batch:
                break   # nothing new to query

            addrs  = [(ip, port) for _, ip, port in batch]
            tasks  = [self.get_peers((ip, port)) for _, ip, port in batch]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            queried.update(addrs)

            new_nodes = []
            for addr, res in zip(addrs, results):
                if not isinstance(res, dict):
                    continue

                # Track token for announce_peer
                if b"token" in res:
                    tokens[addr] = res[b"token"]

                # 'values' → compact peer list  (we found peers!)
                if b"values" in res:
                    for peer_bytes in res[b"values"]:
                        if isinstance(peer_bytes, bytes):
                            self.found_peers.update(decode_peers(peer_bytes))

                # 'nodes' → closer nodes to explore
                if b"nodes" in res:
                    closer = decode_nodes(res[b"nodes"])
                    for node_id, ip, port in closer:
                        self.routing_table.add_node(node_id, ip, port)
                    new_nodes.extend(closer)

            print(f"[DHT] Iteration {iteration + 1}: "
                  f"{len(self.found_peers)} peers found so far.")

            if self.found_peers:
                break   # stop as soon as we have peers

            # Merge new nodes into candidates and re-sort by XOR distance
            combined = candidates + new_nodes
            combined.sort(key=lambda n: xor_distance(n[0], self.info_hash))
            candidates = combined[:K * 2]   # keep a wider pool

        # Announce ourselves to nodes that gave us tokens (be a good DHT citizen)
        if tokens:
            announce_tasks = [
                self.announce_peer(addr, token)
                for addr, token in list(tokens.items())[:5]
            ]
            await asyncio.gather(*announce_tasks, return_exceptions=True)
            print(f"[DHT] Announced to {len(announce_tasks)} node(s).")

        print(f"[DHT] Done — {len(self.found_peers)} peer(s) found.")
        return self.found_peers

    # ── Lifecycle ─────────────────────────────

    async def start(self):
        """Bind UDP socket and bootstrap into the DHT network."""
        loop = asyncio.get_event_loop()
        self.transport, _ = await loop.create_datagram_endpoint(
            lambda: DHTProtocol(self),
            local_addr=("0.0.0.0", self.port),
        )
        await self.bootstrap()

    def stop(self):
        if self.transport:
            self.transport.close()
            self.transport = None


# ── Public entry point ────────────────────────

async def dht_get_peers(info_hash: bytes, port: int = 6882) -> set:
    """
    Convenience wrapper — starts a DHTNode, finds peers, stops it, returns peers.

    Call this from get_new_peers.py:

        from dht import dht_get_peers
        dht_peers = await dht_get_peers(mh.info_hash)
        new_peers.update(dht_peers)
    """
    node = DHTNode(info_hash, port=port)
    try:
        await node.start()
        return await node.find_peers()
    finally:
        node.stop()
