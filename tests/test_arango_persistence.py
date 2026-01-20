import os
import subprocess
import time


def test_persist_graph_against_service():
    # Assumes GitHub Actions service 'arangodb' is available at localhost:8529
    os.environ.setdefault("DATABASE_HOST", "http://localhost:8529")
    os.environ.setdefault("DATABASE_USERNAME", "root")
    os.environ.setdefault("DATABASE_PASSWORD", "rootpass")
    os.environ.setdefault("DATABASE_NAME", "ci_networkx_graphs")

    # Run the persistence script
    proc = subprocess.run(["python", "026_Entry_Point_NCM_Elevation_ArangoDB.py"], capture_output=True, text=True)
    print(proc.stdout)
    assert proc.returncode == 0
    assert "✅ Graph 'manufacturing_semantic_layer' persisted successfully" in proc.stdout
