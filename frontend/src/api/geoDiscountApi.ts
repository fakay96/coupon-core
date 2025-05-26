import axiosInstance from "@/api/axiosClient";
import { AxiosError } from 'axios';

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
 * @param {Object} params - Search parameters
 * @param {string} params.message - The search message
 * @returns Promise containing search results
 * @throws {ApiError} Backend API error response
 */
export const aiSearchApi = async (params: {
  message: string;
}) => {
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
 * @param id - The unique identifier of the retailer
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
 * @param {Object} params - Refinement parameters
 * @param {string} params.conversation_id - The conversation ID to refine
 * @param {string} params.query - The refinement query
 * @param {Object} params.context - Optional context for refinement
 * @param {string[]} params.context.previous_queries - Previous search queries
 * @param {Object} params.context.filters - Optional filters to apply
 * @param {Object} params.context.filters.price_range - Price range filter
 * @param {string[]} params.context.filters.categories - Category filters
 * @param {number} params.context.filters.distance - Distance filter
 * @returns Promise containing refined search results
 * @throws {ApiError} Backend API error response
 */
export const refineSearchApi = async (params: {
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
}) => {
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