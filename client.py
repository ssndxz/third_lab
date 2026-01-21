
import requests
import argparse
import json
import sys

def find_leader(nodes):
    """Find the current leader by querying all nodes"""
    for node in nodes:
        try:
            response = requests.get(f"http://{node}/status", timeout=1)
            if response.status_code == 200:
                data = response.json()
                if data["state"] == "Leader":
                    return node, data
        except:
            pass
    return None, None

def send_command(node, command):
    """Send a command to a node"""
    try:
        response = requests.post(
            f"http://{node}/command",
            json={"command": command},
            timeout=2
        )
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        return {"success": False, "message": str(e)}

def get_cluster_status(nodes):
    """Get status of all nodes in the cluster"""
    statuses = []
    for node in nodes:
        try:
            response = requests.get(f"http://{node}/status", timeout=1)
            if response.status_code == 200:
                statuses.append(response.json())
            else:
                statuses.append({"node_id": node, "status": "unreachable"})
        except:
            statuses.append({"node_id": node, "status": "unreachable"})
    return statuses

def main():
    parser = argparse.ArgumentParser(description='Raft Lite Client')
    parser.add_argument('--nodes', required=True, 
                       help='Comma-separated node addresses (ip:port)')
    parser.add_argument('--command', help='Command to send (e.g., "SET x=5")')
    parser.add_argument('--status', action='store_true', 
                       help='Get cluster status')
    args = parser.parse_args()
    
    nodes = args.nodes.split(',')
    
    if args.status:
        print("\n=== Cluster Status ===")
        statuses = get_cluster_status(nodes)
        for status in statuses:
            if "status" in status and status["status"] == "unreachable":
                print(f"Node {status['node_id']}: UNREACHABLE")
            else:
                print(f"Node {status['node_id']}:")
                print(f"  State: {status['state']}")
                print(f"  Term: {status['term']}")
                print(f"  Log Length: {status['log_length']}")
                print(f"  Commit Index: {status['commit_index']}")
                print(f"  Leader: {status.get('leader', 'None')}")
        return
    
    if args.command:
        print(f"\nFinding leader...")
        leader, leader_status = find_leader(nodes)
        
        if not leader:
            print("Error: No leader found in cluster!")
            sys.exit(1)
        
        print(f"Leader found: {leader} (term {leader_status['term']})")
        print(f"Sending command: {args.command}")
        
        result = send_command(leader, args.command)
        
        if result["success"]:
            print(f"✓ Success: {result['message']}")
        else:
            print(f"✗ Failed: {result['message']}")
            
            if "Not leader" in result["message"]:
                print("\nRetrying with current leader...")
                leader, _ = find_leader(nodes)
                if leader:
                    result = send_command(leader, args.command)
                    if result["success"]:
                        print(f"✓ Success: {result['message']}")

if __name__ == "__main__":
    main()