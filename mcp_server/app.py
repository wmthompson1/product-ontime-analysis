from fastapi import FastAPI, Request, HTTPException
import os
from typing import Dict, Any
import pathlib

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

@app.post("/mcp/resource")
async def resource(request: Request):
    """Accepts a resource JSON and, for repo-path resources, returns a manifest of files.

    Expected payload example:
    {
      "resource": {
        "type": "git:repo_path",
        "path": "schemas/my_schema_folder"
      }
    }
    """
    payload: Dict[str, Any] = await request.json()
    resource = payload.get("resource") or {}
    rtype = resource.get("type")
    rpath = resource.get("path")

    if rtype != "git:repo_path":
        raise HTTPException(status_code=400, detail="Only resource.type 'git:repo_path' is supported by this endpoint")

    if not rpath:
        raise HTTPException(status_code=400, detail="resource.path is required")

    # Resolve the path relative to the repository workspace root
    repo_root = pathlib.Path.cwd()
    target = (repo_root / rpath).resolve()

    # Security: ensure the resolved path is contained in the repository
    try:
        target.relative_to(repo_root.resolve())
    except Exception:
        raise HTTPException(status_code=400, detail="resource.path must be inside the repository workspace")

    if not target.exists():
        raise HTTPException(status_code=404, detail=f"Path not found: {rpath}")

    if target.is_file():
        # return single file info
        with open(target, "r", encoding="utf-8") as fh:
            content = fh.read()
        return {"type": "file", "path": rpath, "size": len(content), "sample": content[:200]}

    # target is a directory: list schema files (common extensions)
    entries = []
    for p in sorted(target.iterdir()):
        if p.is_file():
            try:
                size = p.stat().st_size
            except Exception:
                size = None
            entries.append({"name": p.name, "path": str((pathlib.Path(rpath) / p.name)), "size": size})

    return {"type": "directory", "path": rpath, "count": len(entries), "entries": entries}
