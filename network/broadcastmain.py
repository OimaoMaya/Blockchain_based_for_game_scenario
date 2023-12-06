import json
import random
import socket
import sys
import threading
import time

from election import *

# seed node must be turn on first
seed = ("127.0.0.1", 5001)

#######
# network package fromat
# {
#     type:
#     data:
# }
# data will pack in JSON
#######

class NetworkBroadcast:
    seed = seed
    peers = {}
    node_id = ""
    udp_socket = {}

    # will do SOMETHING according to action tag
    def to_receiver_message(self, gamechain):

        while 1:
            data, address = receive_message_base(self.udp_socket)
            action = json.loads(data)
            # handshake message
            if action['type'] == 'newpeer':
                print("A new player is coming")
                self.peers[action['data']] = address
                sendJS(self.udp_socket, address, {
                    "type": 'peers',
                    "data": self.peers
                })
            # handshake message
            if action['type'] == 'peers':
                print("Received a bunch of players")
                self.peers.update(action['data'])
                # introduce youself. 
                broadcastJS(self.udp_socket, {
                    "type": "introduce",
                    "data": self.node_id
                }, self.peers)
            # handshake message
            if action['type'] == 'introduce':
                print("Get a new player.")
                self.peers[action['data']] = address

            if action['type'] == 'input':
                print(action['data'])

            # a new player is ready
            if action['type'] == 'newNodeReady':
                node_data = action['data']
                if node_data is None:
                    print("No new player information")
                gamechain.register_node(node_data)  # add network node
                print("Added new player: " + node_data)
                print("now info:")
                print(list(gamechain.nodes))

            # the leader vote from other node
            if action['type'] == 'leader':
                print("leader from others: " + action['data'])
                gamechain.leaders.append(action['data'])

            # ask for POV vote
            if action['type'] == 'POV_vote_request':
                random_numbers = action['data']['random_numbers']
                gamechain.node_proposes = random_numbers

            # to vote node
            if action['type'] == 'POV_node_vote':
                vote = action['data']['vote']
                print("received vote: " + vote)
                gamechain.all_nodes_votes.append(vote)

            # exit
            if action['type'] == 'exit':
                if self.node_id == action['data']:
                    # cannot be closed too fast.
                    time.sleep(0.5)
                    break
                    # self.udp_socket.close()
                value, key = self.peers.pop(action['data'])
                print(action['data'] + " left the chain.")

    # start peer
    def to_start_peer(self):
        sendJS(self.udp_socket, self.seed, {
            "type": "newpeer",
            "data": self.node_id
        })

    # to send message function, useless in thread
    def to_send_message(self):
        while 1:
            # mark $ for the messages from this node
            msg_input = input("$:")
            if msg_input == "exit":
                broadcastJS(self.udp_socket, {
                    "type": "exit",
                    "data": self.node_id
                }, self.peers)
                break
            # check online node list
            if msg_input == "node_list":
                print(self.peers)
                continue
            l = msg_input.split()

            if l[0] == "*NEW*":
                toA = self.peers[l[-1]]
                s = ' '.join(l[:-1])
                sendJS(self.udp_socket, toA, {
                    "type": "input",
                    "data": s
                })

            elif l[-1] in self.peers.keys():
                toA = self.peers[l[-1]]
                s = ' '.join(l[:-1])
                sendJS(self.udp_socket, toA, {
                    "type": "input",
                    "data": s
                })
            # no receiver assigned, broadcast the message yo all nodes
            else:
                broadcastJS(self.udp_socket, {
                    "type": "input",
                    "data": msg_input
                }, self.peers)
                continue

    def to_send_new_node_self_request_register(self, msg_input: str):
        broadcastJS(self.udp_socket, {
            "type": "newNodeReady",
            "data": msg_input
        }, self.peers)

    def to_send_leader(self, msg_input: str):
        broadcastJS(self.udp_socket, {
            "type": "leader",
            "data": msg_input
        }, self.peers)

    def to_send_leader_vote(self):
        random_numbers = []
        for i in range(10):
            random_numbers.append(
                random.getrandbits(256).to_bytes(32, 'little').hex()
            )
        message = {
            "type": "POV_vote_request",
            "data": {
                "random_numbers": random_numbers,
                "node_id": self.node_id
            }
        }
        print(message)
        broadcastJS(self.udp_socket, message, self.peers)

    def broadcast_node_vote(self):
        # broadcast vote result
        voteR = "YES" if random.choice([True, False]) else "NO"
        message = {
            "type": "POV_node_vote",
            "data": {
                "node_id": self.node_id,
                "vote": voteR
            }
        }
        print(message)
        broadcastJS(self.udp_socket, message, self.peers)

    def run_node_consensus(self, all_nodes_votes):
        print(all_nodes_votes)
        # to do consensus, the final consensus will be the most voted result
        final_result = None
        if all_nodes_votes.count("YES") >= len(self.peers) / 2:
            return True
        else:
            return None


# send data , to address. BASIC SEND FUNCTION
def sendmbase(udp_socket, to_receiver_address, message):
    # [0]: IP address, [1] port
    udp_socket.sendto(message.encode(), (to_receiver_address[0], to_receiver_address[1]))


# receive message
# return message, and address.
def receive_message_base(udp_socket):
    data, address = udp_socket.recvfrom(1024)
    return data.decode(), address


def sendJS(udp_socket, toA, message):
    #     print(toA)
    sendmbase(udp_socket, toA, json.dumps(message))


def broadcastms(udp_socket, message, peers):
    for p in peers.values():
        sendmbase(udp_socket, p, message)


def broadcastJS(udp_socket, message, peers):
    for p in peers.values():
        sendJS(udp_socket, p, message)


def rece(udp_socket):
    while 1:
        data, addr = receive_message_base(udp_socket)
        print(data)


def send(udp_socket):
    while 1:
        msg = input("please input message and port:")
        l = msg.split()
        port = int(l[-1])
        s = ' '.join(l[:-1])
        toA = ('127.0.0.1', port)
        sendmbase(udp_socket, toA, s)
