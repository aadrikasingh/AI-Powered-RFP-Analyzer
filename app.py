import asyncio
import json
import os

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from jinja2 import Environment, FileSystemLoader
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (KernelFunctionSelectionStrategy, KernelFunctionTerminationStrategy,)
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistoryTruncationReducer
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

# Function to load summaries (from local files)
def load_summaries():
    """Loads RFP and Vendor Proposal summaries."""
    rfp_summary_path = os.path.join(SUMMARY_FOLDER, "rfp_summary.txt")
    proposal_summary_path = os.path.join(SUMMARY_FOLDER, "vendor_proposal_summary_northwind_traders.json")
    
    if not os.path.exists(rfp_summary_path) or not os.path.exists(proposal_summary_path):
        raise Exception("Missing RFP or Proposal Summary.")

    with open(rfp_summary_path, "r", encoding="utf-8") as rfp_file:
        rfp_summary = rfp_file.read().strip()
    
    with open(proposal_summary_path, "r", encoding="utf-8") as proposal_file:
        try:
            proposal_summary = json.load(proposal_file)
        except json.JSONDecodeError as e:
            raise Exception(f"Failed to parse vendor proposal JSON: {e}")
    
    return rfp_summary, proposal_summary

async def main():
    """Main function to run the agent group chat workflow."""

    # Create a single kernel instance for all agents.
    kernel = create_kernel()

    # Extract agent prompts.
    prompt_instructions = get_agent_prompts()

    # Load summaries
    rfp_summary, proposal_summary = load_summaries()

    ##########################################################
    # For Legal Compliance Agent...
    legal_search_client = SearchClient(endpoint=os.environ.get("AZURE_AI_SEARCH_ENDPOINT"), 
                                       index_name="legal-policy-index", 
                                       credential=AzureKeyCredential(os.environ.get("AZURE_AI_SEARCH_API_KEY")))                      
    legal_compliance_plugin = LegalCompliancePlugin(search_client=legal_search_client, vendor_legal_summary=proposal_summary.get("legal_summary", ""))
    policy_context = await legal_compliance_plugin.check_compliance()

    # For Vendor Evaluation Agent...
    vendor_search_client = SearchClient(endpoint=os.environ.get("AZURE_AI_SEARCH_ENDPOINT"), 
                                          index_name="supplier-insights-index", 
                                          credential=AzureKeyCredential(os.environ.get("AZURE_AI_SEARCH_API_KEY")))
    vendor_evaluation_plugin = VendorEvaluationPlugin(search_client=vendor_search_client, vendor_name=proposal_summary.get("vendor_name", "Unknown Vendor"))
    vendor_insights = vendor_evaluation_plugin.get_vendor_insights()

    # For Market Intelligence Agent...
    market_intelligence_plugin = MarketIntelligencePlugin(market_intelligence_dataset)
    market_insights = market_intelligence_plugin.get_market_insights("Cloud Computing")

    ##########################################################
    ### Create ChatCompletionAgents using the same kernel. ###

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

    ##########################################################
    # Define a selection function to determine which agent should take the next turn.
    selection_function = KernelFunctionFromPrompt(
    function_name="selection",
    prompt=f"""
    You are responsible for selecting the next agent in the workflow.
    Examine the provided RESPONSE and choose the next participant.
    State only the name of the chosen participant without explanation.
    Never choose the participant named in the RESPONSE.

    ### Rules:
    - If the user has just started, follow this strict sequence:
      1. First, call {AGENT_NAMES["rfp_compliance"]}.
      2. Next, call {AGENT_NAMES["legal_compliance"]}.
      3. Then, call {AGENT_NAMES["vendor_evaluation"]}.
      4. Then, call {AGENT_NAMES["market_intelligence"]}.
      5. Then, call {AGENT_NAMES["negotiation_strategy"]}.
      6. Finally, call {AGENT_NAMES["evaluation_report"]}.
    - **Do NOT skip any agent in the sequence.**
    - **Each agent runs exactly ONCE but AT LEAST once during evaluation.**
    
    - After the full evaluation is complete:
      - If the user asks about **compliance issues**, select {AGENT_NAMES["legal_compliance"]}.
      - If the user asks about **vendor history, reputation, or credibility**, select {AGENT_NAMES["vendor_evaluation"]}.
      - If the user asks about **industry insights or trends**, select {AGENT_NAMES["market_intelligence"]}.
      - If the user asks about **negotiation recommendations**, select {AGENT_NAMES["negotiation_strategy"]}.
      - If the user asks about **the final report or modifications**, select {AGENT_NAMES["evaluation_report"]}.
      - If unsure, default to {AGENT_NAMES["evaluation_report"]}.

    RESPONSE:
    {{{{$lastmessage}}}}
    """,
    )

    # Define a termination function where the final agent signals completion.
    termination_keyword = "yes"
    termination_function = KernelFunctionFromPrompt(
        function_name="termination",
        prompt=f"""
       If all checks and evaluations are completed, respond 'yes'. Otherwise, respond 'no'.

        RESPONSE:
        {{{{$lastmessage}}}}
        """,
    )

    history_reducer = ChatHistoryTruncationReducer(target_count=10)

    # Create the AgentGroupChat with selection and termination strategies.
    chat = AgentGroupChat(
        agents=[rfp_compliance_agent, legal_compliance_agent, vendor_evaluation_agent, evaluation_report_agent, market_intelligence_agent, negotiation_strategy_agent],
        selection_strategy=KernelFunctionSelectionStrategy(
            initial_agent=rfp_compliance_agent,
            function=selection_function,
            kernel=kernel,
            result_parser=lambda result: (
                next(
                    (agent for agent in AGENT_NAMES.values() if agent.lower() == str(result.value[0]).strip().lower()),
                    AGENT_NAMES["evaluation_report"],
                    )
                ),
            history_variable_name="lastmessage",
            history_reducer=history_reducer,
        ),
        termination_strategy=KernelFunctionTerminationStrategy(
            agents=[evaluation_report_agent],
            function=termination_function,
            kernel=kernel,
            result_parser=lambda result: termination_keyword in str(result.value[0]).strip().lower(),
            history_variable_name="lastmessage",
            maximum_iterations=6,
            history_reducer=history_reducer,
        ),
    )

    print("Ready! Type your input, or 'exit' to quit.")

    is_complete = False
    while not is_complete:
        print()
        user_input = input("User > ").strip()
        if not user_input:
            continue

        if user_input.lower() == "exit":
            is_complete = True
            break

        if user_input.lower() == "reset":
            await chat.reset()
            print("[Conversation has been reset]")
            continue

        await chat.add_chat_message(message=user_input)

        try:
            async for response in chat.invoke():
                if response is None or not response.name:
                    continue
                print()
                print(f"# {response.name.upper()}:\n{response.content}")
        except Exception as e:
            print(f"Error during chat invocation: {e}")

        chat.is_complete = False


if __name__ == "__main__":
    asyncio.run(main())
