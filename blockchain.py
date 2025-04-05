from fastapi import FastAPI, requests
import hashlib
import uvicorn
import json
from uuid import uuid4
from time import time


class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        self.new_block(previous_hash=1, proof=100)

    def new_block(self, proof, previous_hash=None):
        """Create a new Block in the Blockchain

        Args:
            proof (int): The proof given by the Proof of Work algorithm
            previous_hash (str): (Optional) Hash of previous Block

        Returns:
            dict: New Block
        """
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time(),
            "transactions": self.current_transactions,
            "proof": proof,
            "previous_hash": previous_hash or self.hash(self.chain[-1]),
        }

        self.current_transactions = []

        self.chain.append(block)

        return block

    def new_transactions(self, sender, recipient, amount):
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

        return self.last_block["index"] + 1

    @staticmethod
    def hash(block):
        """Create a SHA-256 hash of a Block

        Args:
            block (dict): Block

        Returns:
            str
        """
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

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


@app.get("/mine")
async def mine():
    return "We'll mine a new Block"


@app.post("/transaction/new")
async def new_transactions():
    return "We'll add a new transaction"


@app.get("/chain", status_code=200)
async def full_chain():
    return {"chain": blockchain.chain, "length": len(blockchain.chain)}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
