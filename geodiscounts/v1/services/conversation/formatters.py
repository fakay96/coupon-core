"""
Response formatters for conversation service.
"""
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class SearchResponseFormatter:
    """Handles consistent formatting of search responses across the application."""
    
    def format_search_response(self, results: List[Dict], context: Dict[str, Any]) -> str:
        """Format search results into a natural language response."""
        if not results:
            return "I couldn't find any matches. Would you like to try a different search?"
            
        # Group results by match type
        exact_matches = [r for r in results if r.get('match_type') == 'exact']
        category_matches = [r for r in results if r.get('match_type') == 'category']
        related_matches = [r for r in results if r.get('match_type') == 'related_category']
        
        response_parts = []
        
        # Format exact matches
        if exact_matches:
            response_parts.append(self._format_exact_matches(exact_matches))
            
        # Format category matches
        if category_matches:
            response_parts.append(self._format_category_matches(category_matches))
            
        # Format related matches
        if related_matches:
            response_parts.append(self._format_related_matches(related_matches))
            
        return "\n\n".join(response_parts)
    
    def _format_exact_matches(self, matches: List[Dict]) -> str:
        """Format exact match results."""
        response = "Here are the best matches I found:\n"
        for r in matches[:3]:
            response += self._format_result_item(r)
        return response
    
    def _format_category_matches(self, matches: List[Dict]) -> str:
        """Format category match results."""
        response = "Here are some other items in this category:\n"
        for r in matches[:5]:
            response += self._format_result_item(r)
        return response
    
    def _format_related_matches(self, matches: List[Dict]) -> str:
        """Format related category match results."""
        response = "You might also be interested in these related items:\n"
        for r in matches[:3]:
            response += self._format_result_item(r)
        return response
    
    def _format_result_item(self, result: Dict) -> str:
        """Format a single result item."""
        item = f"- {result.get('name', 'Item')} from {result.get('retailer_name', 'nearby store')}"
        
        if result.get('price_per_unit'):
            item += f" (${result['price_per_unit']})"
        if result.get('discount_percentage'):
            item += f" - {result['discount_percentage']}% off"
        if result.get('valid_until'):
            item += f" (valid until {result['valid_until']})"
            
        return item + "\n"
    
    def format_error_response(self, error_type: str, suggestions: List[str]) -> str:
        """Format error responses consistently."""
        response = "I encountered an issue while searching. "
        
        if error_type == 'TimeoutError':
            response += "The search took too long to complete. "
        elif error_type == 'IntegrityError':
            response += "There was a problem with the search parameters. "
        else:
            response += "Let me know what you're looking for and I'll try again. "
            
        if suggestions:
            response += "\n\nYou can try:\n" + "\n".join(f"- {s}" for s in suggestions)
            
        return response 