import axiosInstance from "@/api/axiosClient";
import { AxiosError } from 'axios';

/**
 * Interface for search parameters
 */
interface SearchParams {
  message: string;
}

/**
 * Interface for refinement parameters
 */
interface RefinementParams {
  conversation_id: string;
  query: string;
  context?: {
    previous_queries?: string[];
    filters?: {
      price_range?: { min: number; max: number };
      categories?: string[];
      distance?: number;
    };
  };
}

/**
 * Interface for conversation message
 */
interface ConversationMessage {
  message: string;
  conversation_id?: string;
}

/**
 * Interface for conversation response
 */
export interface ConversationResponse {
  type: 'greeting' | 'conversation' | 'search_results' | 'searching' | 'error' | 'clarification_needed' | 'question';
  message: string;
  message_id: string;
  conversation_id: string;
  results?: any[];
  suggestions?: string[];
  context?: any;
  search_id?: string;
  retailers?: Array<{
    name: string;
    categories: string[];
    discount_count: number;
  }>;
  follow_up_questions?: string[];
  messages?: Array<{
    id: string;
    content: string;
    role: 'user' | 'assistant';
    message_type: string;
    created_at: string;
    metadata?: {
      results?: any[];
      suggestions?: string[];
      retailers?: Array<{
        name: string;
        categories: string[];
        discount_count: number;
      }>;
      follow_up_questions?: string[];
    };
  }>;
}

/**
 * Interface for conversation list response
 */
interface ConversationListResponse {
  conversations: Array<{
    id: string;
    status: string;
    messages: Array<{
      id: string;
      content: string;
      role: 'user' | 'assistant';
      message_type: string;
      created_at: string;
    }>;
    created_at: string;
    updated_at: string;
  }>;
  total_count: number;
}

/**
 * Fetches all available discounts from the system
 * @returns Promise containing discount data
 * @throws {ApiError} Backend API error response
 */
export const discountApi = async () => {
  try {
    const response = await axiosInstance.post("/api/geodiscounts/v1/discounts/search/", {
      message: "Show me all available discounts"
    });
    return response.data.results || [];
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Discount API Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Performs an AI-powered search for discounts
 * @param {SearchParams} params - Search parameters
 * @param {string} params.message - The search message
 * @returns Promise containing search results
 * @throws {ApiError} Backend API error response
 */
export const aiSearchApi = async (params: SearchParams) => {
  try {
    const response = await axiosInstance.post("/api/geodiscounts/v1/discounts/search/", {
      message: params.message
    });

    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('AI Search API Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Retrieves all discount categories available in the system
 * @returns Promise containing category data
 * @throws {ApiError} Backend API error response
 */
export const categoriesApi = async () => {
  try {
    const response = await axiosInstance.get("/api/geodiscounts/v1/discounts/categories/");
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Categories API Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Fetches nearby discounts based on user's location
 * @returns Promise containing nearby discount data
 * @throws {ApiError} Backend API error response
 */
export const nearbyApi = async () => {
  try {
    const response = await axiosInstance.get("/api/geodiscounts/v1/discounts/nearby/");
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Nearby API Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Retrieves information about a specific retailer
 * @param {string} id - The unique identifier of the retailer
 * @returns Promise containing retailer data
 * @throws {ApiError} Backend API error response
 */
export const specificRetailerApi = async (id: string) => {
  try {
    const response = await axiosInstance.get(`/api/geodiscounts/v1/retailers/${id}`);
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Specific Retailer API Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Refines search based on conversation context
 * @param {RefinementParams} params - Refinement parameters
 * @param {string} params.conversation_id - The conversation ID to refine
 * @param {string} params.query - The refinement query
 * @param {Object} [params.context] - Optional context for refinement
 * @param {string[]} [params.context.previous_queries] - Previous search queries
 * @param {Object} [params.context.filters] - Optional filters to apply
 * @param {Object} [params.context.filters.price_range] - Price range filter
 * @param {string[]} [params.context.filters.categories] - Category filters
 * @param {number} [params.context.filters.distance] - Distance filter
 * @returns Promise containing refined search results
 * @throws {ApiError} Backend API error response
 */
export const refineSearchApi = async (params: RefinementParams) => {
  try {
    const response = await axiosInstance.post("/api/geodiscounts/v1/discounts/refine/", params);
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Refine Search API Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Sends a message in the conversational interface
 * @param {ConversationMessage} params - Message parameters
 * @param {string} params.message - The message to send
 * @param {string} [params.conversation_id] - Optional conversation ID
 * @returns Promise containing conversation response
 * @throws {ApiError} Backend API error response
 */
export const sendConversationMessage = async (params: ConversationMessage): Promise<ConversationResponse> => {
  try {
    const url = params.conversation_id 
      ? `/api/geodiscounts/v1/conversations/${params.conversation_id}/messages/`
      : '/api/geodiscounts/v1/conversations/messages/';
    
    const response = await axiosInstance.post(url, {
      message: params.message
    });
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Conversation Message Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Gets a list of user's conversations
 * @returns Promise containing list of conversations
 * @throws {ApiError} Backend API error response
 */
export const getConversations = async (): Promise<ConversationListResponse> => {
  try {
    const response = await axiosInstance.get('/api/geodiscounts/v1/conversations/');
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Get Conversations Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Gets a specific conversation by ID
 * @param {string} conversationId - The conversation ID
 * @returns Promise containing conversation details
 * @throws {ApiError} Backend API error response
 */
export const getConversation = async (conversationId: string): Promise<ConversationResponse> => {
  try {
    const response = await axiosInstance.get(`/api/geodiscounts/v1/conversations/${conversationId}/`);
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Get Conversation Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Updates a conversation's status (archive/delete)
 * @param {string} conversationId - The conversation ID
 * @param {'archive' | 'delete'} action - The action to perform
 * @returns Promise containing update status
 * @throws {ApiError} Backend API error response
 */
export const updateConversationStatus = async (conversationId: string, action: 'archive' | 'delete'): Promise<{ status: string }> => {
  try {
    const response = await axiosInstance.patch(`/api/geodiscounts/v1/conversations/${conversationId}/`, {
      action
    });
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Update Conversation Status Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};