import binascii
import hashlib  # 信息安全加密
import json
import os
import random
import threading
import time
import socket
from urllib.parse import urlparse  # 网络编码解码
import requests  # 生成网络请求
from flask import Flask, jsonify, request  # 请求，网络请求
from typing import Any, Dict, List, Optional  # 数据结构
from network.broadcastmain import NetworkBroadcast
from collections import Counter as caFORLEADER
import election

port = 5000


class DaDaCoinBlockChain:

    def __init__(self):  # 初始化
        self.current_transactions = []  # 交易列表
        self.chain = []  # 区块链管理多个区块
        self.nodes = set()  # 保存网络中的多个节点
        if os.path.exists("last_game_result.txt"):
            with open("last_game_result.txt", "r") as f:
                read_data = f.read()
                self.new_block(previous_hash=read_data)
        else:
            self.new_block(previous_hash="Game deplyed TODAY! Genius Block!")  # 创建创世区块
        self.node_proposes = {}  # 保存节点提案
        self.all_nodes_votes = []  # 保存节点投票
        self.leader = "" # 本地leader
        self.leaders = [] # 保存其他节点广播的leader

    def new_block(self,
                  previous_hash: Optional[str]) -> Dict[str, Any]:  # 创建一个区块，返回字典数据类型
        block = {
            "index": len(self.chain) + 1,  # 索引
            "timestamp": time.time(),  # 时间戳
            "transactions": self.current_transactions,  # 当前的交易
            "previous_hash": previous_hash or self.hash(self.chain[-1])  # 前一块的哈希
        }
        self.current_transactions = []  # 交易记录加入区块后被清空
        self.chain.append(block)  # 区块加入区块链
        return block

    def new_transactions(self, sender: str, recipient: str, amount: int) -> int:  # 创建一个交易
        self.current_transactions.append({
            "sender": sender,  # 付款方
            "recipient": recipient,  # 收款方
            "amount": amount  # 交易金额
        })
        return self.last_block["index"] + 1  # 索引标记交易的数量

    @property
    def last_block(self) -> Dict[str, any]:  # 取得最后一个区块
        return self.chain[-1]

    @staticmethod
    def hash(block: Dict[str, any]) -> str:  # 哈希加密传递一个字典返回字符串
        blockstring = json.dumps(block, sort_keys=True).encode()  # 编码
        return hashlib.sha3_256(blockstring).hexdigest()  # 取出编码16进制的哈希

    def register_node(self, addr: str) -> None:  # 加入网络的其他节点，用于更新
        now_url = urlparse(addr)  # 解析网络
        self.nodes.add(now_url.netloc)  # 增加网络节点

    def valid_chain(self, chain: List[Dict[str, any]]) -> bool:  # 区块链校验
        # List[Dict[str,any]是一个列表，列表的每一个元素都是字典
        last_block = chain[0]  # 第一个区块
        curr_index = 1  # 当前的第一个索引
        while curr_index < len(chain):
            block = chain[curr_index]
            # 哈希校验,校验区块链的连接
            if block["previous_hash"] != self.hash():
                return False
            last_block = block  # 轮替循环
            curr_index += 1
        return True

    def resolve_conflicts(self) -> bool:  # 共识算法
        # 网络中的多个节点，取出最长的
        neighbours = self.nodes  # 取得所有节点
        new_chain = None  # 新的区块链
        max_length = len(self.chain)  # 当前的区块链长度
        for node in neighbours:
            response = requests.get(f"http://{node}/chain")  # 访问网络节点
            if response.status_code == 200:
                length = response.json()["length"]  # 取出长度
                chain = response.json()["chain"]  # 取出区块链
                # 如果当前区块链长度比较长
                if length > max_length:
                    max_length = length
                    new_chain = chain  # 保存长度与区块链
        if new_chain:
            self.chain = new_chain  # 替换区块链
            return True
        return False


app = Flask(__name__)  # 初始化Flask框架

dadacoin = DaDaCoinBlockChain()  # 创建一个网络节点


@app.route("/")
def index_page():
    return "Welcome to DadaCoin..."


@app.route("/chain")  # 查看所有的区块链
def index_chain():
    response = {
        "chain": dadacoin.chain,  # 区块链
        "length": len(dadacoin.chain)  # 区块链的长度
    }
    return jsonify(response), 200  # 展示区块链


global leader
leader = "127.0.0.1:5000"


@app.route("/mine")  # 挖矿
def index_mine():
    global leader
    '''
    if request.host.replace("localhost:", "127.0.0.1:") != miner:
        return "该节点不是矿工" + request.host.replace("localhost:", "127.0.0.1:"), 400
    '''

    # 系统奖励比特币挖矿产生交易
    dadacoin.new_transactions(
        sender="0",  # 系统奖励
        recipient=leader,  # 当前钱包
        amount=10,
    )
    block = dadacoin.new_block(None)  # 增加一个区块
    response = {
        "message": "新的区块创建",
        "index": block["index"],  # 创建索引
        "transactions": block["transactions"],  # 交易
        "previous_hash": block["previous_hash"]  # 前一块的哈希
    }
    return jsonify(response), 200


