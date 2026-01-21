# Lab 3: Consensus (Raft Lite) Deployment
This project implements a simplified version of the Raft consensus protocol (Raft Lite) across 3–5 EC2 nodes. It handles leader election, heartbeats, log replication, and majority-based commits to ensure data consistency and fault tolerance.

## Setup & Run
1. Start Nodes: On each EC2 instance, run the server using its private IP:
- Node A: 
```bash
python3 node.py --id A --port 8000 --peers http://<IP_B>:8001,http://<IP_C>:8002 
```
- Node B:
```bash
python3 node.py --id B --port 8001 --peers http://<IP_A>:8000,http://<IP_C>:8002 
```
- Node C:
```bash
python3 node.py --id C --port 8002 --peers http://<IP_A>:8000,http://<IP_B>:8001 
```
2. Use Client: Use the CLI to interact with the cluster and observe the consensus state:
```bash
curl -X POST http://<LEADER_IP>:<LEADER_PORT>/client \
     -H "Content-Type: application/json" \
     -d '{"cmd": "SET x= "}'
```

## System Requirements

* Leader Election: Nodes transition from Follower to Candidate if a heartbeat timeout occurs, becoming a Leader upon receiving a majority of votes.
* Log Replication: The Leader appends commands to its log and replicates them to followers via AppendEntries.
* Majority Commit: Entries are considered committed only after being acknowledged by a majority of the cluster.
* Failure Recovery: If the Leader process is killed, the cluster will automatically elect a new leader.
