# Import libraries
import os
import json
from dotenv import load_dotenv
from openai import AzureOpenAI 
from pydantic import BaseModel
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import AnalyzeDocumentRequest

# Load environment variables
load_dotenv(override=True)
endpoint=os.environ["AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"]
key=os.environ["AZURE_DOCUMENT_INTELLIGENCE_API_KEY"]
azure_openai_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY", "") if len(os.getenv("AZURE_OPENAI_API_KEY", "")) > 0 else None
azure_openai_chat_deployment = os.environ["AZURE_OPENAI_CHAT_DEPLOYMENT_NAME"]

# Set up clients
document_intelligence_client  = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))
openai_client = AzureOpenAI(azure_endpoint=azure_openai_endpoint, api_key=azure_openai_key, api_version="2024-10-21",)

# Analyze the document layout
def analyze_document(file_path: str):
    """Analyze the layout of the document using Azure Document Intelligence."""
    with open(file_path, "rb") as f:
        poller = document_intelligence_client.begin_analyze_document("prebuilt-layout", body = f)
        result_json = poller.result()
    return result_json.content

# Chunk text content
def chunk_text(content, max_model_tokens, reserved_tokens=1000):
    """Chunk the text content into smaller segments based on the token limit of the model."""
    max_tokens = max_model_tokens - reserved_tokens
    words = content.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1
        if current_length + word_length > max_tokens:
            chunks.append(" ".join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
        
    return chunks

# Summarize the chunk
def summarize_chunk(chunk, doc_type):
    """Summarize the chunk of text using the Azure OpenAI API."""
    prompts = {
        "rfp": (
                "You are summarizing a Request for Proposal (RFP). The RFP may be for any domain, and your summary should retain "
                "all critical information while ensuring clarity and organization. The summary **must be in Markdown format** "
                "with **clearly defined sections** that allow for easy comparison with vendor proposals.\n\n"
                "Ensure the summary contains the following sections:\n"
                "- **General Information** (Must include: Issued by, Release Date, Proposal Submission Deadline)\n"
                "- **Purpose** (Clearly state the objective of the RFP)\n"
                "- **Technical Requirements** (List any technical criteria, integrations, security expectations, or compliance frameworks)\n"
                "- **Functional Requirements** (Outline required features, user functionalities, and system expectations)\n"
                "- **Legal & Compliance Requirements** (Ensure ALL compliance-related information is included with proper section headers)\n"
                "- **Financial & Support Requirements** (Capture vendor financial stability expectations, SLA conditions, support availability)\n"
                "- **Evaluation Criteria** (Clearly highlight weightage factors if mentioned in the document)\n"
                "- **Submission Requirements** (Specify deadline, format, and proposal structure if provided)\n\n"
                "### Formatting Guidelines:\n"
                "- Use **bold headings** (##, ###) for section titles.\n"
                "- Preserve important **bullet points** and subpoints.\n"
                "- Ensure all compliance-related areas are clearly marked (e.g., Legal & Compliance).\n"
                "- If weightage is present in the RFP, **retain numerical evaluation weightage in the criteria section**.\n"
                "- If any section is missing in the document, **do not remove the section but note its absence**.\n"
                "Maintain the structure **even if some details are missing**, ensuring that missing sections are marked as 'Not specified in the RFP.'"
        ),
        "proposal": (
            "You are summarizing a vendor proposal. Extract all key details that may be required to evaluate the proposal comprehensively. "
            "Your summary must capture:\n"
            "- **Vendor Name**: The official name of the vendor.\n"
            "- **Legal Summary**: Key compliance, security, and regulatory commitments, including adherence to standards such as ISO 27001, SOC 2, GDPR, HIPAA, or any other relevant frameworks.\n"
            "- **Overall Summary**: A detailed overview of the proposal, including:\n"
            "  - **Solution Offering**: Describe the product or service being proposed, including key features and differentiators.\n"
            "  - **Security & Compliance**: Highlight encryption methods, data protection policies, and adherence to compliance frameworks.\n"
            "  - **Service-Level Agreements (SLA)**: Include response times, uptime guarantees, and escalation procedures.\n"
            "  - **Implementation Approach**: Summarize the deployment process, estimated timeline, and key milestones.\n"
            "  - **Financials & Pricing**: Capture pricing models (subscription-based, per-user cost, or fixed fee), licensing terms, and any hidden costs.\n"
            "  - **Support & Customer Success**: Describe support models, availability (24/7, business hours), and dedicated account management options.\n"
            "  - **Past Performance & References**: Highlight past client engagements, case studies, or success stories that validate the vendor’s capabilities.\n\n"
            "The **overall_summary** must include all major aspects of the proposal, ensuring the summary remains detailed and useful for decision-making.\n"
            "Do not omit any critical financial, security, or SLA details even if they are not explicitly requested in the proposal document.\n"
            "If certain details are missing from the proposal, note them as 'Not specified in the proposal' instead of omitting them.\n\n"
        )
    }

    class VendorProposalSummary(BaseModel):
        vendor_name: str
        legal_summary: str
        overall_summary: str

    if doc_type=='rfp':
        messages = [{"role": "system", "content": [{"type": "text", "text": f"{prompts[doc_type]}\n\n{chunk}"}]}]
    
        completion = openai_client.chat.completions.create(
            model=azure_openai_chat_deployment,  
            messages=messages,
            max_tokens=1000,) 

        result = completion.choices[0].message.content

    elif doc_type=='proposal':
        messages = [{"role": "system", "content": [{"type": "text", "text": f"{prompts[doc_type]}\n\n{chunk}"}]}]
    
        completion = openai_client.beta.chat.completions.parse(
            model=azure_openai_chat_deployment,  
            messages=messages,
            response_format=VendorProposalSummary,
            max_tokens=1000,) 

        result = completion.choices[0].message.content
        
    return result

# Save summary
def save_summary(summary, file_path, doc_type):
    """Save the generated summary in the appropriate format."""
    output_path = os.path.splitext(file_path)[0]

    if doc_type == "rfp":
        with open(f"{output_path}/rfp_summary.txt", "w", encoding="utf-8") as f:
            f.write(summary)

    elif doc_type == "proposal":
        try:
            # Ensure that summary is a properly formatted JSON string before parsing
            if isinstance(summary, str):
                parsed_summary = json.loads(summary)
            else:
                parsed_summary = summary
                
            formatted_summary = {
                "vendor_name": str(parsed_summary.get("vendor_name", "Not specified")),
                "legal_summary": str(parsed_summary.get("legal_summary", "Not specified")),
                "overall_summary": str(parsed_summary.get("overall_summary", "Not specified"))
            }

        except (json.JSONDecodeError, TypeError):
            formatted_summary = {
                "vendor_name": "Not specified",
                "legal_summary": "Not specified",
                "overall_summary": summary if isinstance(summary, str) else json.dumps(summary)
            }

        with open(f"{output_path}/vendor_proposal_summary.json", "w", encoding="utf-8") as f:
            json.dump(formatted_summary, f, indent=4, ensure_ascii=False)

def summarize_document(file_path, output_file_path, doc_type):
    """Summarize a document. If only one chunk is generated, it is used as the final summary without additional summarization."""
    analyze_result = analyze_document(file_path)
    chunks = chunk_text(analyze_result, 126000)

    if len(chunks) == 1:
        final_summary = summarize_chunk(chunks[0], doc_type)
    else:
        summaries = [summarize_chunk(chunk, doc_type) for chunk in chunks]
        final_summary = summarize_chunk(" ".join(summaries), doc_type)

    save_summary(final_summary, output_file_path, doc_type)

if __name__ == "__main__":
    rfp_file_path = "..RFP - Contoso.docx"
    proposal_file_path = "..Vendor Proposal - Fourth Coffee.docx"
    output_file_path = "documents/generated_summaries"

    summarize_document(rfp_file_path, output_file_path, "rfp")
    print("RFP Summary saved successfully.")

    summarize_document(proposal_file_path, output_file_path, "proposal")
    print("Vendor Proposal Summary saved successfully.")