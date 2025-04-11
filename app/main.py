from uuid import uuid4

import uvicorn
from fastapi import FastAPI

from models import Blockchain
from schemas import Nodes, Transaction

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
