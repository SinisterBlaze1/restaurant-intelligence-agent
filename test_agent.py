import sys
import uuid

# Trick Python into thinking uuid_utils is already loaded 
# by mapping it to the standard, secure, built-in uuid module
sys.modules['uuid_utils'] = uuid
sys.modules['uuid_utils.compat'] = uuid

# Now your original imports can run without triggering the DLL check!
from app.agent import run_agent

query = "I want good Chinese food under 1000 rupees in Koramangala"
print(f"Query: {query}\n")
print(run_agent(query))