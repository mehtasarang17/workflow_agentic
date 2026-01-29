import os
import operator
from typing import Annotated, List, TypedDict, Union

from langchain_aws import ChatBedrock
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END
from tools import available_tools
from pydantic import BaseModel, Field

# --- State Application ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    plan: List[str]
    current_step: int
    results: dict

# --- LLM Setup ---
# Using Amazon Nova Lite via Bedrock
llm = ChatBedrock(
    model_id="apac.amazon.nova-lite-v1:0", 
    model_kwargs={
        "temperature": 0.4,  # Balanced creativity/consistency for production
        "top_p": 0.9,        # Nucleus sampling for better quality
    },
    max_tokens=8192,  # Support complex workflows (20+ nodes)
    region_name=os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")
)

from graph_models import WorkflowGraph
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

# --- Planner Agent ---
# We use the 'with_structured_output' capability if available, or just a strong system prompt with JSON enforcement.
# Since Bedrock + LangChain integration varies, we will use a strong system prompt for JSON output.
planner_system_prompt = """You are a Workflow Architect. Your objective is to design a high-fidelity automation workflow in a strict JSON format compatible with the company application.

### MANDATORY JSON STRUCTURE
The response must be a single JSON object with this exact structure:
{{
  "version": "1.0",
  "exported_at": "2026-01-27T10:41:52Z",
  "workflows": [
    {{
      "name": "Mandatory Workflow Name",
      "description": "...",
      "workflow_data": {{
        "nodes": [
          {{
            "id": "node-1",
            "type": "webhook",
            "label": "Human Readable Label",
            "config": {{ "accept_json_only": true }},
            "nodeNumber": 1
          }}
        ],
        "connections": [
          {{ "from": "node-1", "to": "node-2" }}
        ]
      }},
      "is_active": true
    }}
  ],
  "workflow_comments": {{}}
}}

### CRITICAL RULES FOR NODES
1. **LABEL**: EVERY node MUST have a descriptive `label` string (e.g., "Check CPU", "Clear Cache"). If missing, it will show as "Untitled".
### INTEGRATION REGISTRY (DATA-AWARE)
You MUST only use integrations that are available in the database. 
If an integration is not in this list, create a `log` node with message: "No integrations available for this requirement.".

| Service | integration_id | type_name | Available Tasks & Mandatory Params |
| :--- | :--- | :--- | :--- |
| **Email** | 48 | `Email` | `send_email` (to, subject, body), `send_bulk_email` (recipients, subject, body) |
| **AWS** | 42 | `AWS` | `list_blocked_ips_waf` (ipset_name, scope), `unblock_ip_waf` (ipset_name, ip, scope) |
| **Github** | 49 | `Github` | `create_issue` (params), `list_projects` (params) |
| **Gitlab** | 45 | `Gitlab` | `create_issue` (params), `list_projects` (params) |

### NODE TYPE SPECIFICATIONS
| Type | Mandatory Fields |
| :--- | :--- |
| `webhook` | `config`: {{"accept_json_only": true}}, `params`: {{}} |
| `condition` | `config`: {{"condition": {{"format": "simple", "type": "simple", "left": "{{{{variable}}}}", "operator": "eq/ne/gt/lt", "right": "value"}}, "true_nodes": [], "false_nodes": []}} |
| `integration` | **ROOT**: `integration_id`, `task`, `task_display_name`, `integration_type_name`, `continue_on_error`: false, `run_all_tasks`: false. <br> **PARAMS**: contains task parameters, `timeout_seconds`: 300, AND `integration_types`: "Same as integration_type_name" |
| `log` | `config`: {{"message": "..."}} |
| `script` | `params`: {{"script": "python code here"}} |
| `http` | `config`: {{"url": "...", "method": "GET/POST/PUT/DELETE", "body": {{}}}} |

### EXAMPLE INTEGRATION (Strict Alignment)
{{
  "id": "node-2",
  "type": "integration",
  "label": "Send Email",
  "integration_id": 48,
  "task": "send_email",
  "task_display_name": "Send Email",
  "integration_type_name": "Email",
  "params": {{
    "to": "user@example.com",
    "subject": "Alert",
    "body": "Issue detected",
    "timeout_seconds": 300,
    "integration_types": "Email"
  }},
  "nodeNumber": 2,
  "continue_on_error": false,
  "run_all_tasks": false
}}

### EXAMPLE CONDITION NODE (CRITICAL)
{{
  "id": "node-5",
  "type": "condition",
  "label": "Check Status",
  "nodeNumber": 5,
  "config": {{
    "condition": {{
      "format": "simple",
      "type": "simple",
      "left": "{{{{data.status}}}}",
      "operator": "eq",
      "right": "blocked"
    }},
    "true_nodes": [],
    "false_nodes": []
  }}
}}

### COMPLETE WORKFLOW EXAMPLE (Script → Condition → Branches)
This shows the CORRECT pattern for workflows with script extraction and conditions:

**Nodes:**
```json
[
  {{"id": "node-1", "type": "webhook", "label": "Receive Alert", "nodeNumber": 1}},
  {{"id": "node-2", "type": "script", "label": "Extract IP", "nodeNumber": 2, "params": {{"script": "ip = data['ip']"}}}},
  {{"id": "node-3", "type": "integration", "label": "Check AWS WAF", "integration_id": 42, "task": "list_blocked_ips_waf", "nodeNumber": 3}},
  {{"id": "node-4", "type": "condition", "label": "Is IP Blocked?", "nodeNumber": 4, "config": {{"condition": {{"left": "{{{{ip}}}}", "operator": "eq", "right": "blocked"}}}}}},
  {{"id": "node-5", "type": "integration", "label": "Send Alert Email", "integration_id": 48, "task": "send_email", "nodeNumber": 5}},
  {{"id": "node-6", "type": "integration", "label": "Block IP", "integration_id": 42, "task": "unblock_ip_waf", "nodeNumber": 6}},
  {{"id": "node-7", "type": "log", "label": "Log Action", "nodeNumber": 7}}
]
```

**Connections (CRITICAL - Study this pattern):**
```json
[
  {{"from": "node-1", "to": "node-2"}},           // Webhook → Script
  {{"from": "node-2", "to": "node-3"}},           // Script → AWS Check
  {{"from": "node-3", "to": "node-4"}},           // AWS Check → Condition
  {{"from": "node-4", "sourceHandle": "true", "to": "node-5"}},   // If blocked → Email
  {{"from": "node-4", "sourceHandle": "false", "to": "node-6"}},  // If not blocked → Block IP
  {{"from": "node-5", "to": "node-7"}},           // Email → Log (merge point)
  {{"from": "node-6", "to": "node-7"}}            // Block IP → Log (merge point)
]
```

**Key Pattern**: webhook → script → integration → **condition** → (true branch + false branch) → **merge to common node**

### CONNECTION RULES (CRITICAL - READ CAREFULLY)

**EVERY node must be connected - no orphaned or dead-end nodes allowed!**

#### Sequential Flow (Default Pattern)
Actions should flow in logical order: A → B → C → D
```json
{{"from": "node-1", "to": "node-2"}},
{{"from": "node-2", "to": "node-3"}},
{{"from": "node-3", "to": "node-4"}}
```

#### Parallel Actions Pattern
When multiple actions must happen, they should be **SEQUENTIAL**, not parallel:
```json
// CORRECT - Sequential flow
{{"from": "node-5", "to": "node-6"}},  // First action
{{"from": "node-6", "to": "node-7"}},  // Second action
{{"from": "node-7", "to": "node-8"}},  // Third action
{{"from": "node-8", "to": "node-9"}}   // Continue to next step

// WRONG - Parallel branches without convergence
{{"from": "node-5", "to": "node-6"}},
{{"from": "node-5", "to": "node-7"}},  // Dead end!
{{"from": "node-5", "to": "node-8"}}   // Dead end!
```

#### Condition Node Pattern
Condition branches **MUST** merge back together:
```json
{{"from": "node-4", "sourceHandle": "true", "to": "node-5"}},
{{"from": "node-4", "sourceHandle": "false", "to": "node-8"}},
// True branch: sequential actions
{{"from": "node-5", "to": "node-6"}},
{{"from": "node-6", "to": "node-7"}},
{{"from": "node-7", "to": "node-10"}},  // Merge here
// False branch: sequential actions
{{"from": "node-8", "to": "node-9"}},
{{"from": "node-9", "to": "node-10"}},  // Merge here
// Continue after merge
{{"from": "node-10", "to": "node-11"}}
```

#### Mandatory Rules
1. **Start node** (webhook/trigger): Must connect to exactly 1 node
2. **Condition nodes**: Must have exactly 2 outgoing connections (sourceHandle: "true" and "false")
3. **All other nodes**: Must have at least 1 outgoing connection (except final log/email nodes)
4. **No orphans**: Every node except start must have at least 1 incoming connection
5. **Branch convergence**: All condition branches must eventually merge to a common node

### CRITICAL VALIDATION RULES (MUST FOLLOW)

Before generating the workflow, ensure:

1. **Unique Node IDs**: Every node must have a unique ID (node-1, node-2, node-3, etc.). No duplicates allowed.

2. **Valid Connections**: All 'from' and 'to' IDs in connections must reference existing node IDs in the nodes array.

3. **Required Parameters**: Integration nodes must include ALL required parameters:
   - Email.send_email: to, subject, body
   - Email.send_bulk_email: recipients, subject, body
   - AWS.list_blocked_ips_waf: ipset_name, scope
   - AWS.unblock_ip_waf: ipset_name, ip, scope
   - Github/Gitlab: params object

4. **Valid Operators**: Condition nodes must use ONLY these operators: eq, ne, gt, lt, gte, lte, contains, not_contains

5. **No Cycles**: Workflow must NOT contain circular dependencies (node A → node B → node A)

6. **Metadata**: Workflow must have non-empty name and description

7. **Complete Connections**: Every node must be reachable from the start node

### FINAL CHECK
- Is `integration_id` (e.g. 48 for Email) correct based on the registry?
- Does `params` include both task parameters AND `integration_types` + `timeout_seconds`?
- If the requested tool is missing, is a `log` node used?
- Are ALL nodes connected in a valid flow?
- Do condition branches merge properly?
- Are all node IDs unique?
- Do all connections reference existing nodes?
- Are all required parameters present?
- Are all operators valid?
- No circular dependencies?
- No text outside JSON.
"""

