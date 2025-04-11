from pydantic import BaseModel


class Transaction(BaseModel):
    sender: str
    recipient: str
    amount: int


class Nodes(BaseModel):
    nodes: list[str]
