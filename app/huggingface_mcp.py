"""
Hugging Face MCP Server Integration

This module provides a client interface to the Hugging Face MCP Server
for manufacturing semantic context and SQL generation capabilities.

The HF MCP Server provides access to:
- Model search and discovery (text-to-SQL, NLP models)
- Dataset search (manufacturing, quality control datasets)
- Paper search for research context
- AI image generation capabilities
"""

import os
import json
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

HF_MCP_URL = "https://huggingface.co/mcp"
HF_API_URL = "https://huggingface.co/api"

@dataclass
class MCPTool:
    """Represents an MCP tool definition"""
    name: str
    description: str
    input_schema: Dict[str, Any]

@dataclass 
class MCPResult:
    """Represents an MCP tool call result"""
    success: bool
    data: Any
    error: Optional[str] = None

class HuggingFaceMCPClient:
    """
    Client for interacting with the Hugging Face MCP Server.
    
    Provides methods to:
    - Search for models (especially text-to-SQL for manufacturing)
    - Search for datasets
    - Search for papers
    - Access MCP tools
    """
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the HF MCP Client.
        
        Args:
            token: Hugging Face API token. If not provided, reads from 
                   HUGGINGFACE_TOKEN environment variable.
        """
        self.token = token or os.environ.get("HUGGINGFACE_TOKEN")
        if not self.token:
            raise ValueError("HUGGINGFACE_TOKEN is required")
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        """Make a request to the HF API."""
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(
                    f"{HF_API_URL}/{endpoint}",
                    headers=self.headers,
                    params=params or {}
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP error: {e.response.status_code}"}
        except Exception as e:
            return {"error": str(e)}
    
    def search_models(
        self,
        query: str,
        task: Optional[str] = None,
        limit: int = 10,
        sort: str = "downloads",
        direction: str = "-1"
    ) -> MCPResult:
        """
        Search for models on Hugging Face Hub.
        
        Args:
            query: Search query (e.g., "text-to-sql", "manufacturing")
            task: Filter by task (e.g., "text2text-generation", "text-generation")
            limit: Maximum number of results
            sort: Sort field (downloads, likes, trending_score)
            direction: Sort direction (-1 for descending, 1 for ascending)
        
        Returns:
            MCPResult with list of matching models
        """
        params = {
            "search": query,
            "limit": limit,
            "sort": sort,
            "direction": direction,
            "full": "true"
        }
        if task:
            params["pipeline_tag"] = task
        
        result = self._make_request("models", params)
        
        if "error" in result:
            return MCPResult(success=False, data=None, error=result["error"])
        
        models = []
        for model in result if isinstance(result, list) else []:
            models.append({
                "id": model.get("id", ""),
                "author": model.get("author", ""),
                "downloads": model.get("downloads", 0),
                "likes": model.get("likes", 0),
                "pipeline_tag": model.get("pipeline_tag", ""),
                "tags": model.get("tags", [])[:10],
                "description": model.get("description", "")[:200] if model.get("description") else "",
                "url": f"https://huggingface.co/{model.get('id', '')}"
            })
        
        return MCPResult(success=True, data=models)
    
    def search_datasets(
        self,
        query: str,
        limit: int = 10,
        sort: str = "downloads"
    ) -> MCPResult:
        """
        Search for datasets on Hugging Face Hub.
        
        Args:
            query: Search query (e.g., "manufacturing", "quality control")
            limit: Maximum number of results
            sort: Sort field
        
        Returns:
            MCPResult with list of matching datasets
        """
        params = {
            "search": query,
            "limit": limit,
            "sort": sort,
            "direction": "-1",
            "full": "true"
        }
        
        result = self._make_request("datasets", params)
        
        if "error" in result:
            return MCPResult(success=False, data=None, error=result["error"])
        
        datasets = []
        for dataset in result if isinstance(result, list) else []:
            datasets.append({
                "id": dataset.get("id", ""),
                "author": dataset.get("author", ""),
                "downloads": dataset.get("downloads", 0),
                "likes": dataset.get("likes", 0),
                "tags": dataset.get("tags", [])[:10],
                "description": dataset.get("description", "")[:200] if dataset.get("description") else "",
                "url": f"https://huggingface.co/datasets/{dataset.get('id', '')}"
            })
        
        return MCPResult(success=True, data=datasets)
    
    def search_spaces(
        self,
        query: str,
        limit: int = 10,
        sort: str = "likes"
    ) -> MCPResult:
        """
        Search for Spaces on Hugging Face Hub.
        
        Args:
            query: Search query
            limit: Maximum number of results
            sort: Sort field
        
        Returns:
            MCPResult with list of matching Spaces
        """
        params = {
            "search": query,
            "limit": limit,
            "sort": sort,
            "direction": "-1",
            "full": "true"
        }
        
        result = self._make_request("spaces", params)
        
        if "error" in result:
            return MCPResult(success=False, data=None, error=result["error"])
        
        spaces = []
        for space in result if isinstance(result, list) else []:
            spaces.append({
                "id": space.get("id", ""),
                "author": space.get("author", ""),
                "likes": space.get("likes", 0),
                "sdk": space.get("sdk", ""),
                "tags": space.get("tags", [])[:10],
                "url": f"https://huggingface.co/spaces/{space.get('id', '')}"
            })
        
        return MCPResult(success=True, data=spaces)
    
    def get_model_info(self, model_id: str) -> MCPResult:
        """
        Get detailed information about a specific model.
        
        Args:
            model_id: The model ID (e.g., "defog/sqlcoder-7b-2")
        
        Returns:
            MCPResult with model details
        """
        result = self._make_request(f"models/{model_id}")
        
        if "error" in result:
            return MCPResult(success=False, data=None, error=result["error"])
        
        return MCPResult(success=True, data={
            "id": result.get("id", ""),
            "author": result.get("author", ""),
            "downloads": result.get("downloads", 0),
            "likes": result.get("likes", 0),
            "pipeline_tag": result.get("pipeline_tag", ""),
            "tags": result.get("tags", []),
            "model_card": result.get("cardData", {}),
            "siblings": [s.get("rfilename") for s in result.get("siblings", [])[:10]],
            "url": f"https://huggingface.co/{result.get('id', '')}"
        })
    
    def search_text_to_sql_models(self, limit: int = 10) -> MCPResult:
        """
        Search specifically for text-to-SQL models useful for manufacturing.
        
        Returns:
            MCPResult with list of text-to-SQL models
        """
        return self.search_models(
            query="text-to-sql sql generation",
            limit=limit,
            sort="downloads"
        )
    
    def search_manufacturing_datasets(self, limit: int = 10) -> MCPResult:
        """
        Search for manufacturing-related datasets.
        
        Returns:
            MCPResult with list of manufacturing datasets
        """
        return self.search_datasets(
            query="manufacturing quality control industrial",
            limit=limit
        )
    
    def get_mcp_tools(self) -> List[Dict[str, Any]]:
        """
        Return the list of available MCP tools for this client.
        
        These represent the capabilities exposed through the MCP interface.
        """
        return [
            {
                "name": "search_models",
                "description": "Search for machine learning models on Hugging Face Hub",
                "parameters": ["query", "task", "limit"]
            },
            {
                "name": "search_datasets",
                "description": "Search for datasets on Hugging Face Hub",
                "parameters": ["query", "limit"]
            },
            {
                "name": "search_spaces",
                "description": "Search for Hugging Face Spaces (ML apps)",
                "parameters": ["query", "limit"]
            },
            {
                "name": "get_model_info",
                "description": "Get detailed information about a specific model",
                "parameters": ["model_id"]
            },
            {
                "name": "search_text_to_sql_models",
                "description": "Find models specifically for text-to-SQL generation",
                "parameters": ["limit"]
            },
            {
                "name": "search_manufacturing_datasets",
                "description": "Find datasets related to manufacturing and quality control",
                "parameters": ["limit"]
            }
        ]


def create_hf_mcp_client() -> Optional[HuggingFaceMCPClient]:
    """
    Factory function to create a HuggingFaceMCPClient instance.
    
    Returns:
        HuggingFaceMCPClient instance or None if token not available
    """
    try:
        return HuggingFaceMCPClient()
    except ValueError:
        return None


if __name__ == "__main__":
    client = create_hf_mcp_client()
    if client:
        print("HF MCP Client initialized successfully!")
        print("\nAvailable MCP Tools:")
        for tool in client.get_mcp_tools():
            print(f"  - {tool['name']}: {tool['description']}")
        
        print("\nSearching for text-to-SQL models...")
        result = client.search_text_to_sql_models(limit=5)
        if result.success:
            for model in result.data:
                print(f"  - {model['id']} ({model['downloads']:,} downloads)")
        else:
            print(f"  Error: {result.error}")
    else:
        print("Failed to initialize HF MCP Client - check HUGGINGFACE_TOKEN")