def validate_connections(graph_data):
    """Validate that all nodes are properly connected"""
    workflows = graph_data.get("workflows", [])
    if not workflows:
        return []
    
    nodes = workflows[0].get("workflow_data", {}).get("nodes", [])
    connections = workflows[0].get("workflow_data", {}).get("connections", [])
    
    errors = []
    node_ids = {n["id"] for n in nodes}
    incoming = {nid: [] for nid in node_ids}
    outgoing = {nid: [] for nid in node_ids}
    
    # Build connection graph
    for conn in connections:
        from_id = conn["from"]
        to_id = conn["to"]
        if from_id in outgoing:
            outgoing[from_id].append(to_id)
        if to_id in incoming:
            incoming[to_id].append(from_id)
    
    # Validate each node
    for node in nodes:
        nid = node["id"]
        ntype = node["type"]
        label = node.get("label", "Unknown")
        
        # Start nodes should have no incoming
        if ntype in ["webhook", "trigger"]:
            if incoming[nid]:
                errors.append(f"{nid} ({label}): Start node should have no incoming connections")
            if not outgoing[nid]:
                errors.append(f"{nid} ({label}): Start node must have at least 1 outgoing connection")
        else:
            # All other nodes must have incoming
            if not incoming[nid]:
                errors.append(f"{nid} ({label}): Orphaned node - no incoming connections")
        
        # Condition nodes must have exactly 2 outgoing (true/false)
        if ntype == "condition":
            if len(outgoing[nid]) != 2:
                errors.append(f"{nid} ({label}): Condition must have exactly 2 outgoing connections (true/false)")
        
        # Warn about potential dead ends (nodes with no outgoing except final log nodes)
        if not outgoing[nid] and ntype not in ["log"] and len(nodes) > 1:
            # Check if this is truly a dead end or just a final node
            # A final node is acceptable if it's at the end of a branch
            if incoming[nid]:  # Has incoming, so it's in the middle of flow
                errors.append(f"{nid} ({label}): Potential dead end - no outgoing connections")
    
    return errors

