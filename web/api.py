from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from angora.message import Message
from angora import EXCHANGE, USER, PASSWORD, HOST, PORT

app = FastAPI(version="0.0.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.get("/send", tags=["angora"])
def send(message, params=None):
    """
    Send a message to Angora
    """
    msg = Message(EXCHANGE, "initialize", message, data=params)

    try:
        msg.send(USER, PASSWORD, HOST, PORT, "initialize")
    except AttributeError:
        status = "error"
    else:
        status = "ok"

    return {"status": status, "message": message}
