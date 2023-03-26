# -*- coding: utf8 -*-
import json
import math
import time
from hashlib import sha256

import requests
from flask import Flask, request


# 节点服务

# 区块
class Block:
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        f"""
        Block的构造函数
        :param index: 区块ID，全局唯一
        :param transactions: 交易数据
        :param timestamp: 生成该区块时的时间戳
        :param previous_hash: 前一个区块的哈希
        :param nonce: 自定义修改的值
        :return: new Block
        """
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

    def compute_hash(self) -> str:
        f"""
        计算该区块所存储数据的哈希
        :return: sha256
        """
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain:
    # 前导0的个数，工作量证明
    # difficulty = 2

    def __init__(self):
        self.unconfirmed_transactions = []  # 未确认的交易，待加入区块链中
        self.chain = []
        self.difficulty = 2

    def create_genesis_block(self):
        """
        创建第一个区块
        """
        genesis_block = Block(0, [], time.time(), "0")
        self.chain.append(genesis_block)

    #  使方法变为只读属性
    @property
    def last_block(self):
        """
        获取最后一个区块
        """
        if len(self.chain) == 0:
            return {}
        return self.chain[-1]

    def proof_of_work(self, block):
        f"""
        尝试不同的nonce计算满足difficulty要求的哈希
        :param block: Block
        :return: computed_hash
        """
        block.nonce = 0
        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * self.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()
        return computed_hash

    def add_block(self, block: Block, proof: str) -> bool:
        f"""
        将新区块加入链中，验证规则包括该区块{block}的previous_hash为链中最后一个块的哈希
        该区块的哈希满足前导0的个数满足要求difficulty
        :param block: 新的区块
        :param proof: 该新区快的哈希
        :return: 符合规则加入链中，返回true，其它false
        """
        if len(self.chain) == 0:
            if block.compute_hash() == proof:
                self.chain.append(block)
                return True
            else:
                return False
        previous_hash = self.last_block.compute_hash()  # 最后一个块的哈希
        if previous_hash != block.previous_hash:
            return False

        if not self.is_valid_proof(block, proof):
            return False

        self.chain.append(block)
        if self.difficulty != math.floor(math.log2(len(self.chain))) + 2:
            self.difficulty = math.floor(math.log2(len(self.chain))) + 2
        return True

    def is_valid_proof(self, block: Block, block_hash: str) -> bool:
        """
        判断某一个区块是否满足工作量要求
        :param block: 区块
        :param block_hash: 区块的哈希
        :return: 满足difficulty为true否则为false
        """
        return block_hash.startswith('0' * self.difficulty) and block_hash == block.compute_hash()

    def add_new_transaction(self, transaction):
        """
        添加新的交易
        :param transaction: 新的交易
        :return: None
        """
        self.unconfirmed_transactions.append(transaction)

    def mine(self):
        """
        将未确认的交易加入区块链中
        :return: 存在新的交易时，返回新的区块的index,否则返回False
        """
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block
        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.compute_hash())

        proof = self.proof_of_work(new_block)
        self.add_block(new_block, proof)
        self.unconfirmed_transactions = []
        return new_block.index

    @classmethod
    def check_chain_validity(cls, _chain):
        """
        检查当前的区块链_chain是否满足要求
        :param _chain: 传入的区块链
        :return: 该区块链是否合法
        """
        result = True
        previous_hash = "0"

        for block in _chain:
            block_hash = block.compute_hash()  # 当前块的哈希
            if previous_hash != block.previous_hash:
                result = False
                break
            previous_hash = block_hash
        return result


def allow_cors(response):
    """
    允许跨域
    :param response:response
    :return: header中添加跨域支持
    """
    response.headers['Access-Control-Allow-Methods'] = '*'
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = '*'
    return response


def before_request_func():
    print('请求')


# 添加访问API
app = Flask(__name__)
# CORS(app)
app.after_request(allow_cors)

# 初始化区块链结构
blockchain = Blockchain()

# 当前所有的节点
peers = set()
self_url_host = ''