# --- Production-Ready Validation Functions ---

def validate_json_structure(graph_data):
    """Validate JSON structure before processing"""
    errors = []
    
    if "workflows" not in graph_data:
        errors.append("Missing 'workflows' key in root object")
        return errors
    
    if not isinstance(graph_data["workflows"], list):
        errors.append("'workflows' must be an array")
        return errors
    
    if len(graph_data["workflows"]) == 0:
        errors.append("'workflows' array is empty")
        return errors
    
    workflow = graph_data["workflows"][0]
    
    if not workflow.get("name") or not workflow.get("name").strip():
        errors.append("Workflow 'name' is required and cannot be empty")
    
    if not workflow.get("description") or not workflow.get("description").strip():
        errors.append("Workflow 'description' is required and cannot be empty")
    
    if "workflow_data" not in workflow:
        errors.append("Missing 'workflow_data' in workflow")
        return errors
    
    workflow_data = workflow["workflow_data"]
    
    if "nodes" not in workflow_data:
        errors.append("Missing 'nodes' in workflow_data")
    
    if "connections" not in workflow_data:
        errors.append("Missing 'connections' in workflow_data")
    
    return errors

def validate_node_ids(nodes):
    """Ensure all node IDs are unique"""
    errors = []
    node_ids = [n["id"] for n in nodes]
    duplicates = [nid for nid in node_ids if node_ids.count(nid) > 1]
    
    if duplicates:
        unique_dupes = list(set(duplicates))
        errors.append(f"Duplicate node IDs found: {', '.join(unique_dupes)}")
    
    return errors

