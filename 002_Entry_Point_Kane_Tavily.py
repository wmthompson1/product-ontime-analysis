# check if Tavily can be accessed
import os
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.tools import Tool

#from google.colab import userdata
# os.environ["TAVILY_API_KEY"] = secrets.get('TAVILY_API_KEY')

search_tavily = TavilySearchResults()

search_tool = Tool.from_function(
    name = "Tavily",
    func=search_tavily,
    description="Useful for browsing information from the Internet about current events, or information you are unsure of."
)