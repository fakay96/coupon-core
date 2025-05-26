export interface Discount {
  id: string;
  title: string;
  description: string;
  original_price: number;
  discounted_price: number;
  retailer: {
    name: string;
    location: string;
  };
}

export interface SearchResult {
  id: string;
  title: string;
  description: string;
  original_price: number;
  discounted_price: number;
  retailer: {
    name: string;
    location: string;
  };
}

export interface SearchContext {
  previous_queries: string[];
  filters: {
    price_range?: {
      min: number;
      max: number;
    };
    categories: string[];
  };
  current_context?: string;
  preferences: {
    retailers: string[];
  };
}

export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  hasResults?: boolean;
  results?: any[];
  conversation_id?: string;
  type?: 'greeting' | 'question' | 'search_results' | 'conversation' | 'error';
  metadata?: {
    suggestions?: string[];
    retailers?: Array<{
      name: string;
      categories: string[];
      discount_count: number;
    }>;
    is_inappropriate?: boolean;
    greeting_type?: 'time_based' | 'simple';
    time_of_day?: string;
    question_type?: 'available_discounts' | 'general' | 'specific';
    is_general_inquiry?: boolean;
    [key: string]: any;
  };
}

export interface SearchState {
  query: string;
  results: any[];
  message: string;
  messages: Message[];
  conversation_id?: string;
  error?: string;
  isSearching: boolean;
} 