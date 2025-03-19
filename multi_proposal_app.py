import asyncio
import json
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from fpdf import FPDF
from jinja2 import Environment, FileSystemLoader
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (KernelFunctionSelectionStrategy, KernelFunctionTerminationStrategy,)
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import AuthorRole, ChatHistory, ChatMessageContent, ChatHistoryTruncationReducer
from semantic_kernel.functions import KernelFunctionFromPrompt

from plugins.legal_compliance_plugin import LegalCompliancePlugin
from plugins.vendor_evaluation_plugin import VendorEvaluationPlugin
from plugins.market_intelligence_plugin import MarketIntelligencePlugin

# Define agent names
AGENT_NAMES = {
    "rfp_compliance": "RFPCompliance",
    "legal_compliance": "LegalCompliance",
    "vendor_evaluation": "VendorEvaluation",
    "market_intelligence": "MarketIntelligence",
    "negotiation_strategy": "NegotiationStrategy",
    "evaluation_report": "EvaluationReport",
}

# Folder Structure
SUMMARY_FOLDER = "documents/summaries/"  # Storage for summaries
REPORTS_FOLDER = "documents/generated_reports/"  # Storage for reports
market_intelligence_dataset = "documents/market-intelligence.json"  # Storage for market intelligence dataset

# Function to create a kernel instance with an Azure OpenAI ChatCompletion service
def create_kernel() -> Kernel:
    """Creates a Kernel instance with an Azure OpenAI ChatCompletion service."""
    kernel = Kernel()
    kernel.add_service(service=AzureChatCompletion())
    return kernel

# Function to extract agent prompts
def get_agent_prompts() -> dict:
    """Loads agent prompts from a Jinja template."""
    env = Environment(loader=FileSystemLoader("."))
    template = env.get_template("agent_prompts.jinja")
    
    try:
        return json.loads(template.render())
    except json.JSONDecodeError as e:
        print(f"\n[ERROR] Jinja Prompt - JSON Parsing Failed: {e}")
        return {}

# Function to load RFP summary
def load_rfp_summary():
    rfp_summary_path = os.path.join(SUMMARY_FOLDER, "rfp_summary.txt")
    if not os.path.exists(rfp_summary_path):
        raise Exception("Missing RFP Summary.")
    with open(rfp_summary_path, "r", encoding="utf-8") as file:
        return file.read().strip()

# Function to load all vendor proposal summaries
def load_proposal_summaries():
    proposal_summary_files = [f for f in os.listdir(SUMMARY_FOLDER) if f.startswith("vendor_proposal_") and f.endswith(".json")]
    proposal_summaries = {}
    for file in proposal_summary_files:
        with open(os.path.join(SUMMARY_FOLDER, file), "r", encoding="utf-8") as f:
            try:
                proposal_summaries[file] = json.load(f)
            except json.JSONDecodeError as e:
                print(f"[ERROR] Failed to parse {file}: {e}")
    return proposal_summaries

# Function to save a report as a PDF
def save_as_pdf(filename, content):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    for line in content.split("\n"):
        pdf.cell(200, 10, txt=line, ln=True)
    pdf.output(os.path.join(REPORTS_FOLDER, filename))

