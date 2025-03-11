from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizableTextQuery, QueryType, QueryCaptionType, QueryAnswerType

class VendorEvaluationPlugin:
    """
    Plugin to assess vendor credibility by retrieving historical insights from Azure AI Search.
    """

    def __init__(self, search_client: SearchClient, vendor_name: str):
        """
        Initialize the vendor Evaluation Plugin.

        :param search_client: Azure AI Search client instance.
        :param vendor_name: Name of the vendor being evaluated.
        """
        self.search_client = search_client
        self.vendor_name = vendor_name

    async def get_vendor_insights(self) -> str:
        """
        Retrieve vendor reputation insights from the search index.
        
        :return: Retrieved historical insights about the vendor.
        """

        # Vectorize the vendor name and perform search
        vector_query = VectorizableTextQuery(
            text=self.vendor_name,
            k_nearest_neighbors=1,
            fields="text_vector",
            exhaustive=True
        )

        results = self.search_client.search(
            search_text=self.vendor_name,
            vector_queries=[vector_query],
            select=["chunk", "past_clients", "industries_served", "customer_satisfaction_avg", 
                    "financial_growth_5y", "compliance_issues", "market_growth", "bbb_accreditation",
                    "contract_disputes", "notes"],
            query_type=QueryType.SEMANTIC,
            semantic_configuration_name="supplier-insights-index-semantic-configuration",
            query_caption=QueryCaptionType.EXTRACTIVE,
            query_answer=QueryAnswerType.EXTRACTIVE,
            top=1
        )

        vendor_record = next(iter(results), None)
        
        if not vendor_record:
            return "No historical data found for this vendor. Ensure the index is correctly populated."
        
        # Format response
        insights = (
            f"### **Vendor:** {vendor_record['chunk']}\n"
            f"- **Past Clients:** {', '.join(vendor_record['past_clients'])}\n"
            f"- **Industries Served:** {', '.join(vendor_record['industries_served'])}\n"
            f"- **Customer Satisfaction:** {vendor_record['customer_satisfaction_avg']}%\n"
            f"- **Financial Growth (5y):** {vendor_record['financial_growth_5y']}\n"
            f"- **Compliance Issues:** {vendor_record['compliance_issues']}\n"
            f"- **Market Growth:** {vendor_record['market_growth']}\n"
            f"- **BBB Accreditation:** {vendor_record['bbb_accreditation']}\n"
            f"- **Contract Disputes:** {vendor_record['contract_disputes']}\n"
            f"- **Additional Notes:** {vendor_record['notes']}\n"
        )
        
        return insights