def validate_connection_targets(nodes, connections):
    """Validate all connections reference existing nodes"""
    errors = []
    node_ids = {n["id"] for n in nodes}
    
    for conn in connections:
        from_id = conn.get("from")
        to_id = conn.get("to")
        
        if not from_id:
            errors.append("Connection missing 'from' field")
            continue
        
        if not to_id:
            errors.append("Connection missing 'to' field")
            continue
        
        if from_id not in node_ids:
            errors.append(f"Connection references non-existent source node: {from_id}")
        
        if to_id not in node_ids:
            errors.append(f"Connection references non-existent target node: {to_id}")
    
    return errors

# Integration parameter requirements
INTEGRATION_REQUIRED_PARAMS = {
    "Email": {
        "send_email": ["to", "subject", "body"],
        "send_bulk_email": ["recipients", "subject", "body"]
    },
    "AWS": {
        "list_blocked_ips_waf": ["ipset_name", "scope"],
        "unblock_ip_waf": ["ipset_name", "ip", "scope"]
    },
    "Github": {
        "create_issue": ["params"],
        "list_projects": ["params"]
    },
    "Gitlab": {
        "create_issue": ["params"],
        "list_projects": ["params"]
    }
}

def validate_integration_params(nodes):
    """Validate integration nodes have required parameters"""
    errors = []
    
    for node in nodes:
        if node.get("type") != "integration":
            continue
        
        integration_type = node.get("integration_type_name")
        task = node.get("task")
        params = node.get("params", {})
        node_id = node.get("id")
        label = node.get("label", "Unknown")
        
        if integration_type in INTEGRATION_REQUIRED_PARAMS:
            required = INTEGRATION_REQUIRED_PARAMS[integration_type].get(task, [])
            for param in required:
                if param not in params or not params[param]:
                    errors.append(
                        f"{node_id} ({label}): Missing required parameter '{param}' for {integration_type}.{task}"
                    )
    
    return errors

