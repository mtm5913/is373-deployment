# Verification — October 27, 2026

## Current live server
Authenticated through the existing SSH key as the non-root deploy account. Ubuntu 24.04.5 LTS; Docker 29.8.2; Compose 5.6.0. Approximately 2 GB RAM and 48 GB disk. Existing QA, production, five additional Apache site containers, and Traefik were inventoried without stopping them.

## ETL deployed and repeated
The isolated is373-data Compose project runs Neo4j Community with no public database ports. The ETL container extracted current public GitHub history, validated it, loaded canonical SQLite, and loaded Neo4j. Two consecutive live imports completed successfully:

```json
{
  "accepted": 9,
  "rejected": 0,
  "nodes": 19,
  "edges": 26,
  "neo4j_loaded": true
}
```

Independent Cypher queries after the second import returned:

```text
nodes, edges
19, 26
failed_run, deployment_edges
37821274704, 0
```

Database containers expose internal container ports only; no host bindings were configured. Traefik retains the existing public 80/443 bindings. After deployment the host reported approximately 743 MB available RAM. Monitor resource use before adding further services.

## Security checks
Root SSH login with the existing key was rejected: `Permission denied (publickey)`.
A password-only attempt with public-key authentication disabled was rejected: `Permission denied (publickey)`.

Current readable SSH configuration includes disabling root and password authentication. A fresh privileged `sshd -T` check and firewall status require interactive sudo and remain pending. Historical effective-settings screenshots remain in the README. No credentials are included here.

## Automated verification
Five local unit tests pass: website validation, real snapshot import with idempotent reload and foreign-key integrity, invalid-record rejection, unrelated-workflow environment isolation, and stale-snapshot protection. A real local Neo4j load and repeat returned the same 19 nodes and 26 relationships. The dedicated ETL CI workflow also performs two real graph loads and checks counts.

## Publication and desktop
The specification and Pages workflow are prepared. Record the successful public Pages URL and GitHub CI links after publication. ChatGPT desktop is installed, and the official openai.chatgpt VS Code extension is installed. User sign-in and an actual editor interaction still need interactive verification.
