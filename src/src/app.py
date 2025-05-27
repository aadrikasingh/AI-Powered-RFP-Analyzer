import json
import os

from jinja2 import Environment, FileSystemLoader
from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

# Define agent names
AGENT_NAMES = {
    "rfp_compliance": "RFPCompliance",
    "legal_compliance": "LegalCompliance",
    "vendor_evaluation": "VendorEvaluation",
    "market_intelligence": "MarketIntelligence",
    "negotiation_strategy": "NegotiationStrategy",
    "evaluation_report": "EvaluationReport",
}

# Function to create a kernel instance with an Azure OpenAI ChatCompletion service
def create_kernel() -> Kernel:
    """Creates a Kernel instance with an Azure OpenAI ChatCompletion service."""
    kernel = Kernel()
    kernel.add_service(service=AzureChatCompletion())
    return kernel

# Function to extract agent prompts
def get_agent_prompts() -> dict:
    """Loads agent prompts from a Jinja template."""
    # Path to the directory of app.py
    script_dir = os.path.dirname(__file__)
    env = Environment(loader=FileSystemLoader(script_dir))
    template = env.get_template("agent_prompts.jinja")
    
    try:
        return json.loads(template.render())
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] Jinja Prompt - JSON Parsing Failed: {e}")
        return {}