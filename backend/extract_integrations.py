import re
import json
import os

def parse_sql_dump(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Extract integration_types
    type_data = {}
    type_copy_match = re.search(r"COPY public\.integration_types .*?FROM stdin;\n(.*?)\n\\\.", content, re.DOTALL)
    if type_copy_match:
        lines = type_copy_match.group(1).split('\n')
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 5:
                try:
                    tid = int(parts[0])
                    name = parts[1]
                    # Robust JSON parsing for tasks
                    raw_tasks = parts[4]
                    tasks = []
                    if raw_tasks != '\\N' and not raw_tasks.startswith('Z0FB'):
                        try:
                            # Handle some escaping if necessary, but usually tab-separated is clean
                            tasks = json.loads(raw_tasks)
                        except:
                            # Try again with some basic cleaning if needed
                            pass
                    type_data[tid] = {"name": name, "tasks": tasks}
                except:
                    pass

    # 2. Extract integrations (instances)
    instance_data = []
    instance_copy_match = re.search(r"COPY public\.integrations .*?FROM stdin;\n(.*?)\n\\\.", content, re.DOTALL)
    if instance_copy_match:
        lines = instance_copy_match.group(1).split('\n')
        for line in lines:
            parts = line.split('\t')
            if len(parts) >= 6:
                try:
                    iid = int(parts[0])
                    iname = parts[1]
                    tid = int(parts[2])
                    active = parts[5] == 't'
                    if active:
                        instance_data.append({"id": iid, "name": iname, "type_id": tid})
                except:
                    pass

    # 3. Build optimized registry
    registry = {}
    for inst in instance_data:
        tinfo = type_data.get(inst["type_id"])
        if tinfo:
            type_name = tinfo["name"]
            if type_name not in registry:
                registry[type_name] = {
                    "integration_id": inst["id"], # Use the first active instance found
                    "type_name": type_name,
                    "tasks": []
                }
            
            # Add tasks (focusing on actions or first few checks)
            for t in tinfo["tasks"]:
                # Only add if it's an action or if we have few tasks
                if t.get("category") == "action" or len(registry[type_name]["tasks"]) < 5:
                    registry[type_name]["tasks"].append({
                        "name": t["name"],
                        "display_name": t.get("display_name", t["name"]),
                        "parameters": [p["name"] for p in t.get("parameters", []) if p.get("required")]
                    })
    
    return registry

if __name__ == "__main__":
    sql_path = "/Users/sarangmehta/Desktop/workflow_agentic/data_dump/workflow_db.sql"
    if os.path.exists(sql_path):
        reg = parse_sql_dump(sql_path)
        # Sort and print a readable summary
        print("### AVAILABLE INTEGRATIONS REGISTRY")
        for tname, info in sorted(reg.items()):
            print(f"- {tname} (ID: {info['integration_id']})")
            for task in info["tasks"]:
                params = ", ".join(task["parameters"])
                print(f"  * Task: {task['name']} ('{task['display_name']}') | Mandatory Params: [{params}]")
    else:
        print(f"File not found: {sql_path}")
