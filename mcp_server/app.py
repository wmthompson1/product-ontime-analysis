from fastapi import FastAPI, Request
import os

app = FastAPI(title="MCP Server - product-ontime-analysis")

SPACE_NAME = os.getenv("SPACE_NAME", "wmthompson1_sql")


@app.get("/")
async def root():
    return {"status": "ok", "space": SPACE_NAME}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/mcp/handshake")
async def handshake(request: Request):
    payload = await request.json()
    # Echo back payload to demonstrate a simple MCP handshake endpoint
    return {"received": payload, "status": "accepted", "space": SPACE_NAME}
