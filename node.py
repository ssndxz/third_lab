import json
import time
import random
import threading
import requests
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer

class RaftNode:
    def __init__(self, node_id, port, peers):
        self.id = node_id
        self.port = port
        self.peers = peers

        self.state = "Follower"
        self.currentTerm = 0
        self.votedFor = None

        self.log = []
        self.commitIndex = -1

        self.last_heartbeat = time.time()
        self.lock = threading.Lock()

    def election_timeout(self):
        return random.uniform(3, 5)

    def start_election(self):
        with self.lock:
            self.state = "Candidate"
            self.currentTerm += 1
            self.votedFor = self.id
            term = self.currentTerm

        votes = 1
        print(f"[Node {self.id}] Timeout → Candidate (term {term})")

        for peer in self.peers:
            try:
                r = requests.post(
                    f"http://{peer}/request_vote",
                    json={"term": term, "candidateId": self.id},
                    timeout=1
                )
                if r.json().get("voteGranted"):
                    votes += 1
            except:
                pass

        if votes > (len(self.peers) + 1) // 2:
            self.become_leader()

    def become_leader(self):
        with self.lock:
            self.state = "Leader"
        print(f"[Node {self.id}] Became Leader (term {self.currentTerm})")
        threading.Thread(target=self.send_heartbeats, daemon=True).start()

    def send_heartbeats(self):
        while self.state == "Leader":
            for peer in self.peers:
                try:
                    requests.post(
                        f"http://{peer}/append_entries",
                        json={
                            "term": self.currentTerm,
                            "leaderId": self.id,
                            "entries": []
                        },
                        timeout=1
                    )
                except:
                    pass
            time.sleep(1)

    def run_background(self):
        while True:
            if self.state != "Leader":
                if time.time() - self.last_heartbeat > self.election_timeout():
                    self.start_election()
            time.sleep(0.2)

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers["Content-Length"])
        data = json.loads(self.rfile.read(length))

        if self.path == "/request_vote":
            self.handle_request_vote(data)
        elif self.path == "/append_entries":
            self.handle_append_entries(data)
        elif self.path == "/client":
            self.handle_client(data)
        else:
            self.send_response(404)
            self.end_headers()

    def handle_request_vote(self, data):
        with node.lock:
            if data["term"] > node.currentTerm:
                node.currentTerm = data["term"]
                node.votedFor = None
                node.state = "Follower"

            voteGranted = False
            if node.votedFor is None:
                node.votedFor = data["candidateId"]
                voteGranted = True

        self.respond({"voteGranted": voteGranted})

    def handle_append_entries(self, data):
        with node.lock:
            if data["term"] >= node.currentTerm:
                node.currentTerm = data["term"]
                node.state = "Follower"
                node.last_heartbeat = time.time()

                if data["entries"]:
                    node.log.extend(data["entries"])
                    print(f"[Node {node.id}] Append success")

                self.respond({"success": True})
            else:
                self.respond({"success": False})

    def handle_client(self, data):
        if node.state != "Leader":
            self.respond({"error": "Not leader"})
            return

        entry = {
            "term": node.currentTerm,
            "cmd": data["cmd"]
        }

        node.log.append(entry)
        index = len(node.log) - 1
        acks = 1

        print(f"[Leader {node.id}] Append log entry {entry}")

        for peer in node.peers:
            try:
                r = requests.post(
                    f"http://{peer}/append_entries",
                    json={
                        "term": node.currentTerm,
                        "leaderId": node.id,
                        "entries": [entry]
                    },
                    timeout=1
                )
                if r.json().get("success"):
                    acks += 1
            except:
                pass

        if acks > (len(node.peers) + 1) // 2:
            node.commitIndex = index
            print(f"[Leader {node.id}] Entry committed (index={index})")

        self.respond({"status": "OK"})

    def respond(self, obj):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

parser = argparse.ArgumentParser()
parser.add_argument("--id", required=True)
parser.add_argument("--port", type=int, required=True)
parser.add_argument("--peers", required=True)
args = parser.parse_args()

peers = args.peers.split(",")
node = RaftNode(args.id, args.port, peers)

threading.Thread(target=node.run_background, daemon=True).start()

server = HTTPServer(("", args.port), Handler)
print(f"[Node {node.id}] Running on port {args.port}")
server.serve_forever()
