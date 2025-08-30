# check if Tavily can be accessed
import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools import Tool

# In Replit, TAVILY_API_KEY is already available as environment variable
# No need to manually set it - it's automatically loaded from secrets

search_tavily = TavilySearchResults()

search_tool = Tool.from_function(
    name = "Tavily",
    func=search_tavily,
    description="Useful for browsing information from the Internet about current events, or information you are unsure of."
)