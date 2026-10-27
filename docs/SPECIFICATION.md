# IS 373 — Server & Data Pipeline Specification

Owner: Megan McNeal · Updated October 27, 2026

## Purpose
Extend the existing containerized QA/production website with documented infrastructure and a working data pipeline. This specification interprets classroom notes dated October 22; no detailed follow-up assignment was supplied. It is not an instructor-approved rubric.

## Assumptions
- “Reverse engineer” means inspect and describe the existing system before changing it.
- The specification is a static site published through GitHub Pages, separate from the Droplet website.
- “Canonical DB” means a normalized source of truth with stable identifiers, validation, and provenance. SQLite is the relational implementation for this small, single-writer project.
- GitHub Actions deployment history is the initial ETL dataset. It is real project data, public and reproducible without another paid service.
- Neo4j Community is the graph database. It models repositories, commits, workflow runs, and successful deployments to environments.
- Desktop work means ChatGPT plus the official Codex extension in VS Code. User sign-in and desktop app access permissions require interactive verification.
- Run ETL manually first. Scheduling, dashboards, additional data sources, and automated backups are future work.

## Existing system — observed October 27
The deploy account successfully accepted SSH-key authentication. The Droplet runs Ubuntu 24.04.5 LTS, approximately 2 GB RAM, and a 48 GB root disk. The deploy user belongs to the sudo and docker groups. Docker group membership provides administrative power and must remain restricted.

Traefik v3.7.13 publishes ports 80 and 443. It routes hostname-based HTTPS requests to separate Apache containers on the external hosting-web network and manages Let's Encrypt certificates. Its Docker socket mount is read-only, but Docker API access remains privileged.

Production uses the is373-production project at https://megan373lab.xyz. QA uses is373-qa at https://qa.megan373lab.xyz. Five other Apache site containers share the host. Public site checks succeeded over HTTPS on October 27. Matching current content is expected after promotion and does not imply shared containers.

The repository contains the website source, Dockerfile, deployment script, Compose configuration, tests, and GitHub Actions workflow. Pushes to qa deploy QA; pushes to main deploy production. The workflow validates HTML and configuration, builds and smoke-tests an image, pushes a commit-tagged image to GHCR, connects through verified SSH, and runs Compose on the Droplet. It compares the HTTPS response with the expected source. Failed validation/build steps prevent subsequent deployment steps.

Historical SSH evidence shows PermitRootLogin no, PasswordAuthentication no, KbdInteractiveAuthentication no, and PubkeyAuthentication yes. Current readable configuration files also contain these security settings. Effective settings need a fresh privileged sshd -T check; the deploy account requires a sudo password. No private key, credential, environment dump, or authentication token belongs in published evidence.

## Data flow
GitHub Actions API → timestamped raw JSON → validation and normalization → canonical SQLite → graph JSON → Neo4j.

Extraction reads the public repository API with pagination, a timeout, and a clear failure for histories above GitHub's 1,000-result cap. Original responses are retained before transformation. An included snapshot supports repeatable demonstrations and CI without network access.

Transformation validates repository identity, run IDs, attempt numbers, SHA format, timestamps, workflow URLs, and status. Branches qa and main map to QA and production only for the website deployment workflow. Other workflows never claim website deployments. Duplicate run attempts are reconciled by update time. Invalid records are recorded in rejections.json and stop the import before database mutation.

Loading uses SQLite foreign keys, a transaction, stable composite keys, and upserts. Repeating the same import preserves row counts. Older snapshots cannot revert newer run status. Each import records its source and counts. Graph export reads the accumulated canonical database rather than only the latest input.

## Canonical model
- repositories: name is the primary key.
- commits: repository + SHA is the composite primary key.
- environments: qa or production.
- workflow_runs: repository + GitHub run ID + attempt is the primary key; records commit, branch, intended environment, status, conclusion, timestamps, and evidence URL.
- imports: import time, source, accepted count, and rejected count.

A workflow run is an attempted deployment, not proof of one. DEPLOYED_TO relationships are created only for successful completed website deployment runs, whose workflow includes HTTPS verification. Historical workflow success is evidence of what happened then, not a guarantee of current runtime state.

## Graph model
Repository ← BELONGS_TO — WorkflowRun — BUILT_FROM → Commit
WorkflowRun — DEPLOYED_TO → Environment

Entities use stable globally unique IDs. Neo4j has a uniqueness constraint on Entity.id and parameterized MERGE operations so reloading does not duplicate nodes or relationships. Graph data is a derived projection; rebuild it from SQLite. A new schema or deletion policy requires an explicit migration.

## Isolation and security
The new ETL Compose project is independent of the existing website projects. SQLite lives in a bind-mounted data directory; Neo4j uses a named volume. Neo4j's network is internal and no database port is published. The ETL container alone has a second network for public API extraction. It runs as a non-root user with a read-only root filesystem, no Linux capabilities, and no-new-privileges.

Neo4j receives a random deployment password from a server-local ignored .env file with restricted permissions. The public repository contains no real password. Neo4j is limited to 1 GB memory with a 512 MB heap and 128 MB page cache. Given the small host, inspect available memory before starting and monitor resource use. Back up SQLite and the graph volume before any future destructive maintenance.

## Status and acceptance checks
Implemented in the prepared source: ETL, canonical schema, graph loader, repeatable sample, tests, container configuration, specification site, and GitHub Pages publishing workflow.

Verified locally: real snapshot imports 9 workflow runs with zero rejects; duplicate import leaves row count unchanged; malformed input is quarantined; older snapshots cannot regress current status; unrelated workflows do not create deployment claims.

Verified on the Droplet: two live ETL imports loaded 9 workflow runs, 19 graph nodes, and 26 relationships without duplicates. A failed run has zero deployment edges. Database ports are not published. Detailed evidence is in evidence/verification.md. The public GitHub Pages specification and successful QA, production, and ETL workflow runs have been verified. The project is open and trusted in VS Code; the official Codex sidebar is authenticated and IDE context is enabled.

Acceptance criteria:
1. Both original website URLs still serve the expected content over HTTPS.
2. A raw snapshot imports into SQLite and retains provenance; an unchanged rerun leaves run counts unchanged.
3. Neo4j contains the same canonical entities and relationships; an unchanged rerun creates no duplicates.
4. Failed workflows have no DEPLOYED_TO relationship.
5. Database ports are absent from public host port mappings.
6. The specification is reachable through a public GitHub Pages URL.
7. The official Codex sidebar is authenticated with this project open and IDE context enabled.

## Next work
Confirm the professor's intended dataset and database requirements. Complete a fresh privileged SSH-settings and firewall check. Add a scheduled refresh only after the manual pipeline is demonstrated. Add backup/restore verification, monitoring, incremental extraction, and richer graph queries as the project grows.

## Demonstration
Show QA and production; explain their promotion rule. Run ETL on the included snapshot twice and compare counts. Query successful deployments in SQLite and Neo4j, then show a failed workflow with no deployment relationship. Open the specification site and the project in VS Code. See RUNBOOK.md for commands and evidence instructions.

## References
- GitHub Pages: https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages
- GitHub Actions workflow API: https://docs.github.com/en/rest/actions/workflow-runs
- Neo4j Docker: https://neo4j.com/docs/operations-manual/current/docker/introduction/
- Official Codex IDE guide: https://learn.chatgpt.com/docs/codex/ide
