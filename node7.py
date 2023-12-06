import binascii
import hashlib  # encryption
import json
import os
import random
import threading
import time
import socket
from urllib.parse import urlparse  # encode and decode
import requests  # 生成网络请求
from flask import Flask, jsonify, request  # request
from typing import Any, Dict, List, Optional
from network.broadcastmain import NetworkBroadcast
from collections import Counter as caFORLEADER
import election

# this node port, 5001 for seed node
port = 5007


##### THIS blockchain prototype is referred to open libraries, the transaction parts of the program are useless
##### The contribution of us is to change its consensus and alogorithm part and add network communication

class GameRNBlockChain:

    def __init__(self):  # initialize
        self.current_transactions = []  # the list of transaction
        self.chain = []  # the chain list
        self.nodes = set()  # 保save all nodes
        # check whether the last game result existed, otherwise use the genius block data
        if os.path.exists("last_game_result.txt"):
            with open("last_game_result.txt", "r") as f:
                read_data = f.read()
                self.new_block(previous_hash=read_data)
        else:
            # no game result, use the genius block data
            self.new_block(previous_hash="Game deplyed TODAY! Genius Block!")
        self.node_proposes = {}  # save the proposed RN from this node
        self.all_nodes_votes = []  # save the vote from nodes
        self.leader = ""  # the local save leader
        self.leaders = []  # save the leaders received from other nodes via broadcast

    def new_block(self,
                  previous_hash: Optional[str]) -> Dict[str, Any]:  # new a block as a dictionary
        block = {
            "index": len(self.chain) + 1,  # index
            "timestamp": time.time(),  # timestamp
            "transactions": self.current_transactions,  # current transaction
            "previous_hash": previous_hash or self.hash(self.chain[-1])  # previous block hash
        }
        self.current_transactions = []  # clear all transactions when they are written in block
        self.chain.append(block)  # add block to the chain
        return block

    def new_transactions(self, sender: str, recipient: str, amount: int) -> int:  # create a new transaction
        self.current_transactions.append({
            "sender": sender,  # payer
            "recipient": recipient,  # receiver
            "amount": amount  # amount
        })
        return self.last_block["index"] + 1  # index of TX

    @property
    def last_block(self) -> Dict[str, any]:  # get the last block
        return self.chain[-1]

    @staticmethod
    def hash(block: Dict[str, any]) -> str:  # pass a dictionary and get a hash
        blockstring = json.dumps(block, sort_keys=True).encode()  # encode
        return hashlib.sha3_256(blockstring).hexdigest()  # get the HEX hash

    def register_node(self, addr: str) -> None:  # add and register other node automaticcal
        now_url = urlparse(addr)  # to parse node list
        self.nodes.add(now_url.netloc)  # add node

    def valid_chain(self, chain: List[Dict[str, any]]) -> bool:  # valid the chain
        # List[Dict[str,any] a list of dictionary
        last_block = chain[0]  # the first block
        curr_index = 1  # current first index
        while curr_index < len(chain):
            block = chain[curr_index]
            # valid by hash, valid the connection of chain
            if block["previous_hash"] != self.hash():
                return False
            last_block = block  # to loop
            curr_index += 1
        return True

    def resolve_conflicts(self) -> bool:  # consensus
        # get the longest chain
        neighbours = self.nodes  # get all node
        new_chain = None  # 新的区块链
        max_length = len(self.chain)  # get now length
        for node in neighbours:
            response = requests.get(f"http://{node}/chain")  # access each node
            if response.status_code == 200:
                length = response.json()["length"]  # get each node length
                chain = response.json()["chain"]  # get chain
                # if longer in this node
                if length > max_length:
                    max_length = length
                    new_chain = chain  # save the length
        if new_chain:
            self.chain = new_chain  # follow the longest
            return True
        return False


app = Flask(__name__)  # initial flask

gameChain = GameRNBlockChain()  # create a node


@app.route("/")
def index_page():
    return "Welcome to gameChain..."


@app.route("/chain")  # check each node
def index_chain():
    response = {
        "chain": gameChain.chain,  # block chain
        "length": len(gameChain.chain)  # the length of chain
    }
    return jsonify(response), 200  # to show the chain


# define initial leader
global leader
leader = "127.0.0.1:5000"


@app.route("/mine")  # mine
def index_mine():
    global leader

    # reward
    gameChain.new_transactions(
        sender="0",  # reward
        recipient=leader,  # now wallet
        amount=10,
    )
    block = gameChain.new_block(None)  # add a new block
    response = {
        "message": "add new block",
        "index": block["index"],  # create index
        "transactions": block["transactions"],  # TX
        "previous_hash": block["previous_hash"]  # previous hash
    }
    return jsonify(response), 200


@app.route("/new_transactions", methods=["POST"])  # to new transaction
def new_transactions():
    values = request.get_json()  # get info from network
    required = ["sender", "recipient", "amount"]
    if not all(key in values for key in required):
        return "format error", 400
    index = gameChain.new_transactions(values["sender"], values["recipient"], values["amount"])

    response = {
        "message": f"add TX{index}"
    }
    return jsonify(response), 200


