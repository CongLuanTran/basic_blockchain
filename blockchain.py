from fastapi import FastAPI
from urllib.parse import urlparse
from pydantic import BaseModel
import hashlib
import uvicorn
import json
import requests
from uuid import uuid4
from time import time


class Transaction(BaseModel):
    sender: str
    recipient: str
    amount: int


class Nodes(BaseModel):
    nodes: list[str]


class Block:
    def __init__(self, index, timestamp, transactions, proof, previous_hash):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.proof = proof

    def hash(self):
        """Create a SHA-256 hash of this block

        Returns:
            str: hash of this block
        """
        block_string = json.dumps(
            {
                "index": self.index,
                "timestamp": self.timestamp,
                "transactions": self.transactions,
                "proof": self.proof,
                "previous_hash": self.previous_hash,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha256(block_string).hexdigest()


class Blockchain(object):
    def __init__(self):
        self.nodes = set()
        self.chain: list[Block] = []
        self.current_transactions = []

        self.new_block(previous_hash=1, proof=100)

    def register_node(self, address):
        """Add a new node to the list of nodes

        Args:
            address (str): Address of node. E.g. 'http://192.168.0.5:5000'
        """
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain: list[Block]):
        """Determine if a given block chain is valid

        Args:
            chain (list): A blockchain

        Returns:
            bool: True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print(f"{last_block}")
            print(f"{block}")
            print("\n------------\n")

            # Check that the hash of the block is correct
            if block.previous_hash != last_block.hash():
                return False

            # Check that Proof of Work is correct
            if not self.valid_proof(last_block.proof, block.proof):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        # Look for the longest chain amongst all chains in our network
        max_length = len(self.chain)
        for node in neighbours:
            response = requests.get(f"http://{node}/chain")

            if response.status_code == 200:
                length = response.json()["length"]
                chain = response.json()["chain"]

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we find a longer chain
        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_block(self, proof, previous_hash=None):
        """Create a new Block in the Blockchain

        Args:
            proof (int): The proof given by the Proof of Work algorithm
            previous_hash (str): (Optional) Hash of previous Block

        Returns:
            dict: New Block
        """
        block = Block(
            len(self.chain) + 1,
            time(),
            self.current_transactions,
            proof,
            previous_hash or self.last_block.hash(),
        )

        self.current_transactions = []

        self.chain.append(block)

        return block

    def new_transaction(self, sender, recipient, amount):
        """Create a new transaction to go into the next mined Block

        Args:
            sender (str): Address of the Sender
            recipient (str): Address of the Recipient
            amount (int): Amount

        Returns:
            int: The index of the Block that will hold this transaction
        """
        self.current_transactions.append(
            {
                "sender": sender,
                "recipient": recipient,
                "amount": amount,
            }
        )

        return self.last_block.index + 1

    @property
    def last_block(self):
        return self.chain[-1]

    def proof_of_work(self, last_proof):
        """Simple Proof of Work Algorithm
        - Find a number p' such that hash(pp') contains 4 leading zeroes where p is the previous p'
        - p is the previous proof, and p' is the new proof

        Args:
            last_proof (int): Last Proof

        Returns:
            int
        """
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """Validate the Proof: Does hash(last_proof, proof) contain 4 leading zeroes?

        Args:
            last_proof (int): Previous Proof
            proof (int): Current Proof

        Returns:
            bool: True if correct, False if not
        """
        guess = f"{last_proof}{proof}".encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


# Instantiate our Node
app = FastAPI()


# Generate a globally unique address for this node
node_indentifier = str(uuid4()).replace("-", " ")

# Instantiate the Blockchain
blockchain = Blockchain()


@app.get("/mine", status_code=200)
async def mine():
    # Use proof of work algorithm to get the next proof
    last_block = blockchain.last_block
    last_proof = last_block.proof
    proof = blockchain.proof_of_work(last_proof)

    # Reward the miner 1 coin for finding the new proof
    # Sender is set to "0" to signify that this coin is mined
    blockchain.new_transaction(sender="0", recipient=node_indentifier, amount=1)

    # Forge a new Block with the with the mined coin to the chain
    previous_hash = last_block.hash()
    block = blockchain.new_block(proof, previous_hash)

    return {
        "message": "New Block Forged",
        "index": block.index,
        "transactions": block.transactions,
        "proof": block.proof,
        "previous_hash": block.previous_hash,
    }


# Using pydantic Model, the required fields are automatically checked
@app.post("/transaction/new", status_code=201)
async def new_transactions(transaction: Transaction):
    # Create a new Transaction
    index = blockchain.new_transaction(
        transaction.sender, transaction.recipient, transaction.amount
    )
    return {"message": f"Transaction will be added to {index}"}


@app.get("/chain", status_code=200)
async def full_chain():
    return {"chain": blockchain.chain, "length": len(blockchain.chain)}


@app.post("/node/register", status_code=201)
def register_nodes(nodes: Nodes):
    for node in nodes.nodes:
        blockchain.register_node(node)

    return {
        "message": "New nodes have been added",
        "total_nodes": list(blockchain.nodes),
    }


@app.get("/node/resolve", status_code=200)
def consensus():
    replaced = blockchain.resolve_conflicts()
    if replaced:
        response = {"message": "Our chain was replaced", "new_chain": blockchain.chain}
    else:
        response = {"message": "Our chain is authoritative", "chain": blockchain.chain}
    return response


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
