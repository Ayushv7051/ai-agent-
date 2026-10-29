"""
Broker Interface Adapter (Scaffold for V8).
Real-money broker integrations strictly require multi-party explicit human confirmation.
"""
def execute_broker_order(*args, **kwargs):
    raise PermissionError("Real-money broker execution is strictly prohibited in V1.")