@app.route("/new_node", methods=["POST"])  # register a new node
def new_node():
    values = request.get_json()  # get json
    nodes = values.get("nodes")  # get all nodes
    if nodes is None:
        return "no nodes", 400
    for node in nodes:
        gameChain.register_node(node)  # add node
    response = {
        "message": f"noded added",
        "nodes": list(gameChain.nodes),  # check all node
    }
    return jsonify(response), 200


@app.route("/check_node", methods=["GET"])  # register a new node
def check_node():
    response = {
        "message": f"Now nodes info",
        "nodes": list(gameChain.nodes),  # check all node
    }
    return jsonify(response), 200


@app.route("/node_refresh", methods=["POST"])  # update node
def node_refresh():
    replaced = gameChain.resolve_conflicts()  # follow by consensus
    if replaced:
        response = {
            "message": "updated to the longest chain",
            "new-chain": gameChain.chain,
        }
    else:
        response = {
            "message": "already the longest chain",
            "new-chain": gameChain.chain
        }
    return jsonify(response), 200

##### election of leader
@app.route("/election")
def show_election():
    global leader
    alpha_string = binascii.unhexlify(gameChain.hash(gameChain.last_block))
    print("----- Part 1  Committee Election -----")
    committee_nodes = election.committee_election(alpha_string, gameChain.nodes)
    print("The Committee consists of nodes:" + "\n" + ', '.join(map(str, committee_nodes)) + "\n")
    print("----- Part 2  Leader Election -----")
    leader = election.leader_election(alpha_string, committee_nodes)
    response = {
        "message": "A leader has been elected",
        "committee nodes": committee_nodes,
        "leader": leader
    }
    return jsonify(response), 200


#### to start a server
def start_server():
    app.run("127.0.0.1", port, threaded=True)  # Node 1


if __name__ == "__main__":
    server_thread = threading.Thread(target=start_server)
    server_thread.start()
    # initial network peer
    address_pair = ("127.0.0.1", port)
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind((address_pair[0], address_pair[1]))
    peer = NetworkBroadcast()
    peer.node_id = "127.0.0.1" + ":" + str(port)
    node_info = "http://" + "127.0.0.1" + ":" + str(port)
    peer.udp_socket = udp_socket
    # print(address_pair, peer.node_id)
    peer.to_start_peer()
    # initial thread to receive message
    receive_thread = threading.Thread(target=peer.to_receiver_message,
                                      args=(gameChain,))
    receive_thread.start()
    print("This node initialized, preparing registering! This is node " + node_info)
    # ask for register

    send_thread = threading.Thread(target=peer.to_send_message, args=())
    send_thread.start()
    time.sleep(10)
    while True:
        peer.to_send_new_node_self_request_register(node_info)
        time.sleep(10)
        if len(gameChain.nodes) == 10:
            print("Registered Successfully")
            break
    time.sleep(10)
    alpha_string = binascii.unhexlify(gameChain.hash(gameChain.last_block))
    print("----- Part 1  Committee Election -----")
    committee_nodes = election.committee_election(alpha_string, gameChain.nodes)
    print("The Committee consists of nodes:" + "\n" + ', '.join(map(str, committee_nodes)) + "\n")
    print("----- Part 2  Leader Election -----")
    leader = election.leader_election(alpha_string, committee_nodes)
    gameChain.leader = leader
    while True:
        peer.to_send_leader(leader)
        time.sleep(10)
        if len(gameChain.leaders) == 10:
            print("Leaders Registered Successfully")
            break
    time.sleep(10)
    # get the most repeat times nodes as the leader
    new_leader = caFORLEADER(gameChain.leaders).most_common(1)[0][0]
    leader = new_leader
    print("leader: " + new_leader)
    time.sleep(10)
    # run_consensus
    print("----- Part 3  Vote Consensus-----")
    while True:
        # broadcast self RN if I am the leader
        print(leader)
        print(peer.node_id)
        if peer.node_id == leader:
            print("I'm the leader")
            peer.to_send_leader_vote()
            peer.broadcast_node_vote()
        # If not leader, receive RN from others, and broadcast the vote for RN (YES or NO)
        else:
            print("I'm not the leader")
            peer.broadcast_node_vote()
        # if all received vote, then calculate. If half of nodes agree, regard the received RN as self RN
        # otherwise less than half of people, restart the vote
        time.sleep(20)
        final_result = peer.run_node_consensus(gameChain.all_nodes_votes)
        if final_result is not None:
            print("Final Consensus Result: {}".format(gameChain.node_proposes))
            if peer.node_id == leader:
                with open("last_game_result.txt", "w") as last_game_result:
                    last_game_result.write(str(gameChain.node_proposes))
            break
        else:
            # otherwise less than half of people, restart
            gameChain.all_nodes_votes = []
            gameChain.leader = ""
            gameChain.leaders = []
            print("No consensus reached, restart")
