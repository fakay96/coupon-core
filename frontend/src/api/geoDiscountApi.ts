import axiosInstance from "@/api/axiosClient";
import { AxiosError } from 'axios';

/**
 * Fetches all available discounts from the system
 * @returns Promise containing discount data
 * @throws {ApiError} Backend API error response
 */
export const discountApi = async () => {
  try {
    const response = await axiosInstance.get("/api/geodiscounts/v1/discounts/");
    return response.data;
  } catch (error) {
    if (error instanceof AxiosError && error.response?.data) {
      console.error('Discount API Error:', error.response.data);
      throw error.response.data;
    }
    throw error;
  }
};

/**
 * Performs an AI-powered search for discounts with progressive radius expansion
 * @param {Object} params - Search parameters
 * @param {string} params.query - The search query
 * @param {number} params.latitude - User's latitude
 * @param {number} params.longitude - User's longitude
 * @param {number} params.radius - Initial search radius in kilometers
 * @param {number} params.maxRadius - Maximum search radius in kilometers
 * @param {number} params.maxRetries - Maximum number of retry attempts
 * @returns Promise containing search results
 * @throws {ApiError} Backend API error response
 */
export const aiSearchApi = async (params: {
  query: string;
  latitude: number;
  longitude: number;
  radius?: number;
  maxRadius?: number;
  maxRetries?: number;
}) => {
  const {
    query,
    latitude,
    longitude,
    radius = 5.0,
    maxRadius = 50.0,
    maxRetries = 3
  } = params;

  let currentRadius = radius;
  let attempts = 0;
  let lastError: any = null;

  while (attempts < maxRetries && currentRadius <= maxRadius) {
    try {
      const response = await axiosInstance.post("/api/geodiscounts/v1/discounts/search/", {
        message: query,
        latitude,
        longitude,
        radius: currentRadius
      });

      // If we got results, return them
      if (response.data?.results?.length > 0) {
        return {
          ...response.data,
          searchRadius: currentRadius,
          attempts: attempts + 1
        };
      }

      // If no results, expand radius and try again
      currentRadius *= 2;
      attempts++;
    } catch (error) {
      lastError = error;
      if (error instanceof AxiosError && error.response?.data) {
        console.error('AI Search API Error:', error.response.data);
        // If it's a server error, don't retry
        if (error.response.status >= 500) {
          throw error.response.data;
        }
      }
      attempts++;
    }
  }

  // If we've exhausted all retries, throw the last error or return empty results
  if (lastError) {
    throw lastError;
  }

  return {
    results: [],
    searchRadius: currentRadius,
    attempts,
    message: "No results found after expanding search radius"
  };
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