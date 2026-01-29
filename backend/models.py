from datetime import datetime
from database import db
from sqlalchemy.dialects.postgresql import JSON, JSONB

class AdminWorkflow(db.Model):
    __tablename__ = 'admin_workflows'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    workflow_data = db.Column(db.Text, nullable=False) # JSON string or actual JSON
    category = db.Column(db.String(100), nullable=False)
    is_template = db.Column(db.Boolean, default=False)
    elevated_permissions = db.Column(JSON)
    created_by = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    execution_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AgentSession(db.Model):
    __tablename__ = 'agent_sessions'

    id = db.Column(db.Integer, primary_key=True)
    organization_id = db.Column(db.Integer, nullable=False, default=1) # Defaulting for singleton
    user_id = db.Column(db.Integer, nullable=False, default=1) # Defaulting for singleton
    status = db.Column(db.String(50))
    session_type = db.Column(db.String(50))
    ai_provider = db.Column(db.String(50), nullable=False)
    ai_model = db.Column(db.String(100), nullable=False)
    conversation_history = db.Column(db.Text, nullable=False) # JSON string
    collected_parameters = db.Column(db.Text)
    generated_workflow_id = db.Column(db.Integer)
    workflow_preview = db.Column(db.Text)
    total_tokens = db.Column(db.Integer)
    prompt_tokens = db.Column(db.Integer)
    completion_tokens = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

class ExecutionLog(db.Model):
    __tablename__ = 'execution_logs'

    id = db.Column(db.Integer, primary_key=True)
    workflow_id = db.Column(db.Integer)
    integration_id = db.Column(db.Integer)
    log_type = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    execution_time_seconds = db.Column(db.Integer)
    total_tasks = db.Column(db.Integer)
    successful_tasks = db.Column(db.Integer)
    failed_tasks = db.Column(db.Integer)
    execution_data = db.Column(db.Text)
    error_message = db.Column(db.Text)
    celery_task_id = db.Column(db.String(255))
    trigger_source = db.Column(db.String(50))
    trigger_metadata = db.Column(db.Text)

class ApiKey(db.Model):
    __tablename__ = 'api_keys'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    organization_id = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
