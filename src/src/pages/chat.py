# Standard library imports
import asyncio
import json
import os
import pathlib
import sys
import time
from time import sleep

# Third-party imports
import streamlit as st
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from dotenv import load_dotenv
from streamlit_option_menu import option_menu

# Semantic Kernel imports
from semantic_kernel import Kernel
from semantic_kernel.agents import AgentGroupChat, ChatCompletionAgent
from semantic_kernel.agents.strategies import (
    KernelFunctionSelectionStrategy,
    KernelFunctionTerminationStrategy,
)
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from semantic_kernel.contents import ChatHistoryTruncationReducer
from semantic_kernel.functions import KernelFunctionFromPrompt

# Application-specific imports
from app import (
    create_kernel,
    get_agent_prompts,
    AGENT_NAMES,
)
from plugins.legal_compliance_plugin import LegalCompliancePlugin
from plugins.vendor_evaluation_plugin import VendorEvaluationPlugin
from plugins.market_intelligence_plugin import MarketIntelligencePlugin
# from speech import transcribe_real_time_audio

# Custom config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
st.set_page_config(layout="wide")

# Load environment variables
load_dotenv()

# Function to load CSS styles from a file
def load_css(file_name):  
    with open(file_name) as f:  
        st.html(f"<style>{f.read()}</style>")

css_path = pathlib.Path("style.css")
load_css(css_path)

legal_policy_index = os.getenv("LEGAL_POLICY_INDEX")
supplier_insights_index = os.getenv("SUPPLIER_INDEX")
# Function to initialize the chat system
async def initialize_chat():

    kernel = create_kernel()
    prompt_instructions = get_agent_prompts()
    rfp_summary = st.session_state.rfp_summary_ready
    proposal_summary = st.session_state.vendor_summary_ready
    market_intelligence_dataset = os.path.join(os.path.dirname(__file__), "..", "documents", "market-intelligence.json")
    market_intelligence_dataset = os.path.abspath(market_intelligence_dataset)

    ###########################################################################################

    # For Legal Compliance Agent...
    legal_search_client = SearchClient(endpoint=os.environ.get("AZURE_AI_SEARCH_ENDPOINT"), 
                                       index_name=legal_policy_index, 
                                       credential=AzureKeyCredential(os.environ.get("AZURE_AI_SEARCH_API_KEY")))                      
    legal_compliance_plugin = LegalCompliancePlugin(search_client=legal_search_client, vendor_legal_summary=proposal_summary.get("legal_summary", ""))
    policy_context = await legal_compliance_plugin.check_compliance()

    # For Vendor Evaluation Agent...
    vendor_search_client = SearchClient(endpoint=os.environ.get("AZURE_AI_SEARCH_ENDPOINT"), 
                                          index_name=supplier_insights_index, 
                                          credential=AzureKeyCredential(os.environ.get("AZURE_AI_SEARCH_API_KEY")))
    vendor_evaluation_plugin = VendorEvaluationPlugin(search_client=vendor_search_client, vendor_name=proposal_summary.get("vendor_name", "Unknown Vendor"))
    vendor_insights = await vendor_evaluation_plugin.get_vendor_insights()

    # For Market Intelligence Agent...
    market_intelligence_plugin = MarketIntelligencePlugin(market_intelligence_dataset)
    market_insights = market_intelligence_plugin.get_market_insights("Cloud Computing")

    ###########################################################################################

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

    ###########################################################################################

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
    return chat


# Initialize session state for chat
if "session_uid" not in st.session_state:
    st.warning("❌ No session UID found! Redirecting to home page...")
    sleep(2)
    st.switch_page("main.py")  # Redirect to home page
    
if "chat" not in st.session_state:
    st.session_state.chat = None
if "responses" not in st.session_state:
    st.session_state.responses = []


st.markdown("""
    <style>
        .st-emotion-cache-13g75r2 {
            display: flex;
            justify-content: center;  /* Centers horizontally */
            align-items: center;      /* Centers vertically */
            text-align: center;
            width: 100%;              /* Ensures it spans full width */
            height: 100%;             /* Adjust based on parent */
        }
    </style>
""", unsafe_allow_html=True)

