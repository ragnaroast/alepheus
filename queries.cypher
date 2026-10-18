// ============================================================================
// CHOKEPOINT CYPHER QUERY CATALOG (FalkorDB)
// ============================================================================

// 1. Attack Chain Discovery (Bounded Variable-Depth Traversal)
// Finds all paths from attacker-controlled inputs to crown jewel secrets or publish capabilities
MATCH p = (i:Input {attacker: true})-[:FLOWS*1..8]->(c:Capability {crown: true})
RETURN [n IN nodes(p) | coalesce(n.name, n.id, labels(n)[0])] AS path_nodes,
       reduce(cost = 0, e IN relationships(p) | cost + coalesce(e.difficulty, 1)) AS total_difficulty,
       length(p) AS hop_count
ORDER BY total_difficulty ASC, hop_count ASC
LIMIT 50;


// 2. Incident Mode: Upstream Compromised Action Blast Radius
// Evaluates which jobs, workflows, and high-value secrets are exposed if an action is compromised
MATCH (a:Action {slug: $slug})<-[:USES]-(step:Step)<-[:HAS_STEP]-(j:Job)
OPTIONAL MATCH (j)-[:HOLDS]->(s:Secret)
OPTIONAL MATCH (j)<-[:HAS_JOB]-(w:Workflow)
RETURN a.slug AS action_slug,
       collect(DISTINCT w.path) AS affected_workflows,
       collect(DISTINCT j.id) AS affected_jobs,
       collect(DISTINCT s.name) AS exposed_secrets;


// 3. Choke Points via Degree Centrality
// Finds high-leverage bottlenecks in the workflow graph
MATCH (n)
WHERE n:Step OR n:Job OR n:Action
WITH n,
     size([(n)<-[:FLOWS]-() | 1]) AS in_flows,
     size([(n)-[:FLOWS]->() | 1]) AS out_flows
RETURN coalesce(n.name, n.id, n.slug) AS component,
       labels(n)[0] AS type,
       in_flows,
       out_flows,
       (in_flows * out_flows) AS leverage_score
ORDER BY leverage_score DESC
LIMIT 20;


// 4. Minimum Cut Capacity Subgraph Preparation (algo.maxFlow)
// Selects flow edges with fix_cost capacities between attacker sources and crown jewel sinks
MATCH (src:Input {attacker: true})
MATCH (sink:Capability {crown: true})
CALL algo.maxFlow(src, sink, {
  capacityProperty: 'fix_cost',
  relationshipType: 'FLOWS'
})
YIELD flow, source, sink, edgeFlows
RETURN flow AS max_flow_capacity, edgeFlows;


// 5. PR Gate Snapshot Comparison (Base vs Head)
// Compares attack paths between base and head commit snapshots
// Base snapshot graph query:
// GRAPH: cp:<tenant>:<base_sha>
MATCH p_base = (i:Input {attacker: true})-[:FLOWS*1..8]->(c:Capability {crown: true})
RETURN count(p_base) AS base_chains_count;

// Head snapshot graph query:
// GRAPH: cp:<tenant>:<head_sha>
MATCH p_head = (i:Input {attacker: true})-[:FLOWS*1..8]->(c:Capability {crown: true})
RETURN count(p_head) AS head_chains_count;


// 6. Aggregate Corpus Exposure (Ecosystem Choke Points)
// Identifies third-party actions with the highest downstream secret access across hundreds of repos
MATCH (a:Action)<-[:USES]-(step:Step)<-[:HAS_STEP]-(j:Job)-[:HOLDS]->(s:Secret)
RETURN a.slug AS third_party_action,
       count(DISTINCT j) AS jobs_using_action,
       count(DISTINCT s) AS secrets_accessible,
       collect(DISTINCT s.name)[..5] AS sample_secrets
ORDER BY secrets_accessible DESC, jobs_using_action DESC
LIMIT 20;


// 7. Graph Isolation & What-If Verification
// Copies live graph to isolated whatif namespace to verify patch re-analysis
// GRAPH.COPY cp:default:latest whatif:default:simulation
