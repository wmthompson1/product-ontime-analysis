# Arango_research_001 — Local ArangoDB startup troubleshooting

Status: in-progress

## Purpose

Document diagnosis steps and findings for why local ArangoDB (http://localhost:8529)
is not reachable from the dev container. Capture commands, logs, and recommended fixes
so we can persist graphs (Entry Point 020) from this Codespaces environment.

## Context / Observed behavior

- `scripts/persist_to_arango.py` attempted to POST to `http://localhost:8529` and
  received `Connection refused` (TCP errno 111).
- A TCP check to `localhost:8529` returned connection refused.
- Previous Docker attempts in this environment failed due to daemon/network issues
  (iptables/nftables / insufficient capabilities) in the dev container.

## Goals

- Reproduce the connectivity failure and capture root cause.
- Provide actionable remediation: start Arango locally (docker/system), or use
  an alternate reachable Arango instance (cloud or remote VM).
- Document commands for team members to start Arango and validate connectivity.

## Quick diagnostic checklist

1. Verify Arango process is listening (host machine):

   - `ss -ltnp | grep 8529` or `netstat -ltnp | grep 8529`

2. From the dev container / Codespace, test TCP reachability:

   - `python -c "import socket; s=socket.socket(); s.settimeout(3); s.connect(('localhost',8529)); print('ok')"`

3. Try HTTP probe to Arango server (admin endpoint):

   - `curl -sS http://localhost:8529/_admin/version`

4. If using Docker, verify container is running and port is published:

   - `docker ps --filter ancestor=arangodb --format '{{.ID}} {{.Ports}}'`
   - Example run command (dev):

     ```bash
     docker run --name arangodb-local -e ARANGO_LICENSE_KEY=server -e ARANGO_ROOT_PASSWORD=passwd -p 8529:8529 -d arangodb
     ```

   - Note: in restricted dev containers (Codespaces, Replit) Docker may not be available
     or the daemon may fail to start due to kernel/net namespace restrictions.

5. Check local firewall / host binding issues (iptables/nftables):

   - `sudo iptables -L -n` or `sudo nft list ruleset`
   - Confirm port 8529 not blocked.

6. If Docker cannot be used due to permissions, options:

   - Run Arango on a remote host/VM and set `DATABASE_HOST` to that URL.
   - Use ArangoDB Cloud (managed) and provide credentials.
   - Use the export GraphML (`data/schema_018.graphml`) and persist from a machine that can reach Arango.

## Common causes in Codespaces / constrained containers

- Docker daemon not running or fails to initialize network (requires CAP_NET_ADMIN).
- Host binding to 127.0.0.1 vs 0.0.0.0 — container may bind to host but Codespaces network isolates ports.
- Local firewall or corporate VPN blocking port 8529.
- Arango service crashed on startup; check `docker logs` or systemd journal.

## Recommended remediation steps (priority order)

1. If you can run Docker locally (outside Codespace), start Arango with `-p 8529:8529` and verify `curl http://localhost:8529/_admin/version` from your host.
2. If Docker in Codespace fails, run Arango on a reachable VM or ArangoDB Cloud and update `.env` (`DATABASE_HOST`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_NAME`).
3. For quick testing, persist graph from your host machine where Arango is running (copy `data/schema_018.graphml`).
4. If you want us to attempt more debugging here, provide permission to start system services or share `docker logs` output from your environment.

## Commands to run (copyable)

```bash
# On host: verify Arango is running
curl -sS http://localhost:8529/_admin/version

# From Codespace / container: test TCP
python - <<PY
import socket
try:
    s=socket.socket(); s.settimeout(2); s.connect(('localhost',8529)); print('TCP ok')
except Exception as e:
    print('TCP failed:', e)
finally:
    s.close()
PY

# Docker run (host):
docker run --name arangodb-local -e ARANGO_ROOT_PASSWORD=passwd -p 8529:8529 -d arangodb

# If Docker logs needed:
docker logs arangodb-local --tail 200
```

## Next actions for me

- Attempt the above TCP/HTTP checks here in the Codespace and capture outputs.
- If Docker is available, try `docker run` and report logs and connectivity.
- Or, persist `data/schema_018.graphml` from here to a remote Arango if you provide reachable credentials.

## References

- ArangoDB HTTP admin API: `/_admin/version`
- nx-arangodb docs: https://github.com/arangoml/nx-arangodb
