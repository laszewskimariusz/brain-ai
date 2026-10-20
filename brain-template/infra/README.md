# infra/

What runs where. One file per host or service, or a single `infra.yaml` for a small setup.

Record: role, address or DNS name, ports, what runs on it, who owns it, backup and restore steps, and the
**name** of every secret it needs (`DB_PASSWORD`, `DEPLOY_TOKEN`) — never the value. Values live in a secret
manager and are read into a variable at runtime.

Runbooks follow GOAL / STEPS / VERIFY / ROLLBACK.
