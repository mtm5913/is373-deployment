# Runbook

## Local demo
From the repository root, run:

```sh
python3 -m unittest discover -s tests -v
python3 -m etl.pipeline --input data/raw/workflow-runs.json
python3 -m etl.pipeline --input data/raw/workflow-runs.json
sqlite3 data/canonical.sqlite3 'SELECT environment,conclusion,count(*) FROM workflow_runs GROUP BY environment,conclusion;'
```

Omit `--input` to extract current public GitHub history. If Python on macOS reports a certificate verification error, run the Python distribution's Install Certificates.command or use the provided Docker container. Never disable TLS verification.

## Server inventory
Connect as deploy using the existing SSH key, then run `bash scripts/inventory.sh`. Sudo prompts must be handled privately. Review output before committing it. The inventory intentionally avoids private keys, environment values, tokens, and container environment dumps.

## Deploy the isolated ETL project
Use a separate directory, such as ~/is373-data-platform, rather than the existing website checkout. Check `free -m` and `docker stats --no-stream` first; the host needs capacity for an additional database. Install no new public firewall rules.

Place the repository source in that directory. Generate a random password into a server-local `.env` with mode 600; never commit it. The file must define NEO4J_PASSWORD. Create `data` owned by the deployment user. Set ETL_UID and ETL_GID in the server-local .env to that user’s numeric UID and GID; the default container UID is 10001. Do not make the directory publicly writable.

```sh
docker compose -p is373-data -f compose.etl.yaml up -d --wait neo4j
docker compose -p is373-data -f compose.etl.yaml run --rm etl
docker compose -p is373-data -f compose.etl.yaml run --rm etl
```

These are manual ETL runs, not a scheduled refresh. `.env` is consumed by Compose, and the runtime database password is never part of the image or public specification. Neo4j has no published ports.

## SQL questions
```sql
SELECT environment, conclusion, COUNT(*) AS runs
FROM workflow_runs GROUP BY environment, conclusion;
SELECT run_id, sha, url FROM workflow_runs
WHERE environment='production' AND conclusion='success';
SELECT * FROM imports ORDER BY id DESC;
```

## Graph questions
Run in Neo4j's cypher-shell inside the database container; supply the password interactively, never as a shared screenshot or public command argument:

```sh
docker compose -p is373-data -f compose.etl.yaml exec neo4j cypher-shell -u neo4j
```

```cypher
MATCH (r:WorkflowRun)-[:DEPLOYED_TO]->(e:Environment)
RETURN e.name, r.sha, r.url;
MATCH (r:WorkflowRun {conclusion:'failure'})
RETURN r.run_id, COUNT { (r)-[:DEPLOYED_TO]->() } AS deployment_edges;
MATCH (n:Entity) RETURN labels(n), count(n);
MATCH ()-[r]->() RETURN type(r), count(r);
```

## Publish the specification to GitHub Pages
Merge the prepared branch into main through GitHub after reviewing changes. In repository Settings → Pages, choose GitHub Actions as the source. The `Publish specification` workflow uploads only `docs/`; it never uploads the database, .env, SSH material, or raw server files. Confirm the URL reported by the successful workflow. Expected URL: https://mtm5913.github.io/is373-deployment/ (not live until verified).

## IDE setup
ChatGPT desktop is already installed. The official openai.chatgpt extension is installed in the Mac's VS Code extension directory. This project is now open in VS Code, its folder is trusted with user approval, and the Codex sidebar is authenticated with IDE context enabled. For a new Mac or account, open the Codex panel and complete Sign in with ChatGPT interactively. If using ChatGPT desktop's editor integration, approve the requested editor access in the app and macOS settings. Capture a signed-in editor screenshot only after it works. See https://learn.chatgpt.com/docs/codex/ide.

## Recovery and backups
Stop only the ETL project with `docker compose -p is373-data -f compose.etl.yaml stop`; this does not stop website projects. Keep the named graph-data volume. Do not run `down -v` on production. Use SQLite's backup API for a consistent live backup, and a supported Neo4j dump procedure while stopped. Backup and restore have not yet been implemented or demonstrated. If a graph load fails, the SQLite import remains committed; correct the issue and rerun to reconcile the projection.
