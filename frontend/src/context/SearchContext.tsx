import React, { createContext, useContext, useReducer, ReactNode } from 'react';
import { SearchState, Message } from '@/types/search';

// Define the response type from the API
interface SearchResponse {
  results: any[];
  message: string;
  conversation_id?: string;
  type?: string;
  metadata?: any;
}

interface SearchContextType {
  state: SearchState;
  setQuery: (query: string) => void;
  setResults: (results: SearchResponse) => void;
  setError: (error: string) => void;
  setIsSearching: (isSearching: boolean) => void;
  addMessage: (message: Message) => void;
  clearSearch: () => void;
}

const initialState: SearchState = {
  query: '',
  results: [],
  message: '',
  messages: [],
  isSearching: false,
};

type SearchAction =
  | { type: 'SET_QUERY'; payload: string }
  | { type: 'SET_RESULTS'; payload: SearchResponse }
  | { type: 'SET_ERROR'; payload: string }
  | { type: 'SET_SEARCHING'; payload: boolean }
  | { type: 'ADD_MESSAGE'; payload: Message }
  | { type: 'CLEAR_SEARCH' };

const searchReducer = (state: SearchState, action: SearchAction): SearchState => {
  switch (action.type) {
    case 'SET_QUERY':
      return { ...state, query: action.payload };
    case 'SET_RESULTS':
      return {
        ...state,
        results: action.payload.results,
        message: action.payload.message,
        conversation_id: action.payload.conversation_id,
        error: undefined,
      };
    case 'SET_ERROR':
      return { ...state, error: action.payload, isSearching: false };
    case 'SET_SEARCHING':
      return { ...state, isSearching: action.payload };
    case 'ADD_MESSAGE':
      return { ...state, messages: [...state.messages, action.payload] };
    case 'CLEAR_SEARCH':
      return initialState;
    default:
      return state;
  }
};

const SearchContext = createContext<SearchContextType | undefined>(undefined);

export const SearchProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(searchReducer, initialState);

  const setQuery = (query: string) => {
    dispatch({ type: 'SET_QUERY', payload: query });
  };

  const setResults = (results: SearchResponse) => {
    dispatch({ type: 'SET_RESULTS', payload: results });
  };

  const setError = (error: string) => {
    dispatch({ type: 'SET_ERROR', payload: error });
  };

  const setIsSearching = (isSearching: boolean) => {
    dispatch({ type: 'SET_SEARCHING', payload: isSearching });
  };

  const addMessage = (message: Message) => {
    dispatch({ type: 'ADD_MESSAGE', payload: message });
  };

  const clearSearch = () => {
    dispatch({ type: 'CLEAR_SEARCH' });
  };

  return (
    <SearchContext.Provider
      value={{
        state,
        setQuery,
        setResults,
        setError,
        setIsSearching,
        addMessage,
        clearSearch,
      }}
    >
      {children}
    </SearchContext.Provider>
  );
};

export const useSearch = () => {
  const context = useContext(SearchContext);
  if (context === undefined) {
    throw new Error('useSearch must be used within a SearchProvider');
  }
  return context;
}; 