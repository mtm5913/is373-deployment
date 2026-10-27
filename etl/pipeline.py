"""Public GitHub Actions -> canonical SQLite -> Neo4j deployment graph.
No credentials required for public extraction. No third-party Python dependencies.
"""
import argparse
import base64
from contextlib import closing
import json
import os
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = "mtm5913/is373-deployment"
SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS repositories (name TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS commits (
 repository TEXT NOT NULL REFERENCES repositories(name), sha TEXT NOT NULL,
 PRIMARY KEY(repository,sha));
CREATE TABLE IF NOT EXISTS environments (name TEXT PRIMARY KEY);
CREATE TABLE IF NOT EXISTS workflow_runs (
 repository TEXT NOT NULL, run_id INTEGER NOT NULL, attempt INTEGER NOT NULL,
 sha TEXT NOT NULL, branch TEXT NOT NULL, environment TEXT,
 status TEXT NOT NULL, conclusion TEXT, created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL, url TEXT NOT NULL,
 PRIMARY KEY(repository,run_id,attempt),
 FOREIGN KEY(repository,sha) REFERENCES commits(repository,sha),
 FOREIGN KEY(environment) REFERENCES environments(name));
CREATE TABLE IF NOT EXISTS imports (
 id INTEGER PRIMARY KEY, imported_at TEXT NOT NULL, source TEXT NOT NULL,
 accepted INTEGER NOT NULL, rejected INTEGER NOT NULL);
"""

def request_json(url, payload=None, headers=None):
    data = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.load(response)

def extract(repository, directory):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Expected owner/repository")
    runs = []
    # GitHub limits Actions search results to 1,000; fail rather than claim full history.
    for page in range(1, 11):
        result = request_json(
            f"https://api.github.com/repos/{repository}/actions/runs?per_page=100&page={page}",
            headers={"Accept": "application/vnd.github+json", "User-Agent": "is373-etl"})
        if result["total_count"] > 1000:
            raise ValueError("History exceeds 1,000 runs; add date-window extraction")
        batch = result["workflow_runs"]
        runs.extend(batch)
        if len(batch) < 100:
            break
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
    path.write_text(json.dumps({"workflow_runs": runs}, indent=2))
    return path

def transform(document):
    if not isinstance(document, dict) or not isinstance(document.get("workflow_runs"), list):
        raise ValueError("Expected a GitHub workflow_runs array")
    accepted, rejected = {}, []
    for index, run in enumerate(document["workflow_runs"]):
        try:
            if not isinstance(run, dict):
                raise ValueError("Run must be an object")
            repo = run["repository"]["full_name"]
            if repo != REPO:
                raise ValueError("Unexpected repository")
            sha = run["head_sha"]
            if not re.fullmatch(r"[a-f0-9]{40}", sha):
                raise ValueError("Invalid commit SHA")
            run_id, attempt = run["id"], run.get("run_attempt", 1)
            if type(run_id) is not int or type(attempt) is not int or min(run_id, attempt) < 1:
                raise ValueError("Invalid run identity")
            branch = run["head_branch"]
            if not isinstance(branch, str) or not branch:
                raise ValueError("Missing branch")
            for field in ("created_at", "updated_at"):
                timestamp = datetime.fromisoformat(run[field].replace("Z", "+00:00"))
                if timestamp.tzinfo is None:
                    raise ValueError("Timestamp requires timezone")
            if run["status"] not in ("queued", "in_progress", "completed", "waiting", "requested", "pending"):
                raise ValueError("Unknown workflow status")
            url = run["html_url"]
            if url != f"https://github.com/{repo}/actions/runs/{run_id}":
                raise ValueError("Unexpected workflow URL")
            # Only the website workflow represents an intended website environment.
            environment = ({"qa": "qa", "main": "production"}.get(branch)
                           if run.get("path") == ".github/workflows/deploy.yml" else None)
            row = dict(repository=repo, run_id=run_id, attempt=attempt, sha=sha,
                       branch=branch, environment=environment, status=run["status"],
                       conclusion=run.get("conclusion"), created_at=run["created_at"],
                       updated_at=run["updated_at"], url=url)
            key = (repo, run_id, attempt)
            if key not in accepted or row["updated_at"] > accepted[key]["updated_at"]:
                accepted[key] = row
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            rejected.append({"record": index, "reason": str(exc)})
    return list(accepted.values()), rejected

def load_sqlite(database, rows, rejected, source):
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(database)) as db, db:
        db.executescript(SCHEMA)
        for r in rows:
            db.execute("INSERT OR IGNORE INTO repositories VALUES (?)", (r["repository"],))
            db.execute("INSERT OR IGNORE INTO commits VALUES (?,?)", (r["repository"], r["sha"]))
            if r["environment"]:
                db.execute("INSERT OR IGNORE INTO environments VALUES (?)", (r["environment"],))
            db.execute("""INSERT INTO workflow_runs VALUES (
                :repository,:run_id,:attempt,:sha,:branch,:environment,:status,
                :conclusion,:created_at,:updated_at,:url)
                ON CONFLICT(repository,run_id,attempt) DO UPDATE SET
                status=excluded.status, conclusion=excluded.conclusion,
                updated_at=excluded.updated_at
                WHERE excluded.updated_at >= workflow_runs.updated_at""", r)
        db.execute("INSERT INTO imports(imported_at,source,accepted,rejected) VALUES (?,?,?,?)",
                   (datetime.now(timezone.utc).isoformat(), source, len(rows), len(rejected)))

def export_graph(database, output):
    with closing(sqlite3.connect(database)) as db, db:
        db.row_factory = sqlite3.Row
        rows = [dict(row) for row in db.execute("SELECT * FROM workflow_runs ORDER BY run_id,attempt")]
    nodes, edges = {}, {}
    def node(key, label, **properties):
        nodes[key] = dict(id=key, label=label, **properties)
    def edge(source, target, relation):
        edges[(source,target,relation)] = dict(source=source,target=target,type=relation)
    for r in rows:
        repo = "repo:" + r["repository"]
        commit = "commit:" + r["repository"] + ":" + r["sha"]
        run = f"run:{r['repository']}:{r['run_id']}:{r['attempt']}"
        node(repo,"Repository",name=r["repository"])
        node(commit,"Commit",sha=r["sha"])
        node(run,"WorkflowRun",**r)
        edge(run,repo,"BELONGS_TO"); edge(run,commit,"BUILT_FROM")
        # A green website deployment workflow includes successful HTTPS verification.
        if r["environment"] and r["status"] == "completed" and r["conclusion"] == "success":
            env = "environment:" + r["environment"]
            node(env,"Environment",name=r["environment"])
            edge(run,env,"DEPLOYED_TO")
    graph = {"nodes":list(nodes.values()), "edges":list(edges.values())}
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(graph,indent=2))
    return graph

def load_neo4j(graph, base_url, password):
    if not password:
        raise ValueError("Set NEO4J_PASSWORD to load Neo4j")
    labels = {"Repository", "Commit", "WorkflowRun", "Environment"}
    relations = {"BELONGS_TO", "BUILT_FROM", "DEPLOYED_TO"}
    statements = [{"statement":"CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE"}]
    def execute(statements):
        result = request_json(base_url.rstrip("/") + "/db/neo4j/tx/commit",
            {"statements": statements}, {"Content-Type":"application/json",
             "Authorization":"Basic " + base64.b64encode(("neo4j:"+password).encode()).decode()})
        if result.get("errors"):
            raise RuntimeError("Neo4j rejected graph transaction")
        return result
    execute(statements)
    statements = []
    for n in graph["nodes"]:
        if n["label"] not in labels: raise ValueError("Unknown node label")
        statements.append({"statement":f"MERGE (n:Entity {{id:$id}}) SET n:{n['label']} SET n += $properties",
                           "parameters":{"id":n["id"],"properties":n}})
    for e in graph["edges"]:
        if e["type"] not in relations: raise ValueError("Unknown relationship")
        statements.append({"statement":f"MATCH (s:Entity {{id:$source}}),(t:Entity {{id:$target}}) MERGE (s)-[:{e['type']}]->(t)",
                           "parameters":e})
    execute(statements)
    ids = [node["id"] for node in graph["nodes"]]
    verification = execute([
        {"statement":"MATCH (n:Entity) WHERE n.id IN $ids RETURN count(n)",
         "parameters":{"ids":ids}},
        {"statement":"MATCH (s:Entity)-[r]->(t:Entity) WHERE s.id IN $ids AND t.id IN $ids RETURN count(r)",
         "parameters":{"ids":ids}}])
    counts = [result["data"][0]["row"][0] for result in verification["results"]]
    if counts != [len(graph["nodes"]),len(graph["edges"])]:
        raise RuntimeError("Graph verification failed: entity or relationship counts differ")

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path)
    parser.add_argument("--data-dir",type=Path,default=Path("data"))
    parser.add_argument("--neo4j-url")
    args = parser.parse_args()
    source = args.input or extract(REPO,args.data_dir/"raw")
    rows, rejected = transform(json.loads(source.read_text()))
    args.data_dir.mkdir(parents=True,exist_ok=True)
    (args.data_dir/"rejections.json").write_text(json.dumps(rejected,indent=2))
    if rejected:
        raise SystemExit(f"Rejected {len(rejected)} records; database unchanged. See rejections.json")
    database = args.data_dir/"canonical.sqlite3"
    load_sqlite(database,rows,rejected,str(source))
    graph = export_graph(database,args.data_dir/"graph.json")
    if args.neo4j_url:
        load_neo4j(graph,args.neo4j_url,os.environ.get("NEO4J_PASSWORD"))
    print(json.dumps({"accepted":len(rows),"rejected":len(rejected),
                      "nodes":len(graph["nodes"]),"edges":len(graph["edges"]),
                      "neo4j_loaded":bool(args.neo4j_url)},indent=2))

if __name__ == "__main__":
    main()