# Evaluate a vendor proposal
async def evaluate_vendor(kernel, rfp_summary, proposal_summary, prompt_instructions):

    vendor_name=proposal_summary.get("vendor_name", "Unknown Vendor")
    print(f"\nAnalyzing proposal for {vendor_name}...")

    results = {}

    ##########################################################
    # For Legal Compliance Agent...
    legal_search_client = SearchClient(endpoint=os.environ.get("AZURE_AI_SEARCH_ENDPOINT"), index_name="legal-policy-index", credential=AzureKeyCredential(os.environ.get("AZURE_AI_SEARCH_API_KEY")))                      
    legal_compliance_plugin = LegalCompliancePlugin(search_client=legal_search_client, vendor_legal_summary=proposal_summary.get("legal_summary", ""))
    policy_context = await legal_compliance_plugin.check_compliance()

    # For Vendor Evaluation Agent...
    vendor_search_client = SearchClient(endpoint=os.environ.get("AZURE_AI_SEARCH_ENDPOINT"), index_name="supplier-insights-index", credential=AzureKeyCredential(os.environ.get("AZURE_AI_SEARCH_API_KEY")))
    vendor_evaluation_plugin = VendorEvaluationPlugin(search_client=vendor_search_client, vendor_name=proposal_summary.get("vendor_name", "Unknown Vendor"))
    vendor_insights = vendor_evaluation_plugin.get_vendor_insights()

    # For Market Intelligence Agent...
    market_intelligence_plugin = MarketIntelligencePlugin(market_intelligence_dataset)
    market_insights = market_intelligence_plugin.get_market_insights("Cloud Computing")
    ##########################################################

    # Create agents

    rfp_compliance_agent = ChatCompletionAgent(
        kernel=kernel,
        name=AGENT_NAMES["rfp_compliance"],
        instructions=f"{prompt_instructions['rfp_compliance']}\n\n### RFP Summary:\n{rfp_summary}\n### Proposal Summary:\n{proposal_summary.get('overall_summary', 'No overall summary provided.')}"
    )
    
    legal_compliance_agent = ChatCompletionAgent(
        kernel=kernel,
        name=AGENT_NAMES["legal_compliance"],
        instructions=f"{prompt_instructions['legal_compliance']}\n\n### Vendor Legal Summary:\n{proposal_summary.get('legal_summary', '')}\n\n### Retrieved Policy Context:\n{policy_context}"
    )
    
    vendor_evaluation_agent = ChatCompletionAgent(
        kernel=kernel,
        name=AGENT_NAMES["vendor_evaluation"],
        instructions=f"{prompt_instructions['vendor_evaluation']}\n\n### Vendor Insights:\n{vendor_insights}"
    )

    market_intelligence_agent = ChatCompletionAgent(
        kernel=kernel,
        name=AGENT_NAMES["market_intelligence"],
        instructions=f"{prompt_instructions['market_intelligence']}\n\n### Market Insights:\n{market_insights}"
    )

    negotiation_strategy_agent = ChatCompletionAgent(
        kernel=kernel,
        name=AGENT_NAMES["negotiation_strategy"],
        instructions=f"{prompt_instructions['negotiation_strategy']}"
    )
    
    evaluation_report_agent = ChatCompletionAgent(
        kernel=kernel,
        name=AGENT_NAMES["evaluation_report"],
        instructions=f"{prompt_instructions['evaluation_report']}"
    )

    agents = {
        "rfp_compliance": rfp_compliance_agent,
        "legal_compliance": legal_compliance_agent,
        "vendor_evaluation": vendor_evaluation_agent,
        "market_intelligence": market_intelligence_agent,
        "negotiation_strategy": negotiation_strategy_agent,
        "evaluation_report": evaluation_report_agent,
    }

    chat = ChatHistory()

    for agent_name, agent in agents.items():
        async for response in agent.invoke(chat):
            if response and response.content:
                # print(f"# {agent_name.upper()}\n{response.content}\n")
                results[agent_name] = response.content
    
    print(chat)

    return results

# Present the final report as a PDF
async def main():
    print("Starting Vendor Evaluation Process...")
    kernel = create_kernel()
    rfp_summary = load_rfp_summary()
    proposals = load_proposal_summaries()
    prompt_instructions = get_agent_prompts()
    evaluation_results = {}

    for file_name, proposal_summary in proposals.items():
        vendor_name = proposal_summary.get("vendor_name", "Unknown Vendor")
        evaluation_results[vendor_name] = await evaluate_vendor(kernel, rfp_summary, proposal_summary, prompt_instructions)
    
    print("\nGenerating final report comparing all proposals...")
    final_report = "Final Vendor Comparison:\n\n"
    for vendor, results in evaluation_results.items():
        final_report += f"Vendor: {vendor}\n\n"
        for section, content in results.items():
            final_report += f"## {section.upper()}\n{content}\n\n"
    
    # save_as_pdf("Final_Report.pdf", final_report)
    
    print("Evaluation complete. Reports generated.")
    print("Do you have feedback? [Yes] [No]")
    
if __name__ == "__main__":
    asyncio.run(main())