from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery, VectorFilterMode, QueryType, QueryCaptionType, QueryAnswerType

class LegalCompliancePlugin:
    """
    Plugin to assess vendor legal compliance by retrieving relevant policies as per the vendor proposal's legal summary.
    """

    def __init__(self, search_client: SearchClient, vendor_legal_summary: str):
        """
        Initialize the Legal Compliance Plugin.

        :param search_client: Azure AI Search client instance.
        :param vendor_legal_summary: The legal-related section of the vendor proposal.
        """
        self.search_client = search_client
        self.vendor_legal_summary = vendor_legal_summary

    async def check_compliance(self) -> str:
        """
        Perform legal compliance check for a given vendor's legal summary.

        :param vendor_legal_summary: The legal-related section of the vendor proposal.
        :return: Retrieved legal policy context.
        """

        # Retrieve policy documents from the Azure AI Search index
        vector_query = VectorizableTextQuery(
            text=self.vendor_legal_summary,
            k_nearest_neighbors=50,
            fields="text_vector",
            exhaustive=True
        )

        results = self.search_client.search(
            search_text=self.vendor_legal_summary,
            vector_queries=[vector_query],
            select=["chunk"], 
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="legal-policy-index-semantic-configuration",
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=5
        )

        # Extract retrieved policy content for context
        policy_context = "\n\n".join([doc["chunk"] for doc in results])

        if not policy_context:
            return "No relevant legal policies found. Ensure the policies are indexed correctly."

        return policy_context