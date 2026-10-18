# ChokePoint
# Agent-maintained build log. Other agents: read this to understand what's been done.
#
# Author: Antigravity (Google DeepMind Advanced Agentic Coding)
# Created: 2026-10-18
# Last Updated: 2026-10-18
#
# === CHANGE LOG ===
#
# [2026-10-18] P0: Foundation
# - Created project skeleton
# - Docker Compose for FalkorDB
# - .env template (Gemini 2.5 Flash free tier, no paid APIs)
# - Python backend structure
# - React+Vite+TS frontend structure
# - FastMCP hello-world tool
# - FalkorDB connection + algorithm verification
#
# [2026-10-18] P1: Parser & Ingestor
# - GitHub Actions YAML parser (workflows, jobs, steps, triggers, untrusted inputs)
# - Composite action resolver and reusable workflow tracking
# - FLOWS edge derivation (inject, exec, expose, poison, consume, grant, inherit)
# - Batch UNWIND MERGE writer and graph index schema
#
# [2026-10-18] P2: Graph Tools
# - Attack chain discovery (list_chains, explain_chain with hop-by-hop evidence)
# - Incident mode (blast_radius, corpus_exposure)
# - Minimum cut / fix set (algo.maxFlow + residual BFS, choke_points)
# - PR gate snapshot comparison (diff_snapshots)
# - Advisory search and guarded read-only Cypher
#
# [2026-10-18] P3: MCP Server & Agent
# - FastMCP server with Streamable HTTP/SSE transport
# - Abstract LLM client (Gemini 2.5 Flash free tier, Groq, Ollama)
# - Hand-rolled bounded agent loop with live step callbacks
# - Investigation trace recording and faithfulness verifier
#
# [2026-10-18] P4: Patch Engine & Verification
# - Comment-preserving ruamel.yaml patch engine (env_var, pin, permission, trigger)
# - What-if simulation via GRAPH.COPY + re-ingest verification
#
# [2026-10-18] P5: Eval Benchmark Harness
# - Synthetic generator with planted ground truth vulnerabilities
# - Per-file flat baseline scanner simulating traditional linters
# - Quantitative evaluation harness measuring alert fatigue reduction and min-cut efficacy
#
# [2026-10-18] P6: Corpus Analysis
# - 250-workflow public repository corpus generator
# - Ecosystem choke point analysis, action centrality, and privacy-preserving aggregates
#
# [2026-10-18] P7: Web Console
# - React + Vite + TypeScript dashboard with cyber-security dark theme
# - Real-time SSE agent trace, attack chain canvas, min-cut comparisons, patch diffs,
#   incident blast radius explorer, PR gate status, and corpus analytics
#
# [2026-10-18] P8: CLI & Composite GitHub Action Gate
# - Complete chokepoint CLI (scan, cut, patch, incident, eval, corpus)
# - SARIF 2.1.0 output generator for GitHub Code Scanning
# - Composite GitHub Action (action/action.yml)
#
# [2026-10-18] P9: Documentation & Delivery
# - Comprehensive README.md with architecture, data model, and quickstart
# - Reference queries.cypher catalog
# - Pytest unit test suite
#
# === ARCHITECTURE DECISIONS ===
#
# 1. LLM: Google Gemini 2.5 Flash (free tier) — native tool calling, auto-schema
#    Abstracted behind LLMClient interface for Groq/Ollama swap
# 2. Graph DB: FalkorDB via Docker — algo.maxFlow, algo.SPpaths, centrality
# 3. MCP: FastMCP with Streamable HTTP + bearer auth
# 4. Backend: Python 3.10+ / FastAPI / Pydantic v2
# 5. Frontend: React + Vite + TypeScript
# 6. YAML Patching: ruamel.yaml (comment-preserving)
# 7. No paid services. No agent frameworks. Hand-rolled bounded loop.
#
# === PROJECT STRUCTURE ===
#
# d:\falkor_hackathon\
# ├── .env                      # Config (Gemini key, GitHub token, FalkorDB)
# ├── docker-compose.yml        # FalkorDB + full stack
# ├── queries.cypher            # Cypher reference catalog
# ├── README.md                 # Full documentation
# ├── action/
# │   └── action.yml            # Composite GitHub Action PR gate
# ├── backend/
# │   ├── pyproject.toml
# │   ├── requirements.txt
# │   ├── src/
# │   │   └── chokepoint/
# │   │       ├── __init__.py
# │   │       ├── config.py          # Pydantic settings from .env
# │   │       ├── db.py              # FalkorDB connection
# │   │       ├── schema.py          # Graph schema (nodes, edges, indexes)
# │   │       ├── cli.py             # CLI command suite
# │   │       ├── mcp_server.py      # FastMCP server
# │   │       ├── api.py             # FastAPI REST + SSE trace
# │   │       ├── parser/            # YAML parsing & FLOWS derivation
# │   │       ├── ingestor/          # Batch UNWIND MERGE & GitHub fetch
# │   │       ├── tools/             # Chains, blast, cuts, diff, cypher
# │   │       ├── patch/             # ruamel.yaml & GRAPH.COPY whatif
# │   │       ├── agent/             # Gemini loop, trace, verifier
# │   │       ├── eval/              # Planted fixtures, baseline, benchmark
# │   │       └── corpus/            # 250-repo ecosystem dataset & analysis
# │   └── tests/                 # Comprehensive Pytest suite
# └── frontend/                  # React + Vite + TypeScript console
