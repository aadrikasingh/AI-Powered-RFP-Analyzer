import json
import os

class MarketIntelligencePlugin:
    """
    Plugin to retrieve market intelligence insights based on industry data.
    """

    def __init__(self, dataset_path: str):
        """
        Initialize the Market Intelligence Plugin.

        :param dataset_path: Path to the static JSON dataset.
        """
        self.dataset_path = dataset_path
        self.market_data = self._load_market_data()

    def _load_market_data(self):
        """
        Loads market intelligence data from the JSON dataset.
        """
        if not os.path.exists(self.dataset_path):
            print(f"Market intelligence dataset not found at {self.dataset_path}")
            return {}

        try:
            with open(self.dataset_path, "r", encoding="utf-8") as file:
                return json.load(file).get("industries", {})
        except json.JSONDecodeError as e:
            print(f"Failed to parse market intelligence dataset: {e}")
            return {}

    def get_market_insights(self, industry: str):
        """
        Retrieves market insights for the specified industry.

        :param industry: The industry name to look up.
        :return: A structured market intelligence report.
        """
        industry_data = self.market_data.get(industry, None)

        if not industry_data:
            return f"No market intelligence data available for {industry}."

        insights = (
            f"### Market Intelligence Report for {industry}\n\n"
            f"**Industry Trends:**\n- " + "\n- ".join(industry_data["trends"]) + "\n\n"
            f"**Competitor Insights:**\n- " + "\n- ".join(industry_data["competitor_insights"]) + "\n\n"
            f"**Supply Chain Risks:**\n- " + "\n- ".join(industry_data["supply_chain_risks"]) + "\n\n"
            f"**Regulatory Changes:**\n- " + "\n- ".join(industry_data["regulatory_changes"]) + "\n"
        )

        return insights