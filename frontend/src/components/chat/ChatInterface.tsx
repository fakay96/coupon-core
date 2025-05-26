import React, { useState, useRef, useEffect } from 'react';
import { useAiSearch, useRefineSearch } from '@/queries/geo-discount-queries';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { useAuth } from '@/context/authContext';
import { SearchResults } from './SearchResults';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  hasResults?: boolean;
  results?: any[];
  conversation_id?: string;
}

export const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  const { mutateAsync: search } = useAiSearch();
  const { mutateAsync: refineSearch } = useRefineSearch();

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const getConversationContext = () => {
    const previousQueries = messages
      .filter(m => m.role === 'user')
      .map(m => m.content);
    
    // Extract filters from previous results
    const filters = messages
      .filter(m => m.role === 'assistant' && m.results?.length > 0)
      .reduce((acc, message) => {
        const result = message.results?.[0];
        if (result) {
          return {
            price_range: {
              min: Math.min(acc.price_range?.min || Infinity, result.original_price),
              max: Math.max(acc.price_range?.max || 0, result.original_price)
            },
            categories: [...new Set([...(acc.categories || []), result.category])]
          };
        }
        return acc;
      }, {} as any);

    return {
      previous_queries: previousQueries,
      filters
    };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      let response;
      const lastMessage = messages[messages.length - 1];
      
      if (lastMessage?.conversation_id) {
        // Refine existing conversation
        response = await refineSearch({
          conversation_id: lastMessage.conversation_id,
          query: input,
          context: getConversationContext()
        });
      } else {
        // New search
        response = await search({
          query: input,
          latitude: user?.latitude || 0,
          longitude: user?.longitude || 0,
        });
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: response.message || 'I found some results for you!',
        role: 'assistant',
        timestamp: new Date(),
        hasResults: response.results?.length > 0,
        results: response.results,
        conversation_id: response.conversation_id
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      toast.error('Failed to process your request. Please try again.');
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: 'I apologize, but I encountered an error processing your request. Could you please try rephrasing your question?',
        role: 'assistant',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message) => (
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
              <p className="text-sm">{message.content}</p>
              {message.hasResults && message.results && (
                <div className="mt-4">
                  <SearchResults results={message.results} />
                </div>
              )}
            </div>
          </div>
        ))}
        {isTyping && (
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
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about discounts near you..."
            className="flex-1 resize-none"
            rows={1}
          />
          <Button type="submit" disabled={!input.trim() || isTyping}>
            Send
          </Button>
        </div>
      </form>
    </div>
  );
}; 