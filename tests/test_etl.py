import copy
from contextlib import closing
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from etl.pipeline import transform, load_sqlite, export_graph

class ETLTest(unittest.TestCase):
    def setUp(self):
        self.runs = json.loads(Path("data/raw/workflow-runs.json").read_text())

    def test_real_snapshot_and_idempotent_load(self):
        rows, rejected = transform(self.runs)
        self.assertTrue(rows)
        self.assertEqual(rejected, [])
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/"canonical.sqlite3"
            load_sqlite(db,rows,[],"fixture")
            load_sqlite(db,rows,[],"fixture")
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(conn.execute("SELECT count(*) FROM workflow_runs").fetchone()[0],len(rows))
                self.assertEqual(conn.execute("PRAGMA foreign_key_check").fetchall(),[])
            graph = export_graph(db,Path(folder)/"graph.json")
            ids = {n["id"] for n in graph["nodes"]}
            for e in graph["edges"]:
                self.assertIn(e["source"],ids)
                self.assertIn(e["target"],ids)
            successful = {n["id"] for n in graph["nodes"] if n["label"] == "WorkflowRun"
                          and n["status"] == "completed" and n["conclusion"] == "success" and n["environment"]}
            self.assertEqual({e["source"] for e in graph["edges"] if e["type"]=="DEPLOYED_TO"},successful)

    def test_bad_records_are_quarantined(self):
        snapshot = copy.deepcopy(self.runs)
        snapshot["workflow_runs"][0]["head_sha"] = "invalid"
        _, rejected = transform(snapshot)
        self.assertEqual(len(rejected),1)

    def test_other_workflows_never_claim_website_deployment(self):
        snapshot = copy.deepcopy(self.runs)
        snapshot["workflow_runs"][0]["path"] = ".github/workflows/pages.yml"
        rows, _ = transform(snapshot)
        first = snapshot["workflow_runs"][0]
        self.assertIsNone(next(r for r in rows if r["run_id"] == first["id"])["environment"])

    def test_old_snapshot_cannot_revert_new_status(self):
        row = transform(self.runs)[0][0]
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/"db.sqlite3"
            newer = dict(row,status="completed",conclusion="success",updated_at="2026-10-27T14:00:00Z")
            older = dict(row,status="queued",conclusion=None,updated_at="2026-10-01T14:00:00Z")
            load_sqlite(db,[newer],[],"new")
            load_sqlite(db,[older],[],"old")
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(conn.execute("SELECT status FROM workflow_runs").fetchone()[0],"completed")
