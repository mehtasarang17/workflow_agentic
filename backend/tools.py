from langchain_core.tools import tool
import random
import time

@tool
def restart_service(service_name: str, environment: str = "production"):
    """
    Restarts a specified service in the given environment.
    
    Args:
        service_name: Name of the service to restart (e.g., 'payment-api').
        environment: Target environment (default: 'production').
    """
    # Mock implementation
    time.sleep(2) # Simulate work
    if random.random() < 0.1:
         return f"Error: Failed to restart {service_name} in {environment}. Connection timed out."
    return f"Successfully restarted {service_name} in {environment}."

@tool
def check_disk_usage(host: str):
    """
    Checks disk usage on a specific host.
    
    Args:
        host: Hostname or IP address.
    """
    usage = random.randint(20, 95)
    return f"Disk usage on {host} is {usage}%."

@tool
def scale_service(service_name: str, replicas: int):
    """
    Scales a service to a specified number of replicas.
    
    Args:
        service_name: Name of the service.
        replicas: Desired number of replicas.
    """
    return f"Scaled {service_name} to {replicas} replicas."

@tool
def query_metrics(metric_name: str, duration_minutes: int = 60):
    """
    Queries metrics data.
    
    Args:
        metric_name: Name of the metric (e.g., 'cpu_usage').
        duration_minutes: Time range to query.
    """
    val = random.uniform(0, 100)
    return f"Average {metric_name} over last {duration_minutes}m was {val:.2f}."

available_tools = [restart_service, check_disk_usage, scale_service, query_metrics]
