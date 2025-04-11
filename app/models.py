import hashlib
import json
from time import time
from urllib.parse import urlparse

import requests


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
