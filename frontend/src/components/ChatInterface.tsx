import React, { useState, useRef, useEffect } from 'react';
import { sendConversationMessage, getConversations, getConversation } from '@/api/geoDiscountApi';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { ScrollArea } from './ui/scroll-area';
import { Card } from './ui/card';
import { Avatar, AvatarFallback } from './ui/avatar';
import { Badge } from './ui/badge';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  type: string;
  timestamp: string;
  results?: any[];
  suggestions?: string[];
  retailers?: Array<{
    name: string;
    categories: string[];
    discount_count: number;
  }>;
  follow_up_questions?: string[];
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadConversation();
  }, []);

  const loadConversation = async () => {
    try {
      const conversations = await getConversations();
      if (conversations.conversations.length > 0) {
        const latestConversation = conversations.conversations[0];
        const conversation = await getConversation(latestConversation.id);
        if (conversation.messages) {
          setMessages(conversation.messages.map(msg => ({
            id: msg.id,
            content: msg.content,
            role: msg.role,
            type: msg.message_type,
            timestamp: msg.created_at,
            ...msg.metadata
          })));
        }
      }
    } catch (error) {
      console.error('Error loading conversation:', error);
    }
  };

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      type: 'text',
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      const response = await sendConversationMessage({
        message: input,
        conversation_id: messages[0]?.id
      });

      const assistantMessage: Message = {
        id: response.message_id,
        content: response.message,
        role: 'assistant',
        type: response.type,
        timestamp: new Date().toISOString(),
        results: response.results,
        suggestions: response.suggestions,
        retailers: response.retailers,
        follow_up_questions: response.follow_up_questions
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error sending message:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const renderMessage = (message: Message) => {
    return (
      <div
        key={message.id}
        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} mb-4`}
      >
        <div className={`flex ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-end gap-2 max-w-[80%]`}>
          <Avatar className="h-8 w-8">
            <AvatarFallback>
              {message.role === 'user' ? 'U' : 'A'}
            </AvatarFallback>
          </Avatar>
          <div className={`flex flex-col ${message.role === 'user' ? 'items-end' : 'items-start'}`}>
            <Card className={`p-3 ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted'}`}>
              <p className="text-sm">{message.content}</p>
            </Card>
            {message.type === 'search_results' && message.results && (
              <div className="mt-2 space-y-2">
                {message.results.map((result, index) => (
                  <Card key={index} className="p-3">
                    <h4 className="font-semibold">{result.name}</h4>
                    <p className="text-sm text-muted-foreground">{result.description}</p>
                    {result.price && (
                      <Badge variant="secondary" className="mt-1">
                        {result.price}
                      </Badge>
                    )}
                  </Card>
                ))}
              </div>
            )}
            {message.suggestions && message.suggestions.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-2">
                {message.suggestions.map((suggestion, index) => (
                  <Button
                    key={index}
                    variant="outline"
                    size="sm"
                    onClick={() => setInput(suggestion)}
                  >
                    {suggestion}
                  </Button>
                ))}
              </div>
            )}
            <span className="text-xs text-muted-foreground mt-1">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-[600px]">
      <ScrollArea ref={scrollRef} className="flex-1 p-4">
        {messages.map(renderMessage)}
      </ScrollArea>
      <div className="p-4 border-t">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message..."
            disabled={isLoading}
          />
          <Button onClick={handleSend} disabled={isLoading}>
            Send
          </Button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface; 