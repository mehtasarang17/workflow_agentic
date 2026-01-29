from typing import List, Dict, Optional, Any, Literal
from pydantic import BaseModel, Field

class NodeData(BaseModel):
    label: str = Field(description="Display label of the node")
    nodeType: Literal['trigger', 'action', 'condition', 'utility'] = Field(description="Category of the node")
    actionType: Optional[str] = Field(description="Specific action type e.g., 'http_request', 'run_script'")
    config: Dict[str, Any] = Field(default_factory=dict, description="Configuration parameters for the node")

class WorkflowNode(BaseModel):
    id: str = Field(description="Unique string ID of the node")
    type: str = Field(description="React Flow node type (usually 'default' or custom)")
    data: NodeData
    position: Dict[str, int] = Field(default={"x": 0, "y": 0}, description="Visual position (calculated later)")

class WorkflowEdge(BaseModel):
    id: str = Field(description="Unique string ID of the edge")
    source: str = Field(description="Source Node ID")
    target: str = Field(description="Target Node ID")
    label: Optional[str] = Field(description="Label for the edge (e.g., 'True', 'False', 'On Success')")

class WorkflowGraph(BaseModel):
    nodes: List[WorkflowNode]
    edges: List[WorkflowEdge]