@app.route("/new_transactions", methods=["POST"])  # 实现交易
def new_transactions():
    values = request.get_json()  # 抓取网络传输的信息
    required = ["sender", "recipient", "amount"]
    if not all(key in values for key in required):
        return "数据不完整或格式错误", 400
    index = dadacoin.new_transactions(values["sender"], values["recipient"], values["amount"])

    response = {
        "message": f"交易加入到区块{index}"
    }
    return jsonify(response), 200


@app.route("/new_node", methods=["POST"])  # 新注册节点
def new_node():
    values = request.get_json()  # 获取json字符串
    nodes = values.get("nodes")  # 获取所有的节点
    if nodes is None:
        return "没有节点信息", 400
    for node in nodes:
        dadacoin.register_node(node)  # 增加网络节点
    response = {
        "message": f"网络节点已经被追加",
        "nodes": list(dadacoin.nodes),  # 查看所有节点
    }
    return jsonify(response), 200


@app.route("/check_node", methods=["GET"])  # 新注册节点
def check_node():
    response = {
        "message": f"Now nodes info",
        "nodes": list(dadacoin.nodes),  # 查看所有节点
    }
    return jsonify(response), 200


@app.route("/node_refresh", methods=["POST"])  # 更新节点
def node_refresh():
    replaced = dadacoin.resolve_conflicts()  # 共识算法进行替换
    if replaced:
        response = {
            "message": "区块链已经被替换为最长",
            "new-chain": dadacoin.chain,
        }
    else:
        response = {
            "message": "当前区块链已经是最长无需替换",
            "new-chain": dadacoin.chain
        }
    return jsonify(response), 200


@app.route("/election")
def show_election():
    global leader
    alpha_string = binascii.unhexlify(dadacoin.hash(dadacoin.last_block))
    print("----- Part 1  Committee Election -----")
    committee_nodes = election.committee_election(alpha_string, dadacoin.nodes)
    print("The Committee consists of nodes:" + "\n" + ', '.join(map(str, committee_nodes)) + "\n")
    print("----- Part 2  Leader Election -----")
    leader = election.leader_election(alpha_string, committee_nodes)
    response = {
        "message": "A leader has been elected",
        "committee nodes": committee_nodes,
        "leader": leader
    }
    return jsonify(response), 200


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
                                      args=(dadacoin,))
    receive_thread.start()
    print("This node initialized, preparing registering! This is node " + node_info)
    # ask for register

    send_thread = threading.Thread(target=peer.to_send_message, args=())
    send_thread.start()
    time.sleep(10)
    while True:
        peer.to_send_new_node_self_request_register(node_info)
        time.sleep(10)
        if len(dadacoin.nodes) == 10:
            print("Registered Successfully")
            break
    time.sleep(10)
    alpha_string = binascii.unhexlify(dadacoin.hash(dadacoin.last_block))
    print("----- Part 1  Committee Election -----")
    committee_nodes = election.committee_election(alpha_string, dadacoin.nodes)
    print("The Committee consists of nodes:" + "\n" + ', '.join(map(str, committee_nodes)) + "\n")
    print("----- Part 2  Leader Election -----")
    leader = election.leader_election(alpha_string, committee_nodes)
    dadacoin.leader = leader
    while True:
        peer.to_send_leader(leader)
        time.sleep(10)
        if len(dadacoin.leaders) == 10:
            print("Leaders Registered Successfully")
            break
    time.sleep(10)
    # 选择leaders里面重复次数最多的作为新的leader
    new_leader = caFORLEADER(dadacoin.leaders).most_common(1)[0][0]
    leader = new_leader
    print("leader: "+new_leader)
    time.sleep(10)
    # run_consensus
    print("----- Part 3  Vote Consensus-----")
    while True:
        # 如果是leader就广播自己的随机数
        print(leader)
        print(peer.node_id)
        if peer.node_id == leader:
            print("I'm the leader")
            peer.to_send_leader_vote()
            peer.broadcast_node_vote()
        # 如果不是leader就接收随机数，然后广播自己对随机数的投票，YES OR NO
        else:
            print("I'm not the leader")
            peer.broadcast_node_vote()
        # 所有人都收到了投票，就开始计算，如果大于一半的人同意，就将之前收到的随机数当作自己的随机数保存
        # 如果没有大于一半的人同意，就重新开始
        time.sleep(20)
        final_result = peer.run_node_consensus(dadacoin.all_nodes_votes)
        if final_result is not None:
            print("Final Consensus Result: {}".format(dadacoin.node_proposes))
            if peer.node_id == leader:
                with open("last_game_result.txt", "w") as last_game_result:
                    last_game_result.write(str(dadacoin.node_proposes))
            break
        else:
            # 如果没有大于一半的人同意，就重新开始
            dadacoin.all_nodes_votes = []
            dadacoin.leader = ""
            dadacoin.leaders = []
            print("No consensus reached, restart")
