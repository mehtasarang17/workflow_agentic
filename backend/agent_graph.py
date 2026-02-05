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
            "id": "node_1",
            "type": "webhook",
            "label": "Human Readable Label",
            "config": {{ "accept_json_only": true }},
            "nodeNumber": 1
          }}
        ],
        "connections": [
          {{ "from": "node_1", "to": "node_2" }}
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
If an integration is not in this list (e.g., Weather API, CoinGecko), use an `http` node instead of an integration node.
Only create a `log` node if the request is impossible to fulfill.

| Service | integration_id | type_name | Available Tasks & Mandatory Params |
| :--- | :--- | :--- | :--- |
| **AWS** | 5 | `Aws` | **S3:** `check_s3_bucket_policy_public_access`, `check_s3_bucket_acl_public_read`, `check_s3_bucket_acl_public_write`, `check_s3_public_access_block_disabled`, `check_s3_versioning_disabled`, `check_s3_encryption_disabled`, `check_s3_server_side_encryption_enabled`, `check_s3_logging_disabled`, `check_s3_lifecycle_policies_missing`, `check_s3_mfa_delete_disabled` | **ACM:** `check_acm_autorenewal_not_enabled`, `check_acm_certificate_export_not_monitored`, `check_acm_certificates_near_expiration`, `check_acm_certificate_transparency_disabled` | **CloudTrail:** `check_cloudtrail_analysis_not_automated`, `check_cloudtrail_api_alarms_missing`, `check_cloudtrail_bucket_access_logging_disabled`, `check_cloudtrail_bucket_mfa_delete_disabled`, `check_cloudtrail_bucket_policy_changes_not_monitored`, `check_cloudtrail_bucket_policy_permissive`, `check_cloudtrail_cloudwatch_integration_missing`, `check_cloudtrail_cmk_deletion_not_alerted`, `check_cloudtrail_data_events_not_logged`, `check_cloudtrail_digest_files_not_generated`, `check_cloudtrail_history_not_exported`, `check_cloudtrail_iam_changes_not_monitored`, `check_cloudtrail_insights_disabled`, `check_cloudtrail_lambda_selectors_missing`, `check_cloudtrail_lifecycle_policy_missing`, `check_cloudtrail_log_validation_disabled`, `check_cloudtrail_logging_stopped`, `check_cloudtrail_logs_not_replicated`, `check_cloudtrail_management_events_not_logged`, `check_cloudtrail_multiregion_trail_missing`, `check_cloudtrail_nacl_changes_not_monitored`, `check_cloudtrail_no_kms_encryption`, `check_cloudtrail_not_enabled_all_regions`, `check_cloudtrail_not_monitored_for_suspicious_activity`, `check_cloudtrail_org_trail_disabled`, `check_cloudtrail_retention_too_short`, `check_cloudtrail_root_usage_not_alerted`, `check_cloudtrail_s3_bucket_insecure`, `check_cloudtrail_s3_selectors_missing`, `check_cloudtrail_sg_changes_not_monitored`, `check_cloudtrail_signin_failures_not_monitored`, `check_cloudtrail_sns_notifications_missing`, `check_cloudtrail_trail_changes_not_monitored`, `check_cloudtrail_unauthorized_calls_not_detected`, `check_cloudtrail_vpc_changes_not_monitored`, `check_kms_cloudtrail_not_enabled` | **IAM:** `check_iam_full_admin_privileges` | **KMS:** `check_kms_rotation_disabled`, `check_kms_public_access_allowed`, `check_kms_material_expiration_unmanaged`, `check_kms_multi_region_not_used`, `check_kms_deletion_window_incorrect` | **Lambda:** `check_lambda_deprecated_runtime`, `check_lambda_public_resource_policy`, `check_lambda_tracing_disabled`, `check_lambda_vpc_not_used`, `check_lambda_hardcoded_secrets` | **RDS:** `check_rds_activity_streams_disabled`, `check_rds_audit_logging_disabled`, `check_rds_autoupgrade_disabled`, `check_rds_backup_retention_7_days`, `check_rds_deletion_protection_disabled`, `check_rds_no_encryption_at_rest`, `check_rds_publicly_accessible`, `check_rds_storage_autoscaling_disabled`, `check_rds_outdated_engine_version` | **WAF:** `check_waf_bot_control_not_enabled`, `check_waf_logging_not_enabled`, `check_waf_rate_limiting_not_configured`, `check_waf_managed_rules_not_used` (all take `params`) |
| **Github** | 15 | `Github` | `check_github_two_factor_authentication_not_enforced_organization_wide` (params), `create_issue` (params), `list_repos` (params) |
| **Gitlab** | 45 | `Gitlab` | `check_gitlab_access_tokens_without_expiry` (params), `check_gitlab_2fa_not_enforced` (params), `create_issue` (params), `list_projects` (params) |
| **Azure** | 55 | `Azure` | `check_azure_public_ip_addresses`, `check_azure_sql_injection_protection_missing`, `check_azure_waf_not_enabled`, `check_azure_storage_class_analysis_disabled`, `check_azure_users_without_multifactor_authentication`, `check_azure_ssh_from_00000`, `check_azure_unencrypted_uploads_allowed`, `check_azure_vnet_peering_not_secured` |
| **Gcp** | 54 | `Gcp` | **IAM:** `check_gcp_users_without_multi_factor_authentication`, `check_gcp_overly_permissive_roles`. **Storage:** `check_gcp_bucket_policy_public_access`, `check_gcp_public_access_allowed`. **Compute:** `check_gcp_public_ip_addresses`. **SQL:** `check_gcp_retention_too_short`. **Network:** `check_gcp_vpc_flow_logs_disabled`. **KMS:** `check_gcp_rotation_disabled`. **Logging:** `check_gcp_logging_stopped` |
| **Email** | 10 | `Email` | `send_email` (to, subject, body) |


### NODE TYPE SPECIFICATIONS
| Type | Mandatory Fields |
| :--- | :--- |
| `webhook` | `config`: {{"accept_json_only": true}}, `params`: {{}} |
| `condition` | `config`: {{"condition": {{"format": "simple", "type": "simple", "left": "{{{{variable}}}}", "operator": "eq/ne/gt/lt", "right": "value"}}, "true_nodes": [], "false_nodes": []}} |
| `integration` | **ROOT**: `integration_id`, `task`, `task_display_name`, `integration_type_name`, `continue_on_error`: false, `run_all_tasks`: false. <br> **PARAMS**: contains task parameters, `timeout_seconds`: 300, AND `integration_types`: "Same as integration_type_name" |
| `log` | `config`: {{"message": "...", "log_level": "info/warning/error"}} |
| `http` | `config`: {{"url": "...", "method": "GET/POST/PUT/DELETE", "body": {{}}}} |

### AMBIGUITY RESOLUTION & DEFAULTS
1. **DEFAULT PROVIDER**: If the user does not specify a cloud provider (AWS, Azure, GCP), **DEFAULT TO AWS**.
2. **WAF**: "WAF" refers to **AWS WAF** (`check_waf_...`) unless Azure or GCP is explicitly mentioned.
3. **LOGGING**: Generic "logging" checks usually refer to **AWS CloudTrail** or **AWS WAF** unless specified otherwise.
4. **S3 / BUCKETS**: Generic "S3" or "Bucket" checks refer to **`check_s3_bucket_policy_public_access`**.
5. **WAF BOT CONTROL**: MUST use task `check_waf_bot_control_not_enabled`.

### CRITICAL - MANDATORY RESTRICTION: FORBIDDEN NODES
1. **SCRIPT NODES**: Do NOT generate `script` nodes under any circumstances. They are NOT supported.
2. For data processing, use template variables directly: `{{$node_N.data.field}}`.

### EXAMPLE INTEGRATION (Strict Alignment)
{{
  "id": "node_2",
  "type": "integration",
  "label": "Send Email",
  "integration_id": 10,
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
  "label": "Check Temperature",
  "params": {{}},
  "nodeNumber": 5,
  "config": {{
    "condition": {{
      "format": "simple",
      "type": "simple",
      "left": "{{$node_4.data.body.temperature_2m}}",
      "operator": "lt",
      "right": "\"2\""
    }},
    "true_nodes": [],
    "false_nodes": []
  }},
  "continue_on_error": false,
  "run_all_tasks": false
}}

### VARIABLE SUBSTITUTION & REFERENCING (MANDATORY FORMAT)
1. **Format**: ALWAYS use `{{{{$node_N.data.body.field}}}}` for Webhooks and HTTP. For integrations, use `{{{{$node_N.data}}}}` for full response or `{{{{$node_N.data.field}}}}` for specific fields.
2. **Double Braces**: Use double braces `{{{{ ... }}}}`. This is MANDATORY - template variables MUST be wrapped in curly braces!
3. **Reference by Node Number**: `N` is the `nodeNumber` of the source node.
4. **Webhook/HTTP Rule**: Data is accessible via `{{{{$node_1.data}}}}`.
5. **Integration Rule**: Use `{{{{$node_2.data}}}}` for full response.
6. **Node IDs**: The system will automatically align `id` with `node_N`.

### CRITICAL SYNTAX RULES - TEMPLATE VARIABLES MUST USE CURLY BRACES
**ALWAYS wrap template variables in {{{{ }}}}:**
- ✅ CORRECT: `{{{{$node_2.data}}}}`  (full integration response)
- ✅ CORRECT: `{{{{$node_1.data}}}}`  (full webhook/HTTP response)
- ❌ WRONG: `node_2.data` (missing {{{{ }}}})
- ❌ WRONG: `$node_2.data` (missing {{{{ }}}})
- ❌ WRONG: `{{{{$node_1.data.body.temperature}}}}` (AVOID specific fields - use full object!)

### CRITICAL - LOGGING RULE
**For LOG nodes, ALWAYS log the full data object:**
- ✅ `{{{{$node_N.data}}}}`
- ❌ Do NOT try to access specific fields like `{{{{$node_N.data.body}}}}` or `{{{{$node_N.data.items}}}}` unless you are 100% sure of the structure. Safest is FULL DATA.

### CRITICAL EXAMPLES - DATA ACCESS

**CORRECT - Universal Logging Pattern:**
```
Log full response: {{{{$node_1.data}}}}  // ALWAYS USE THIS
```

**WRONG - Guessing Fields:**
```
❌ {{{{$node_1.data.body.check_name}}}}  // INCORRECT - do not guess path
❌ {{{{$node_1.data.repositories}}}} // INCORRECT - do not guess path
❌ `Repositories: node_1.data` // INCORRECT - missing {{{{ }}}}!
```


**Key Pattern**: webhook → integration → **condition** → (true branch + false branch) → **merge to common node**

### CONNECTION RULES (CRITICAL - READ CAREFULLY)

**EVERY node must be connected - no orphaned or dead-end nodes allowed!**

#### Sequential Flow (Default Pattern)
Actions should flow in logical order: A → B → C → D
```json
{{ "from": "node_1", "to": "node_2" }},
{{ "from": "node_2", "to": "node_3" }},
{{ "from": "node_3", "to": "node_4" }}
```

#### Parallel Actions Pattern
When multiple actions must happen, they should be **SEQUENTIAL**, not parallel:
```json
// CORRECT - Sequential flow
{{ "from": "node_5", "to": "node_6" }},
{{ "from": "node_6", "to": "node_7" }},
{{ "from": "node_7", "to": "node_8" }},
{{ "from": "node_8", "to": "node_9" }}

// WRONG - Parallel branches without convergence
{{ "from": "node_5", "to": "node_6" }},
{{ "from": "node_5", "to": "node_7" }},
{{ "from": "node_5", "to": "node_8" }}
```

4. **MERGE / FAN-IN (MANDATORY)**:
   - When you have multiple parallel branches (e.g., checking AWS, Azure, GCP simultaneously), they **MUST** all connect to a single `log` node (serving as a **Merge Node/Sync Point**) *before* proceeding to a `condition` node.
   - **DO NOT** connect multiple parallel nodes directly to a `condition` node unless you are sure the condition handles asynchronous inputs (which it often doesn't).
   - **Pattern**: `[Branch A] -> [Merge Log]`, `[Branch B] -> [Merge Log]`, `[Merge Log] -> [Condition]`.
   - The Merge Log should summarize findings, e.g., `message: "Scans complete. AWS: {{...}}, Azure: {{...}}"`

#### Condition Node Pattern (CRITICAL)
Condition branches **MUST** connect to valid nodes. You CANNOT have a "dead end" branch unless it connects to a Log node.
**Every condition must have BOTH a 'true' and 'false' connection.**
```json
{{ "from": "node_4", "sourceHandle": "true", "to": "node_5" }},
{{ "from": "node_4", "sourceHandle": "false", "to": "node_6" }}
```
**Avoid Orphans:** Ensure `node_5` and `node_6` are connected to the next step or are valid end-state Log nodes.
// True branch: sequential actions
{{ "from": "node_5", "to": "node_6" }},
{{ "from": "node_6", "to": "node_7" }},
{{ "from": "node_7", "to": "node_10" }},
// False branch: sequential actions
{{ "from": "node_8", "to": "node_9" }},
{{ "from": "node_9", "to": "node_10" }},
// Continue after merge
{{ "from": "node_10", "to": "node_11" }}
```

### MANDATORY: CHAIN LINKING (NO ORPHANS)
**YOU MUST EXPLICITLY CONNECT EVERY NODE.**
1.  **Iterate through your nodes**: For every Node N, there MUST be a connection `{{ "from": "id_N", "to": "id_N+1" }}`.
2.  **Verify Inputs**: Check that `node_3` matches the `to` field of a connection from `node_2`.
3.  **No Islands**: If a node exists in the `nodes` array, it MUST appear in the `connections` array.
4.  **Auto-Correction**: If you create a node but forget to connect it, the workflow is INVALID.

### CRITICAL VALIDATION RULES (MUST FOLLOW)

Before generating the workflow, ensure:

1. **Unique Node IDs**: Every node must have a unique ID (`node_1`, `node_2`, etc.).

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
    "Aws": {
        "list_blocked_ips_waf": ["ipset_name", "scope"],
        "block_ip_waf": ["ipset_name", "ip", "scope"],
        "unblock_ip_waf": ["ipset_name", "ip", "scope"],
        "check_acm_autorenewal_not_enabled": ["params"],
        "check_acm_certificate_export_not_monitored": ["params"],
        "check_acm_certificates_near_expiration": ["params"],
        "check_acm_certificate_transparency_disabled": ["params"],
        "check_cloudtrail_analysis_not_automated": ["params"],
        "check_cloudtrail_api_alarms_missing": ["params"],
        "check_cloudtrail_bucket_access_logging_disabled": ["params"],
        "check_cloudtrail_bucket_mfa_delete_disabled": ["params"],
        "check_cloudtrail_bucket_policy_changes_not_monitored": ["params"],
        "check_cloudtrail_bucket_policy_permissive": ["params"],
        "check_cloudtrail_cloudwatch_integration_missing": ["params"],
        "check_cloudtrail_cmk_deletion_not_alerted": ["params"],
        "check_cloudtrail_data_events_not_logged": ["params"],
        "check_cloudtrail_digest_files_not_generated": ["params"],
        "check_cloudtrail_history_not_exported": ["params"],
        "check_cloudtrail_iam_changes_not_monitored": ["params"],
        "check_cloudtrail_insights_disabled": ["params"],
        "check_cloudtrail_lambda_selectors_missing": ["params"],
        "check_cloudtrail_lifecycle_policy_missing": ["params"],
        "check_cloudtrail_log_validation_disabled": ["params"],
        "check_cloudtrail_logging_stopped": ["params"],
        "check_cloudtrail_logs_not_replicated": ["params"],
        "check_cloudtrail_management_events_not_logged": ["params"],
        "check_cloudtrail_multiregion_trail_missing": ["params"],
        "check_cloudtrail_nacl_changes_not_monitored": ["params"],
        "check_cloudtrail_no_kms_encryption": ["params"],
        "check_cloudtrail_not_enabled_all_regions": ["params"],
        "check_cloudtrail_not_monitored_for_suspicious_activity": ["params"],
        "check_cloudtrail_org_trail_disabled": ["params"],
        "check_cloudtrail_retention_too_short": ["params"],
        "check_cloudtrail_root_usage_not_alerted": ["params"],
        "check_cloudtrail_s3_bucket_insecure": ["params"],
        "check_cloudtrail_s3_selectors_missing": ["params"],
        "check_cloudtrail_sg_changes_not_monitored": ["params"],
        "check_cloudtrail_signin_failures_not_monitored": ["params"],
        "check_cloudtrail_sns_notifications_missing": ["params"],
        "check_cloudtrail_trail_changes_not_monitored": ["params"],
        "check_cloudtrail_unauthorized_calls_not_detected": ["params"],
        "check_cloudtrail_vpc_changes_not_monitored": ["params"],
        "check_iam_full_admin_privileges": ["params"],
        "check_kms_admins_not_separated": ["params"],
        "check_kms_alias_missing": ["params"],
        "check_kms_aws_managed_keys_used": ["params"],
        "check_kms_cloudtrail_not_enabled": ["params"],
        "check_kms_compliance_not_validated": ["params"],
        "check_kms_conditions_not_restrictive": ["params"],
        "check_kms_crossaccount_not_restricted": ["params"],
        "check_kms_deletion_window_incorrect": ["params"],
        "check_kms_dr_plan_missing": ["params"],
        "check_kms_external_material_no_controls": ["params"],
        "check_kms_grants_without_expiration": ["params"],
        "check_kms_imported_material_no_backup": ["params"],
        "check_kms_key_specs_incorrect": ["params"],
        "check_kms_material_expiration_unmanaged": ["params"],
        "check_kms_metrics_not_configured": ["params"],
        "check_kms_multiregion_not_used": ["params"],
        "check_kms_no_rate_limiting": ["params"],
        "check_kms_not_least_privilege": ["params"],
        "check_kms_pending_deletion_not_reviewed": ["params"],
        "check_kms_permissive_policies": ["params"],
        "check_kms_public_access_allowed": ["params"],
        "check_kms_resource_tags_missing": ["params"],
        "check_kms_rotation_disabled": ["params"],
        "check_kms_tags_missing": ["params"],
        "check_kms_unauthorized_vpc_access": ["params"],
        "check_kms_usage_not_analyzed": ["params"],
        "check_kms_usage_not_monitored": ["params"],
        "check_kms_viaservice_missing": ["params"],
        "check_kms_wildcard_principals": ["params"],
        "check_kms_wrong_key_type": ["params"],
        "check_rds_activity_streams_disabled": ["params"],
        "check_rds_audit_logging_disabled": ["params"],
        "check_rds_autoupgrade_disabled": ["params"],
        "check_rds_backup_retention_7_days": ["params"],
        "check_rds_bluegreen_not_utilized": ["params"],
        "check_rds_certificate_rotation_unmanaged": ["params"],
        "check_rds_cloudwatch_logs_not_exported": ["params"],
        "check_rds_cluster_endpoints_misconfigured": ["params"],
        "check_rds_crossregion_replication_disabled": ["params"],
        "check_rds_default_master_username": ["params"],
        "check_rds_default_parameter_groups": ["params"],
        "check_rds_deletion_protection_disabled": ["params"],
        "check_rds_enhanced_monitoring_disabled": ["params"],
        "check_rds_error_logs_not_monitored": ["params"],
        "check_rds_event_subscriptions_missing": ["params"],
        "check_rds_global_databases_not_used": ["params"],
        "check_rds_iam_auth_disabled": ["params"],
        "check_rds_insufficient_iops": ["params"],
        "check_rds_maintenance_in_business_hours": ["params"],
        "check_rds_minor_upgrades_disabled": ["params"],
        "check_rds_multiaz_disabled": ["params"],
        "check_rds_no_automated_backups": ["params"],
        "check_rds_no_encryption_at_rest": ["params"],
        "check_rds_not_in_backup_plan": ["params"],
        "check_rds_option_groups_misconfigured": ["params"],
        "check_rds_outdated_engine_version": ["params"],
        "check_rds_outdated_tls_allowed": ["params"],
        "check_rds_performance_insights_disabled": ["params"],
        "check_rds_permissive_security_groups": ["params"],
        "check_rds_provisioned_iops_not_used": ["params"],
        "check_rds_public_snapshots": ["params"],
        "check_rds_public_subnet_deployment": ["params"],
        "check_rds_publicly_accessible": ["params"],
        "check_rds_query_logs_not_exported": ["params"],
        "check_rds_rds_proxy_not_used": ["params"],
        "check_rds_read_replicas_missing": ["params"],
        "check_rds_secrets_manager_missing": ["params"],
        "check_rds_slow_query_logs_disabled": ["params"],
        "check_rds_snapshot_retention_missing": ["params"],
        "check_rds_snapshots_not_encrypted": ["params"],
        "check_rds_ssltls_not_enforced": ["params"],
        "check_rds_storage_autoscaling_disabled": ["params"],
        "check_rds_tagging_inadequate": ["params"],
        "check_rds_unused_storage": ["params"],
        "check_rds_weak_authentication": ["params"],
        "check_lambda_alarms_not_configured": ["params"],
        "check_lambda_aliases_missing": ["params"],
        "check_lambda_arm_not_used": ["params"],
        "check_lambda_code_signing_missing": ["params"],
        "check_lambda_compliance_scanning_missing": ["params"],
        "check_lambda_crossaccount_not_controlled": ["params"],
        "check_lambda_deprecated_runtime": ["params"],
        "check_lambda_dlq_not_configured": ["params"],
        "check_lambda_dr_strategy_missing": ["params"],
        "check_lambda_efs_integration_missing": ["params"],
        "check_lambda_error_handling_missing": ["params"],
        "check_lambda_event_mappings_insecure": ["params"],
        "check_lambda_event_sources_unrestricted": ["params"],
        "check_lambda_hardcoded_secrets": ["params"],
        "check_lambda_layers_not_used": ["params"],
        "check_lambda_log_retention_not_set": ["params"],
        "check_lambda_memory_not_optimized": ["params"],
        "check_lambda_outdated_runtime": ["params"],
        "check_lambda_overly_permissive_roles": ["params"],
        "check_lambda_packages_not_scanned": ["params"],
        "check_lambda_plaintext_env_vars": ["params"],
        "check_lambda_provisioned_concurrency_missing": ["params"],
        "check_lambda_public_resource_policy": ["params"],
        "check_lambda_reserved_capacity_wrong": ["params"],
        "check_lambda_reserved_concurrency_missing": ["params"],
        "check_lambda_secrets_manager_not_used": ["params"],
        "check_lambda_snapstart_not_used": ["params"],
        "check_lambda_tags_missing": ["params"],
        "check_lambda_timeout_too_high": ["params"],
        "check_lambda_tracing_disabled": ["params"],
        "check_lambda_unused_artifacts": ["params"],
        "check_lambda_versioning_missing": ["params"],
        "check_lambda_vpc_cold_starts": ["params"],
        "check_lambda_vpc_not_used": ["params"],
        "check_lambda_xray_missing": ["params"],
        "check_waf_bot_control_not_enabled": [],
        "check_s3_bucket_policy_public_access": [],
        "check_s3_bucket_acl_public_read": [],
        "check_s3_bucket_acl_public_write": [],
        "check_s3_public_access_block_disabled": [],
        "check_s3_versioning_disabled": [],
        "check_s3_encryption_disabled": [],
        "check_s3_server_side_encryption_enabled": [],
        "check_s3_logging_disabled": [],
        "check_s3_lifecycle_policies_missing": [],
        "check_s3_mfa_delete_disabled": [],
        "check_waf_logging_not_enabled": ["params"],
        "check_waf_rate_limiting_not_configured": ["params"],
        "check_waf_managed_rules_not_used": ["params"]
    },
    "Github": {
        "create_issue": ["repo", "title", "body"],
        "list_repos": ["repo_type"]
    },
    "Gitlab": {
        "check_gitlab_access_tokens_without_expiry": ["params"],
        "check_gitlab_2fa_not_enforced": ["params"],
        "create_issue": ["params"],
        "list_projects": ["params"]
    },
    "Github": {
        "check_github_two_factor_authentication_not_enforced_organization_wide": ["params"],
        "create_issue": ["params"],
        "list_repos": ["params"]
    },
    "Gcp": {
        "check_gcp_website_hosting_insecure": [],
        "check_gcp_bucket_policy_public_access": [],
        "check_gcp_users_without_multi_factor_authentication": [],
        "check_gcp_overly_permissive_roles": [],
        "check_gcp_public_access_allowed": [],
        "check_gcp_public_ip_addresses": [],
        "check_gcp_retention_too_short": [],
        "check_gcp_vpc_flow_logs_disabled": [],
        "check_gcp_rotation_disabled": [],
        "check_gcp_logging_stopped": []
    },
    "Azure": {
        "check_azure_public_ip_addresses": [],
        "check_azure_sql_injection_protection_missing": [],
        "check_azure_waf_not_enabled": [],
        "check_azure_storage_class_analysis_disabled": [],
        "check_azure_users_without_multifactor_authentication": [],
        "check_azure_ssh_from_00000": [],
        "check_azure_unencrypted_uploads_allowed": [],
        "check_azure_vnet_peering_not_secured": []
    },
    "Email": {
        "send_email": ["to", "subject", "body"]
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

def sanitize_connections(graph_data):
    """
    Remove invalid connections where non-condition nodes attempt to branch.
    Integration nodes cannot have 'sourceHandle' (true/false) connections.
    """
    if "workflows" not in graph_data or not graph_data["workflows"]:
        return
    
    workflow = graph_data["workflows"][0]
    workflow_data = workflow.get("workflow_data", {})
    nodes = workflow_data.get("nodes", [])
    connections = workflow_data.get("connections", [])
    
    node_map = {n["id"]: n for n in nodes}
    new_connections = []
    
    for conn in connections:
        src_id = conn.get("from")
        src_node = node_map.get(src_id)
        
        if src_node:
            # Check for invalid branching: Source has handle but is NOT a condition node
            if "sourceHandle" in conn and src_node.get("type") != "condition":
                print(f"SANITIZER: Removing invalid branch from non-condition node {src_id} (Handle: {conn.get('sourceHandle')})", flush=True)
                continue # Delete this invalid connection
        
        new_connections.append(conn)
    
    workflow_data["connections"] = new_connections

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
        
        # If orphaned (allow condition nodes to be fixed too)
        if not incoming[nid]:
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

def normalize_node_ids(graph_data):
    """Align node IDs with variable references (e.g. node_1 for $node_1)"""
    if "workflows" not in graph_data or not graph_data["workflows"]:
        return
    
    workflow = graph_data["workflows"][0]
    workflow_data = workflow.get("workflow_data", {})
    nodes = workflow_data.get("nodes", [])
    connections = workflow_data.get("connections", [])
    
    if not nodes:
        return
    
    # Create mapping from old IDs to sequential underscore-based IDs
    id_mapping = {}
    
    for i, node in enumerate(nodes):
        old_id = node["id"]
        # Use nodeNumber if available, otherwise just sequential index
        num = node.get("nodeNumber", i + 1)
        new_id = f"node_{num}"
        id_mapping[old_id] = new_id
        
        # Update node ID
        node["id"] = new_id
        print(f"DEBUG: Normalized ID {old_id} → {new_id}", flush=True)
    
    # Update all connection references
    for conn in connections:
        if conn.get("from") in id_mapping:
            conn["from"] = id_mapping[conn["from"]]
        if conn.get("to") in id_mapping:
            conn["to"] = id_mapping[conn["to"]]

def auto_fix_template_variables(graph_data):
    """
    Robustly fix common LLM mistakes in template variables:
    - {{$node-1...}} -> {{$node_1...}}
    - {$node_1...} -> {{$node_1...}}
    - {node_1...} -> {{$node_1...}}
    """
    import json
    import re
    
    # Dump to string for global search/replace
    graph_str = json.dumps(graph_data)
    
    # 1. Fix single brace or missing dollar sign: {$node...}, {node...}, {{node...}}
    # This covers many variations and normalizes to {{$node_...}}
    def variable_fixer(match):
        content = match.group(1).strip()
        # Remove any existing dollar signs or 'node' prefixes to re-standardize
        content = re.sub(r'^(\$)?node[-_]', '', content)
        return f"{{{{$node_{content}}}}}"

    # Search for anything inside braces that starts with node or $node
    # This matches: {$node-1}, {{node_1}}, {$node_1}, {node-1}, etc.
    # It normalizes everything to the required {{$node_1...}} format.
    graph_str = re.sub(r'\{+\s?\$?node[-_](\d+[^}]*)\s?\}+', r'{{$node_\1}}', graph_str)
    
    # 2. Final pass: Ensure all $node- references use underscore (for stability)
    graph_str = graph_str.replace("$node-", "$node_")
    
    try:
        updated_data = json.loads(graph_str)
        graph_data.clear()
        graph_data.update(updated_data)
    except Exception as e:
        print(f"DEBUG: Error in auto_fix_template_variables: {e}", flush=True)

def normalize_workflow_format(graph_data):
    import datetime
    
    if "workflows" not in graph_data or not graph_data["workflows"]:
        return
    
    # Run template variable fix first
    auto_fix_template_variables(graph_data)
    
    # Update root exported_at to current time in exact format (ISO with microseconds)
    # Manual shows: 2026-01-29T16:10:40.291474
    graph_data["exported_at"] = datetime.datetime.now().isoformat()
    
    # Ensure workflow_comments exists at root
    if "workflow_comments" not in graph_data:
        graph_data["workflow_comments"] = {}
    
    workflow = graph_data["workflows"][0]
    workflow_data = workflow.get("workflow_data", {})
    nodes = workflow_data.get("nodes", [])
    
    for i, node in enumerate(nodes):
        # Ensure all nodes have params field
        if "params" not in node:
            node["params"] = {}
        
        # Add default position if missing
        if "position" not in node:
            node["position"] = {
                "x": 100 + (i * 250),  # Space nodes horizontally
                "y": 100
            }
        
        # Ensure continue_on_error and run_all_tasks are present
        if "continue_on_error" not in node:
            node["continue_on_error"] = False
        if "run_all_tasks" not in node:
            node["run_all_tasks"] = False
        
        if node.get("type") == "condition":
            config = node.setdefault("config", {})
            condition = config.setdefault("condition", {})
            
            if "right" in condition:
                right_val = str(condition["right"])
                # If not already wrapped in literal quotes, wrap it
                # The manual JSON shows: "right": "\"2\""
                if not (right_val.startswith('"') and right_val.endswith('"')):
                    condition["right"] = f'"{right_val}"'
                else:
                    condition["right"] = right_val
                print(f"DEBUG: Normalized condition right value to {condition['right']}", flush=True)
        
        # Fix HTTP nodes: ensure all required config fields
        if node.get("type") == "http":
            config = node.setdefault("config", {})
            config.setdefault("headers", {})
            config.setdefault("body", {})
            config.setdefault("query_params", {})
            config.setdefault("timeout", 30)
        
        # Fix webhook nodes: ensure config
        if node.get("type") == "webhook":
            if "config" not in node:
                node["config"] = {}
            if "accept_json_only" not in node["config"]:
                node["config"]["accept_json_only"] = True
        
        # Fix log nodes: ensure config and log_level
        if node.get("type") == "log":
            if "config" not in node:
                node["config"] = {}
            if "log_level" not in node["config"]:
                node["config"]["log_level"] = "info"
        
        # Fix integration nodes: ensure filter, stringified timeout, and GitLab specific fields
        if node.get("type") == "integration":
            task = node.get("task", "")
            if "task_type_filter" not in node:
                # Intelligently set filter based on task name
                if task.startswith("check_"):
                    node["task_type_filter"] = "check"
                else:
                    node["task_type_filter"] = "action"
            
            p = node.get("params", {})
            # Ensure timeout_seconds is a string if present
            if "timeout_seconds" in p:
                p["timeout_seconds"] = str(p["timeout_seconds"])
            
            # Special bypass for GitLab based on manual working JSON
            if node.get("integration_type_name") == "Gitlab":
                if "params" not in p:
                    p["params"] = ""
    
    # Fix connections from condition nodes: add condition object
    connections = workflow_data.get("connections", [])
    for conn in connections:
        # If connection has sourceHandle (true/false) but no condition object, add it
        if "sourceHandle" in conn and "condition" not in conn:
            source_handle = conn["sourceHandle"]
            conn["condition"] = {
                "value": source_handle,
                "type": "expression"
            }
            print(f"DEBUG: Added condition object to connection: {conn['from']} → {conn['to']} ({source_handle})", flush=True)

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
            "aws": {"id": 5, "type": "Aws", "default_task": "list_blocked_ips_waf", "display": "List Blocked Ips Waf"},
            "github": {"id": 50, "type": "Github", "default_task": "create_issue", "display": "Create Issue"},
            "gitlab": {"id": 53, "type": "Gitlab", "default_task": "create_issue", "display": "Create Issue"},
            "azure": {"id": 55, "type": "Azure", "default_task": "check_azure_accelerated_networking_disabled", "display": "Check Accelerated Networking"},
            "gcp": {"id": 54, "type": "Gcp", "default_task": "check_gcp_website_hosting_insecure", "display": "Check Insecure Hosting"},
            "sarang-github": {"id": 50, "type": "Github", "default_task": "create_issue", "display": "Create Issue"},
            "sarang-gitlabs": {"id": 53, "type": "Gitlab", "default_task": "create_issue", "display": "Create Issue"}
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
                            
                            # Do not inject mandatory fields here if they cause conflicts
                            # We let the AI manage the parameters directly
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

        # --- POST-PROCESSING: Normalize node IDs to match variables ---
        print("DEBUG: Normalizing node IDs...", flush=True)
        normalize_node_ids(graph_data)

        # --- AUTO-FIX: Sanitize connections (remove branches from non-condition nodes) ---
        print("DEBUG: Sanitizing connections...", flush=True)
        sanitize_connections(graph_data)

        # --- AUTO-FIX: Repair common connection errors ---
        print("DEBUG: Running auto-fix for connection errors...", flush=True)
        auto_fix_connections(graph_data)
        
        # --- POST-PROCESSING: Normalize workflow format ---
        print("DEBUG: Normalizing workflow format...", flush=True)
        normalize_workflow_format(graph_data)

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
