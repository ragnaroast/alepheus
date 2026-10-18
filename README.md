# ChokePoint 🛡️
### CI/CD Attack-Path Analysis Agent & Minimum-Cut Remediation Engine

[![FalkorDB](https://img.shields.io/badge/FalkorDB-Graph_Database-red.svg)](https://falkordb.com/)
[![LLM](https://img.shields.io/badge/LLM-Google_Gemini_2.5_Flash_(Free)-blue.svg)](https://aistudio.google.com/)
[![MCP](https://img.shields.io/badge/MCP-FastMCP_2.0-green.svg)](https://modelcontextprotocol.io/)
[![Python](https://img.shields.io/badge/Python-3.10+-yellow.svg)](https://www.python.org/)
[![React](https://img.shields.io/badge/Frontend-React_18_+_TypeScript-cyan.svg)](https://react.dev/)

---

## 1. Executive Summary & Problem

Modern CI/CD pipelines represent the highest-privilege attack surface in software engineering. In a GitHub Actions workflow, untrusted input from external contributors (fork pull requests, issue comments, third-party actions) directly converges with your organization's crown-jewel capabilities (production cloud roles, publish tokens, deployment keys).

Classic supply-chain compromises are **multi-hop attack chains spanning steps, jobs, and workflows**, not isolated syntax errors:
* **The "Pwn-Request" Chain**: A `pull_request_target` trigger checks out an untrusted branch, allowing malicious code to execute within a privileged environment holding deploy secrets.
* **The Script Injection Chain**: An attacker inserts shell escape characters into `${{ github.event.issue.title }}` inside an inline `run:` step, which executes in a job holding `AWS_ROLE_ARN`.
* **The Compromised Action Vector** (*tj-actions incident*): An unpinned or mutable tag on a widely used third-party action is compromised, immediately exfiltrating all environment secrets of every job that invokes it.

### Why Traditional Scanners Fail (The Alert Fatigue Trap)
Per-file static linters (*zizmor*, *poutine*, *actionlint*) evaluate files and AST nodes in isolation. A single scan on complex repositories can produce **over 3,500 flat alerts across 160+ workflows**. 

A flat alert list cannot tell you:
1. **Reachability**: Which alerts actually connect to high-value crown jewels vs which are benign dead-ends.
2. **Minimum Cut (Min-Cut)**: What the *fewest, cheapest changes* are that completely sever all attack chains.
3. **Verification**: Whether a suggested fix actually breaks the path without introducing regressions.
4. **Supply-Chain Blast Radius**: If action $X$ is compromised upstream, exactly which secrets and pipelines are impacted.

ChokePoint models the pipeline as a graph in **FalkorDB**, computes the **minimum cut** using graph flow algorithms (`algo.maxFlow`), generates verified comment-preserving YAML patches (`ruamel.yaml`), and provides an autonomous agent with a real-time investigation stream.

---

## 2. Key Capabilities

| Capability | How It Works | Benefit |
|---|---|---|
| **Attack Chains** | Variable-depth graph traversal (`FLOWS*1..8`) linking untrusted inputs to crown-jewel capabilities. | Every hop is cited with exact YAML file paths, step names, and line numbers. |
| **Minimum Fix Set (Min-Cut)** | Subgraph max-flow min-cut algorithm (`algo.maxFlow` with fix-capacity costs and residual BFS). | Solves the *fewest targeted fixes* needed (e.g. 2 targeted fixes eliminate 24 flat alerts). |
| **Verified YAML Patches** | Comment-preserving YAML rewriting (`ruamel.yaml`) verified in isolated `whatif:*` graphs (`GRAPH.COPY`). | Proves attack chains go from $N \to 0$ before touching the codebase. |
| **Incident Mode** | Upstream supply-chain blast radius query on third-party actions. | Generates an immediate list of exposed workflows and an urgent secret rotation checklist. |
| **PR Gate** | Graph diffing between base and head commit snapshots (`cp:<tenant>:<sha>`). | Blocks pull requests that introduce new attack paths to secrets. |
| **Corpus Insights** | Aggregated graph analytics over 250+ scanned repositories. | Identifies systemic ecosystem choke points with privacy preservation (no repo naming). |

---

## 3. Architecture

```
GitHub Repositories / Workflow Files
              │
              ▼
   Parser & Flow Derivation Engine
   (AST extraction + Untrusted Catalog + FLOWS edges)
              │
              ▼ Batched UNWIND MERGE
   ┌────────────────────────────────────────────────────────┐
   │ FalkorDB Engine (cp:<tenant>:<sha>)                    │
   │  - Structural Layer: Workflow, Job, Step, Action, Secret│
   │  - Flow Layer: FLOWS edges with fix_cost capacities    │
   │  - Graph Algorithms: algo.maxFlow, algo.SPpaths        │
   └────────────────────────────────────────────────────────┘
         ▲                                   │ GRAPH.COPY
         │ Guarded RO Cypher                 ▼
   FastMCP Server              whatif:* Simulation Graphs
   (Streamable HTTP + SSE)                   ▲
         │                                   │ Re-ingest
   Hand-Rolled Agent Loop ──────► ruamel.yaml Patch Engine
   (Google Gemini 2.5 Flash)
         │
   FastAPI Server (REST + SSE Trace) ────► React + Vite Console (Port 5173)
                                    ────► CLI / Composite Action Gate
```

---

## 4. FalkorDB Graph Schema

### Structural Layer
* **Nodes**: `Repo`, `Workflow`, `Trigger`, `Job`, `Step`, `Action`, `Secret`, `Environment`, `Permission`, `Artifact`, `Cache`.
* **Relationships**: `TRIGGERS`, `HAS_JOB`, `NEEDS`, `HAS_STEP`, `USES`, `HOLDS`, `GRANTS`.

### Flow Layer (`FLOWS`)
Derived dynamically at ingest connecting `Input`, `Step`, `Job`, `Secret`, and `Capability` nodes:
* `kind`: `inject`, `exec`, `expose`, `poison`, `consume`, `grant`, `inherit`.
* `difficulty`: Integer score representing exploit complexity.
* `fix_cost`: Integer representing remediation cost (used as capacity in `algo.maxFlow`).
* `fixable`: Boolean indicating if the edge can be remediated.
* `fix_kind`: `pin`, `env_var`, `permission`, `trigger`.
* `evidence_file`: File path where the step exists.
* `evidence_line`: Line number in the YAML workflow file.

---

## 5. Setup Guide & API Keys

### Step 1: Clone and Configure Environment
Copy the environment template to `.env`:

```bash
# Linux / macOS:
cp .env.example .env

# Windows (PowerShell):
Copy-Item .env.example .env

# Windows (CMD):
copy .env.example .env
```

Open `.env` in any editor:
```env
# --- 1. Google Gemini API Key (Required for Agent & AI Features) ---
# Free Tier: 15 Requests/Min, 1,500 Requests/Day (No credit card needed)
# Obtain your key in 30 seconds at: https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# --- 2. GitHub Token (Optional for local files, needed for remote repo scans) ---
# Create a Personal Access Token (Classic) with `public_repo` scope at:
# https://github.com/settings/tokens
GITHUB_TOKEN=your_github_token_here

# --- 3. FalkorDB Connection ---
FALKORDB_HOST=localhost
FALKORDB_PORT=6379

# --- 4. Service Ports ---
API_PORT=8000
MCP_PORT=8001
```

#### Where to get API Keys:
1. **Google Gemini API Key (100% Free)**:
   * Visit [Google AI Studio](https://aistudio.google.com/apikey).
   * Sign in with any Google account.
   * Click **"Create API Key"** and copy the string into `GEMINI_API_KEY` in `.env`.
   * *Note: Google Gemini 2.5 Flash is natively supported with zero API costs.*
2. **GitHub Personal Access Token (Free, Optional)**:
   * Visit [GitHub Token Settings](https://github.com/settings/tokens).
   * Click **"Generate new token (classic)"**.
   * Give it a name (e.g. `chokepoint-scanner`) and select the `public_repo` scope.
   * Copy the token into `GITHUB_TOKEN` in `.env`.

---

## 6. One-Click Quickstart

We provide one-click start scripts that automatically spin up FalkorDB via Docker, configure Python dependencies, and launch all backend, MCP, and frontend services simultaneously:

### Windows (PowerShell):
```powershell
.\start-all.ps1
```

### Windows (CMD):
```cmd
start-all.bat
```

### Linux / macOS (Bash):
```bash
chmod +x start-all.sh
./start-all.sh
```

### Active Service Endpoints:
| Service | URL | Description |
|---|---|---|
| **Web Console** | [http://localhost:5173](http://localhost:5173) | Interactive cybersecurity dashboard |
| **FastAPI REST & SSE** | [http://localhost:8000/docs](http://localhost:8000/docs) | Interactive Swagger API documentation |
| **FastMCP Server** | [http://localhost:8001](http://localhost:8001) | Streamable HTTP MCP server for AI IDEs |
| **FalkorDB Browser** | [http://localhost:3000](http://localhost:3000) | Native FalkorDB visual graph explorer |

---

## 7. CLI Reference Guide

You can run ChokePoint directly from the command line on any workflow file or repository:

```bash
# Set PYTHONPATH
export PYTHONPATH="$PWD/backend/src:$PYTHONPATH"  # Linux/macOS
$env:PYTHONPATH="$PWD\backend\src"                # Windows PowerShell

# 1. Scan a workflow or directory for attack chains
python -m chokepoint.cli scan examples/workflows/vulnerable-deploy.yml

# 2. Output SARIF 2.1.0 format for GitHub Code Scanning
python -m chokepoint.cli scan examples/workflows/ --sarif -o report.sarif

# 3. Compute the Minimum Fix Set (Min-Cut)
python -m chokepoint.cli cut examples/workflows/vulnerable-deploy.yml

# 4. Generate comment-preserving YAML patches (unified diff)
python -m chokepoint.cli patch examples/workflows/vulnerable-deploy.yml

# 5. Apply the verified patch directly to the file
python -m chokepoint.cli patch examples/workflows/vulnerable-deploy.yml --apply

# 6. Incident Mode: Analyze blast radius of compromised action (e.g. tj-actions)
python -m chokepoint.cli incident tj-actions/changed-files

# 7. Run evaluation benchmark against traditional flat linters
python -m chokepoint.cli eval

# 8. Run ecosystem corpus analysis across 250 repositories
python -m chokepoint.cli corpus
```

---

## 8. Quantitative Benchmark (Eval Harness)

Run `python -m chokepoint.cli eval` to execute the benchmark harness comparing ChokePoint's graph-aware min-cut against flat linters on planted vulnerable fixtures:

```
==========================================================================================
                   CHOKEPOINT vs FLAT LINTER BENCHMARK EVALUATION                        
==========================================================================================
Repository Fixture           | Planted  | Flat Alerts  | Min-Cut Fixes  | Fix Reduction 
-----------------------------+----------+---------------+----------------+----------------
org/issue-automation-app     | 2        | 7             | 1              |       85.7%
org/tj-actions-pipeline      | 1        | 4             | 1              |       75.0%
org/artifact-poison-app      | 1        | 6             | 1              |       83.3%
org/monorepo-enterprise      | 3        | 8             | 2              |       75.0%
-----------------------------+----------+---------------+----------------+----------------
OVERALL AGGREGATE            | -        | 25            | 5              |       80.0%
==========================================================================================
```

**Key Takeaway**: ChokePoint achieves an **80.0% reduction in developer remediation burden** by identifying high-leverage choke points rather than requiring developers to fix every unpinned action or shell string across the enterprise.

---

## 9. Model Context Protocol (MCP) Integration

ChokePoint includes a dedicated **FastMCP server** implementing the official Model Context Protocol with Streamable HTTP transport on port `8001`.

To integrate ChokePoint into **Claude Desktop**, **Cursor**, or other AI agents, add the following to your MCP configuration:

```json
{
  "mcpServers": {
    "chokepoint": {
      "url": "http://localhost:8001/sse"
    }
  }
}
```

Exposed MCP tools:
* `list_chains`: Enumerate attack paths to crown jewels.
* `explain_chain`: Get hop-by-hop evidence and line numbers.
* `min_fix_set`: Compute the minimum cut that severs all chains.
* `blast_radius`: Incident mode for upstream compromised actions.
* `diff_snapshots`: PR gate comparison across commit snapshots.
* `search_advisories`: Query known CI/CD vulnerability patterns.
* `run_cypher_ro`: Guarded read-only Cypher query execution.

---

## 10. Composite GitHub Action Gate

To run ChokePoint automatically on every pull request, add `.github/workflows/chokepoint-gate.yml` to your repo:

```yaml
name: ChokePoint Attack-Path Gate
on:
  pull_request:
    branches: [main]

jobs:
  security-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run ChokePoint Gate
        uses: ./action
        with:
          workflow_path: ".github/workflows"
          fail_on_chains: "true"
          sarif_file: "chokepoint-results.sarif"
```

The action will fail the pull request if new attack paths to secrets are introduced and automatically upload SARIF findings to the **GitHub Security tab**.

---

## 11. Reference Cypher Queries

Operators and security researchers can run direct queries against FalkorDB. See [`queries.cypher`](file:///d:/falkor_hackathon/queries.cypher) for the full catalog:

```cypher
// Discover attack chains with difficulty weighting
MATCH p = (i:Input {attacker: true})-[:FLOWS*1..8]->(c:Capability {crown: true})
RETURN [n IN nodes(p) | coalesce(n.name, n.id, labels(n)[0])] AS path_nodes,
       reduce(cost = 0, e IN relationships(p) | cost + coalesce(e.difficulty, 1)) AS total_difficulty,
       length(p) AS hop_count
ORDER BY total_difficulty ASC LIMIT 50;

// Incident Mode: Compromised action blast radius
MATCH (a:Action {slug: $slug})<-[:USES]-(step:Step)<-[:HAS_STEP]-(j:Job)
OPTIONAL MATCH (j)-[:HOLDS]->(s:Secret)
OPTIONAL MATCH (j)<-[:HAS_JOB]-(w:Workflow)
RETURN a.slug AS action_slug,
       collect(DISTINCT w.path) AS affected_workflows,
       collect(DISTINCT j.id) AS affected_jobs,
       collect(DISTINCT s.name) AS exposed_secrets;
```

---

## 12. AI Disclosure & Compliance

In strict compliance with hackathon rules:
* **LLM Engine**: Google Gemini 2.5 Flash via official `google-genai` SDK on the free tier.
* **Agent Architecture**: Hand-rolled bounded loop with native tool calling and auto-schema generation. No third-party agent frameworks were used.
* **Verification**: All agent claims are strictly verified against FalkorDB graph state ("no path, no claim").
* **Responsible Corpus Disclosure**: All corpus metrics from 250+ public workflows are aggregated and anonymized without naming individual vulnerable repositories.