# 添加新的交易信息
@app.route('/new_transaction', methods=['GET'])
def add_new_transaction():
    new_transaction_data = request.args
    print('添加新的交易信息 : ', new_transaction_data)
    new_transaction = dict()
    for key, value in new_transaction_data.items():
        new_transaction[key] = value

    new_transaction['timestamp'] = time.time()
    blockchain.add_new_transaction(new_transaction)
    return "success", 200


# 获取区块链中的数据
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data), "chain": chain_data, "peers": list(peers)})


# 挖矿
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transaction to mine", 200
    else:
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined".format(blockchain.last_block.index)


# 获取当前未确认的交易
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)


# 在网络中注册新节点
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    """
    远端节点向本节点注册的接口，
    将本节点和远端节点加入peers，返回本节点最新的区块链数据
    """
    self_addr = request.host_url[:-1]
    node_addr = request.get_json()['node_address']

    if not self_addr:
        return "Invalid data", 400
    peers.add(self_addr)
    global self_url_host
    self_url_host = self_addr
    peers.add(node_addr)
    for peer in peers:
        if peer != self_url_host:
            requests.get('{}/add_peer'.format(peer),
                         params={'node_address': node_addr})
    return get_chain()


@app.route('/add_peer')
def remote_add_peer():
    """
    新节点的注册，将新节点加入peers
    """
    node_addr = request.args['node_address']
    peers.add(node_addr)
    return 'success', 200


@app.route('/register_with', methods=['GET'])
def register_with_existing_node():
    """
    向远端节点注册本节点，并获取区块链信息
    """
    node_address = request.args['node_address']

    if not node_address:
        return "Invalid data", 400
    data = {"node_address": request.host_url[:-1]}  # 自身URL
    global self_url_host
    self_url_host = request.host_url[:-1]
    headers = {'Content-Type': "application/json"}

    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)
    global blockchain
    global peers
    if response.status_code == 200:
        chain_dump = response.json()['chain']
        for block in create_chain_from_dump(chain_dump):
            blockchain.add_block(block, block.compute_hash())
        peers.update(response.json()['peers'])
        return "Registration successful.", 200
    else:
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    """
    从json数据中创建区块链
    :param chain_dump: json数据
    :return: 新的区块链
    """
    chain_list = list()
    for idx, block_data in enumerate(chain_dump):
        block = Block(index=block_data['index'],
                      transactions=block_data['transactions'],
                      timestamp=block_data['timestamp'],
                      previous_hash=block_data['previous_hash'],
                      nonce=block_data['nonce'])
        chain_list.append(block)
    return chain_list


def consensus():
    """
    计算当前所有节点中的最长有效链，即所有节点上链的最长公共部分
    :return: 如果有最长有效链且长度大于1返回true，否则返回false
    """
    global blockchain
    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}/chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len:
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain.chain = create_chain_from_dump(longest_chain)
        return True
    return False


@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    """
    添加新的区块
    :return: 是否添加成功
    """
    block_data = request.get_json()
    block = Block(index=block_data['index'],
                  transactions=(block_data['transactions']),
                  timestamp=block_data['timestamp'],
                  previous_hash=block_data['previous_hash'],
                  nonce=block_data['nonce'])
    proof = block.compute_hash()
    added = blockchain.add_block(block, proof)

    if not added:
        print("can't add -- ")
        return "The block was discarded by the node", 400
    return "Block added to the chain", 200


def block_to_json(block) -> dict:
    """
    区块链数据的预处理，方便转为json数据结构在网络中传输
    """
    return {
        'index': block.index,
        'transactions': block.transactions,
        'timestamp': block.timestamp,
        'previous_hash': block.previous_hash,
        'nonce': block.nonce,
    }


def announce_new_block(block):
    """
    向已注册的所有节点广播新增的区块
    """
    for peer in peers:
        if peer != self_url_host:
            url = "{}/add_block".format(peer)
            headers = {'Content-Type': "application/json"}
            requests.post(url, data=json.dumps(block_to_json(block), sort_keys=True), headers=headers)


@app.route('/get_peers')
def get_peers():
    return json.dumps(list(peers))


@app.route('/init')
def init_self_node():
    blockchain.create_genesis_block()
    return 'success', 200


@app.route('/difficulty')
def get_block_chain_difficulty():
    return str(blockchain.difficulty), 200


if __name__ == '__main__':
    app.run(debug=True, port=5000)