container = st.container(border=True)

with st.sidebar:
    selected = option_menu(
        menu_title="Microsoft",
        options=["chat", "Summaries", "About"],
        icons=["chat", "book", "info-circle"],
        menu_icon="microsoft",
        default_index=0,
    )



if selected == "Summaries":
    tab1, tab2 = st.tabs(["RFP", "Vendor Proposal"])
    with tab1:
        if st.session_state.rfp_summary_ready:
            st.subheader("📄")
            st.write(st.session_state.rfp_summary_ready)

    with tab2:
        if st.session_state.vendor_summary_ready:
            st.subheader("📄 ")
            st.write(st.session_state.vendor_summary_ready)

# Define agent logos (ensures correct representation)
AGENT_LOGOS = {
    "RFPCompliance": "📜",  
    "LegalCompliance": "⚖️",  
    "VendorEvaluation": "🏢",  
    "MarketIntelligence": "📊",  
    "NegotiationStrategy": "🤝",  
    "EvaluationReport": "📑"  
}

USER_LOGO = "https://cdn.pixabay.com/photo/2016/03/31/17/33/avatar-1293744_1280.png"
SYSTEM_LOGO = "https://cdn.pixabay.com/photo/2016/03/31/18/43/gear-1294576_1280.png"
image_path3 = os.path.join(os.path.dirname(__file__), "..", "static", "image3.png")

# Welcome message variable
WELCOME_MESSAGE = "Hello! Welcome to the Group Agent Chat System. Feel free to ask any questions and our agents will respond!"

# Function to simulate typewriter effect with a delay
def slow_stream(content, delay=0.05):
    """Streams content one character at a time with a delay."""
    for char in content:
        yield char
        time.sleep(delay)  # Adds delay to slow down streaming

lang_code = "en-US"
if selected == "chat":
    col1, col2 = st.columns([1, 8])
    with col1:
        st.image(image_path3, use_container_width=True)  # Add your logo here
    with col2:
        st.title("Agent Group Chat")
        st.markdown('''''')
    
    if st.session_state.chat is None:
        st.session_state.chat = asyncio.run(initialize_chat())

    # Show welcome message if no previous messages
    if "responses" not in st.session_state or not st.session_state.responses:
        with st.chat_message("assistant", avatar=SYSTEM_LOGO):  # Avatar can be changed
            st.markdown(f"**System:**")  
            st.markdown(WELCOME_MESSAGE)

    # Display previous responses with correct emoji mapping
    for response in st.session_state.get("responses", []):
        role = response["role"]
        content = response["content"]

        if role == "user":
            with st.chat_message("user", avatar=USER_LOGO):
                st.markdown(f"**You:**")  
                st.markdown(content)
        else:
            agent_logo = AGENT_LOGOS.get(role, "🤖")  
            with st.chat_message("assistant", avatar=agent_logo):
                st.markdown(f"**{role} Agent:**")  
                st.markdown(content)

    # Handle new user input
    prompt = st.chat_input("Enter your message:", key="chat_input")      
    
    if prompt:
        # Display the new user message with the correct format
        with st.chat_message("user", avatar=USER_LOGO):
            st.markdown(f"**You:**")
            st.markdown(prompt)

        # Append new user message correctly to session history
        st.session_state.responses.append({"role": "user", "content": prompt})
        asyncio.run(st.session_state.chat.add_chat_message(message=prompt))

        # Stream responses one by one using st.write_stream
        async def stream_agent_responses():
            async for response in st.session_state.chat.invoke():
                if response and response.name:
                    agent_name = response.name.strip()  
                    agent_logo = AGENT_LOGOS.get(agent_name, "🤖")  

                    with st.chat_message("assistant", avatar=agent_logo):
                        st.markdown(f"**{agent_name} Agent:**")  
                        st.write_stream(slow_stream(response.content, delay=0.005))  

                    st.session_state.responses.append({"role": response.name, "content": response.content})

        asyncio.run(stream_agent_responses())
        st.session_state.chat_process_running = False  # Reset the flag after processing
        st.rerun()