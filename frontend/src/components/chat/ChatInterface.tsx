import React, { useRef, useEffect } from 'react';
import { useAiSearch, useRefineSearch } from '@/queries/geo-discount-queries';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { SearchResults } from './SearchResults';
import { useLocation, useNavigate } from 'react-router-dom';
import { useSearch } from '@/context/SearchContext';
import { Message, SearchContext } from '@/types/search';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export const ChatInterface: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { mutateAsync: search } = useAiSearch();
  const { mutateAsync: refineSearch } = useRefineSearch();
  const { state, setResults, setError, setIsSearching, addMessage } = useSearch();

  // Initialize chat with location state if available
  useEffect(() => {
    if (location.state?.initialMessage) {
      const initialMessage: Message = {
        id: Date.now().toString(),
        content: location.state.initialMessage,
        role: 'user',
        timestamp: new Date(),
      };
      addMessage(initialMessage);
      
      // If there's an error, show it as an assistant message
      if (location.state.error) {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          content: location.state.error,
          role: 'assistant',
          timestamp: new Date(),
        };
        addMessage(errorMessage);
      }
      
      // If we have a conversation_id, use it for the next message
      if (location.state.conversation_id) {
        const lastMessage = state.messages?.[state.messages.length - 1];
        if (lastMessage) {
          lastMessage.conversation_id = location.state.conversation_id;
        }
      }
    }
  }, [location.state]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [state.messages]);

  const getConversationContext = (): SearchContext => {
    // Get all user queries from the conversation
    const previousQueries = state.messages
      ?.filter(m => m.role === 'user')
      .map(m => m.content) || [];
    
    // Extract filters and preferences from previous results
    const filters = state.messages
      ?.filter(m => m.role === 'assistant' && Array.isArray(m.results) && m.results.length > 0)
      .reduce((acc, message) => {
        const results = message.results || [];
        
        // Extract price ranges
        const prices = results.map(r => r.original_price);
        const minPrice = Math.min(...prices);
        const maxPrice = Math.max(...prices);
        
        // Extract categories from descriptions
        const categories = new Set<string>();
        results.forEach(result => {
          // Extract category from description (you might want to improve this logic)
          const categoryMatch = result.description.match(/in the (\w+) category/i);
          if (categoryMatch) {
            categories.add(categoryMatch[1].toLowerCase());
          }
        });

        // Extract retailer preferences
        const retailers = new Set<string>();
        results.forEach(result => {
          retailers.add(result.retailer.name.toLowerCase());
        });

        return {
          price_range: {
            min: Math.min(acc.price_range?.min || Infinity, minPrice),
            max: Math.max(acc.price_range?.max || 0, maxPrice)
          },
          categories: Array.from(categories),
          retailers: Array.from(retailers)
        };
      }, {
        price_range: { min: Infinity, max: 0 },
        categories: [] as string[],
        retailers: [] as string[]
      });

    // Get the last assistant message to understand the current context
    const lastAssistantMessage = state.messages
      ?.filter(m => m.role === 'assistant')
      .pop();

    // Build context object
    return {
      previous_queries: previousQueries,
      filters: {
        price_range: filters.price_range,
        categories: filters.categories
      },
      current_context: lastAssistantMessage?.content,
      preferences: {
        retailers: filters.retailers
      }
    };
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.querySelector('textarea') as HTMLTextAreaElement;
    if (!input.value.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input.value,
      role: 'user',
      timestamp: new Date(),
    };

    addMessage(userMessage);
    input.value = '';
    setIsSearching(true);

    try {
      let response;
      const lastMessage = state.messages?.[state.messages.length - 1];
      
      if (lastMessage?.conversation_id) {
        // Get enhanced context for refine search
        const context = getConversationContext();
        
        // Refine existing conversation with enhanced context
        response = await refineSearch({
          conversation_id: lastMessage.conversation_id,
          query: userMessage.content,
          context
        });
      } else {
        // New search
        response = await search({
          message: userMessage.content
        });
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.message || 'I found some results for you!',
        role: 'assistant',
        timestamp: new Date(),
        hasResults: Array.isArray(response.results) && response.results.length > 0,
        results: response.results,
        conversation_id: response.conversation_id,
        type: response.type || 'conversation',
        metadata: response.metadata || {}
      };

      addMessage(assistantMessage);
      setResults(response);

      // Only navigate to results page if explicitly requested by the user
      // or if it's a search-specific query
      if (response.results && response.results.length > 0 && 
          (response.type === 'search_results' || userMessage.content.toLowerCase().includes('show me'))) {
        navigate('/dashboard/discount', {
          state: {
            searchResults: response.results,
            query: userMessage.content,
            message: response.message,
            conversation_id: response.conversation_id
          }
        });
      }
    } catch (error) {
      toast.error('Failed to process your request. Please try again.');
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'I apologize, but I encountered an error processing your request. Could you please try rephrasing your question?',
        role: 'assistant',
        timestamp: new Date(),
        type: 'error'
      };
      addMessage(errorMessage);
      setError('Failed to process your request. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const renderMessageContent = (message: Message) => {
    // Handle inappropriate content
    if (message.metadata?.is_inappropriate) {
      return (
        <div className="space-y-2">
          <p className="text-sm text-red-600">{message.content}</p>
        </div>
      );
    }

    // Handle greetings
    if (message.type === 'greeting') {
      return (
        <div className="space-y-2">
          <p className="text-sm">{message.content}</p>
          {message.metadata?.suggestions && (
            <div className="mt-4">
              <h4 className="text-sm font-semibold mb-2">You might be interested in:</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {message.metadata.suggestions.map((suggestion: string, index: number) => (
                  <Card 
                    key={index} 
                    className="p-2 hover:bg-gray-50 cursor-pointer transition-colors"
                    onClick={() => {
                      const input = document.querySelector('textarea') as HTMLTextAreaElement;
                      if (input) {
                        input.value = suggestion;
                        input.dispatchEvent(new Event('input', { bubbles: true }));
                      }
                    }}
                  >
                    <p className="text-sm text-gray-600">{suggestion}</p>
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    // Handle questions about available discounts
    if (message.type === 'question' && message.metadata?.retailers) {
      return (
        <div className="space-y-4">
          <p className="text-sm">{message.content}</p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {message.metadata.retailers.map((retailer: any) => (
              <Card 
                key={retailer.name} 
                className="overflow-hidden hover:shadow-md transition-shadow"
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg font-semibold">
                    {retailer.name}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    <p className="text-sm text-gray-600">
                      Categories: {retailer.categories.join(', ')}
                    </p>
                    <p className="text-sm text-gray-600">
                      Active Discounts: {retailer.discount_count}
                    </p>
                    <Button 
                      variant="outline" 
                      size="sm"
                      className="mt-2"
                      onClick={() => {
                        const input = document.querySelector('textarea') as HTMLTextAreaElement;
                        if (input) {
                          input.value = `Show me discounts from ${retailer.name}`;
                          input.dispatchEvent(new Event('input', { bubbles: true }));
                        }
                      }}
                    >
                      View Discounts
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      );
    }

    // Handle search results
    if (message.hasResults && message.results) {
      return (
        <div className="space-y-2">
          <p className="text-sm">{message.content}</p>
          <div className="mt-4">
            <SearchResults results={message.results} />
            <div className="mt-4 flex justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  navigate('/dashboard/discount', {
                    state: {
                      searchResults: message.results,
                      query: message.content,
                      conversation_id: message.conversation_id
                    }
                  });
                }}
              >
                View Full Results
              </Button>
            </div>
          </div>
        </div>
      );
    }

    // Handle general conversation
    return <p className="text-sm">{message.content}</p>;
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {state.messages?.map((message) => (
          <div
            key={message.id}
            className={`flex ${
              message.role === 'user' ? 'justify-end' : 'justify-start'
            }`}
          >
            <div
              className={`max-w-[80%] rounded-lg p-4 ${
                message.role === 'user'
                  ? 'bg-vividOrange text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              {renderMessageContent(message)}
            </div>
          </div>
        ))}
        {state.isSearching && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-4">
              <div className="flex space-x-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-100" />
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce delay-200" />
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={handleSubmit} className="p-4 border-t">
        <div className="flex gap-2">
          <Textarea
            placeholder="Ask about discounts..."
            className="flex-1 resize-none"
            rows={1}
          />
          <Button type="submit" disabled={state.isSearching}>
            Send
          </Button>
        </div>
      </form>
    </div>
  );
}; 