# Valid condition operators
VALID_OPERATORS = ["eq", "ne", "gt", "lt", "gte", "lte", "contains", "not_contains"]

def validate_condition_operators(nodes):
    """Validate condition node operators"""
    errors = []
    
    for node in nodes:
        if node.get("type") != "condition":
            continue
        
        node_id = node.get("id")
        label = node.get("label", "Unknown")
        config = node.get("config", {})
        condition = config.get("condition", {})
        operator = condition.get("operator")
        
        if not operator:
            errors.append(f"{node_id} ({label}): Missing operator in condition")
        elif operator not in VALID_OPERATORS:
            errors.append(
                f"{node_id} ({label}): Invalid operator '{operator}'. "
                f"Must be one of: {', '.join(VALID_OPERATORS)}"
            )
    
    return errors

def detect_cycles(nodes, connections):
    """Detect circular dependencies in workflow"""
    from collections import defaultdict
    
    # Build adjacency list
    graph = defaultdict(list)
    for conn in connections:
        graph[conn["from"]].append(conn["to"])
    
    # DFS to detect cycles
    visited = set()
    rec_stack = set()
    
    def has_cycle(node_id):
        visited.add(node_id)
        rec_stack.add(node_id)
        
        for neighbor in graph[node_id]:
            if neighbor not in visited:
                if has_cycle(neighbor):
                    return True
            elif neighbor in rec_stack:
                return True
        
        rec_stack.remove(node_id)
        return False
    
    node_ids = [n["id"] for n in nodes]
    for nid in node_ids:
        if nid not in visited:
            if has_cycle(nid):
                return ["Circular dependency detected in workflow connections"]
    
    return []

def auto_fix_connections(graph_data):
    """Automatically fix common connection errors before validation"""
    if "workflows" not in graph_data or not graph_data["workflows"]:
        return
    
    workflow = graph_data["workflows"][0]
    workflow_data = workflow.get("workflow_data", {})
    nodes = workflow_data.get("nodes", [])
    connections = workflow_data.get("connections", [])
    
    if not nodes or not connections:
        return
    
    # Build connection maps
    node_ids = [n["id"] for n in nodes]
    incoming = {nid: [] for nid in node_ids}
    outgoing = {nid: [] for nid in node_ids}
    
    for conn in connections:
        from_id = conn.get("from")
        to_id = conn.get("to")
        if from_id in outgoing:
            outgoing[from_id].append(conn)
        if to_id in incoming:
            incoming[to_id].append(conn)
    
    # Fix 1: Connect orphaned nodes to previous sequential node
    for i, node in enumerate(nodes):
        nid = node["id"]
        ntype = node["type"]
        
        # Skip start nodes
        if ntype in ["webhook", "trigger"]:
            continue
        
        # If orphaned and not a condition node
        if not incoming[nid] and ntype != "condition":
            # Find previous node in sequence
            if i > 0:
                prev_node = nodes[i - 1]
                prev_id = prev_node["id"]
                
                # Add connection from previous node
                new_conn = {"from": prev_id, "to": nid}
                connections.append(new_conn)
                outgoing[prev_id].append(new_conn)
                incoming[nid].append(new_conn)
                print(f"AUTO-FIX: Connected orphaned node {nid} to {prev_id}", flush=True)
    
    # Fix 2: Ensure condition nodes have exactly 2 outgoing connections
    for node in nodes:
        if node.get("type") != "condition":
            continue
        
        nid = node["id"]
        out_conns = outgoing[nid]
        
        # Count true/false branches
        true_conns = [c for c in out_conns if c.get("sourceHandle") == "true"]
        false_conns = [c for c in out_conns if c.get("sourceHandle") == "false"]
        
        # If missing branches, try to add them
        if len(true_conns) == 0 or len(false_conns) == 0:
            # Find next nodes in sequence
            node_idx = nodes.index(node)
            
            if len(true_conns) == 0 and node_idx + 1 < len(nodes):
                next_node = nodes[node_idx + 1]
                new_conn = {"from": nid, "sourceHandle": "true", "to": next_node["id"]}
                connections.append(new_conn)
                outgoing[nid].append(new_conn)
                incoming[next_node["id"]].append(new_conn)
                print(f"AUTO-FIX: Added true branch for condition {nid} to {next_node['id']}", flush=True)
            
            if len(false_conns) == 0 and node_idx + 2 < len(nodes):
                next_next_node = nodes[node_idx + 2]
                new_conn = {"from": nid, "sourceHandle": "false", "to": next_next_node["id"]}
                connections.append(new_conn)
                outgoing[nid].append(new_conn)
                incoming[next_next_node["id"]].append(new_conn)
                print(f"AUTO-FIX: Added false branch for condition {nid} to {next_next_node['id']}", flush=True)
    
    # Update connections in workflow data
    workflow_data["connections"] = connections

def planner_node(state: AgentState):
    request = state["messages"][-1].content
    
    # We will simply ask the LLM for the JSON
    prompt = ChatPromptTemplate.from_messages([
        ("system", planner_system_prompt),
        ("user", "{input}")
    ])
    
    chain = prompt | llm
    
    # Retry logic with exponential backoff
    from tenacity import retry, stop_after_attempt, wait_exponential
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    def invoke_llm_with_retry():
        return chain.invoke({"input": request})
    
    try:
        response = invoke_llm_with_retry()
        content = response.content
        
        # Simple cleanup if the LLM wraps code in markdown blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
            
        import json
        try:
            graph_data = json.loads(content)
        except json.JSONDecodeError as e:
            error_msg = f"⚠️ **JSON Parsing Error**\n\nFailed to parse LLM response as JSON: {str(e)}\n\nPlease try again with a simpler workflow request."
            print(f"DEBUG: JSON Parse Error: {e}", flush=True)
            return {
                "plan": [],
                "results": {"error": "json_parse_error"},
                "messages": [AIMessage(content=error_msg)]
            }
        
        # --- VALIDATION PHASE 1: JSON Structure ---
        json_errors = validate_json_structure(graph_data)
        if json_errors:
            error_msg = "⚠️ **JSON Structure Errors:**\n\n" + "\n".join(f"  • {err}" for err in json_errors)
            error_msg += "\n\nThe workflow JSON structure is invalid. Please try again."
            print(f"DEBUG: JSON Structure Errors:\n{error_msg}", flush=True)
            return {
                "plan": [],
                "results": {"graph": graph_data, "json_errors": json_errors},
                "messages": [AIMessage(content=error_msg)]
            }
        
        # --- POST-PROCESSING: Enforcement of Integration Schema ---
        # IDs match public.integrations table in workflow_db.sql
        INTEGRATION_MAP = {
            "email": {"id": 48, "type": "Email", "default_task": "send_email", "display": "Send Email"},
            "aws": {"id": 42, "type": "AWS", "default_task": "list_blocked_ips_waf", "display": "List Blocked IPs"},
            "github": {"id": 49, "type": "Github", "default_task": "create_issue", "display": "Create Issue"},
            "gitlab": {"id": 45, "type": "Gitlab", "default_task": "create_issue", "display": "Create Issue"}
        }

        if "workflows" in graph_data:
            for wf in graph_data["workflows"]:
                nodes = wf.get("workflow_data", {}).get("nodes", [])
                for node in nodes:
                    if node.get("type") == "integration":
                        # Find matching integration
                        itype = str(node.get("integration_type_name", "")).lower()
                        label = str(node.get("label", "")).lower()
                        match = None
                        
                        for key, val in INTEGRATION_MAP.items():
                            if key in itype or key in label:
                                match = val
                                break
                        
                        if match:
                            # Apply mandatory root fields
                            node["integration_id"] = match["id"]
                            node["integration_type_name"] = match["type"]
                            node["task"] = node.get("task") or match["default_task"]
                            node["task_display_name"] = node.get("task_display_name") or match["display"]
                            node["continue_on_error"] = node.get("continue_on_error", False)
                            node["run_all_tasks"] = node.get("run_all_tasks", False)
                            
                            # Ensure params object exists
                            if "params" not in node:
                                node["params"] = {}
                            
                            # Inject mandatory fields as per user request
                            node["params"]["timeout_seconds"] = 300
                            node["params"]["integration_types"] = match["type"]
                        else:
                            # Fallback to LOG node if it's an unrecognized integration
                            original_label = node.get('label', 'Missing Integration')
                            node["type"] = "log"
                            node["label"] = f"Log: Unsupported Integration"
                            node["config"] = {"message": f"No integrations available for this requirement: {original_label}"}
                            node["params"] = {}
                            # Clean up integration fields
                            fields_to_remove = ["integration_id", "task", "task_display_name", "integration_type_name", "continue_on_error", "run_all_tasks"]
                            for field in fields_to_remove:
                                node.pop(field, None)

        # --- AUTO-FIX: Repair common connection errors ---
        print("DEBUG: Running auto-fix for connection errors...", flush=True)
        auto_fix_connections(graph_data)

        # --- VALIDATION PHASE 2: Comprehensive Workflow Validation ---
        all_validation_errors = []
        
        if "workflows" in graph_data and graph_data["workflows"]:
            workflow = graph_data["workflows"][0]
            workflow_data = workflow.get("workflow_data", {})
            nodes = workflow_data.get("nodes", [])
            connections = workflow_data.get("connections", [])
            
            # Run all validation checks
            all_validation_errors.extend(validate_node_ids(nodes))
            all_validation_errors.extend(validate_connection_targets(nodes, connections))
            all_validation_errors.extend(validate_connections(graph_data))
            all_validation_errors.extend(validate_integration_params(nodes))
            all_validation_errors.extend(validate_condition_operators(nodes))
            all_validation_errors.extend(detect_cycles(nodes, connections))
        
        if all_validation_errors:
            error_msg = "⚠️ **Workflow Validation Failed**\n\n**Errors detected:**\n" + "\n".join(f"  • {err}" for err in all_validation_errors)
            error_msg += "\n\n**Suggestion:** Please review the workflow structure and ensure all nodes are properly connected with valid parameters."
            print(f"DEBUG: Validation Errors:\n{error_msg}", flush=True)
            return {
                "plan": [],
                "results": {"graph": graph_data, "validation_errors": all_validation_errors},
                "messages": [AIMessage(content=error_msg)]
            }

        node_count = 0
        if "workflows" in graph_data:
            node_count = len(graph_data["workflows"][0].get("workflow_data", {}).get("nodes", []))

        return {
            "plan": [], 
            "results": {"graph": graph_data},
            "messages": [AIMessage(content=f"✅ Workflow Plan Generated with {node_count} nodes. All validations passed.")]
        }
    except Exception as e:
        print(f"DEBUG: Planner Error: {e}", flush=True)
        return {
             "messages": [AIMessage(content=f"Error generating plan: {str(e)}")],
             "results": {}
        }


# --- Executor Agent ---
# The linear executor is not compatible with the new Graph structure.
# For now, we only generate the Visual Graph.

def executor_node(state: AgentState):
    return {"messages": [AIMessage(content="Executor disabled for Visual Graph mode.")]}


# --- Graph Construction ---
workflow = StateGraph(AgentState)

workflow.add_node("planner", planner_node)
# workflow.add_node("executor", executor_node) # Disabled

workflow.set_entry_point("planner")

workflow.add_edge("planner", END) # End after planning

# workflow.add_edge("planner", "executor")
# workflow.add_conditional_edges("executor", should_continue)

app_graph = workflow.compile()
