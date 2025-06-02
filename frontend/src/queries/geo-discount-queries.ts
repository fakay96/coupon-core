import { categoriesApi, nearbyApi, specificRetailerApi, aiSearchApi, refineSearchApi, discountApi } from "@/api/geoDiscountApi";
import { useQuery, useMutation } from "@tanstack/react-query";

interface SearchResponse {
  results: any[];
  message: string;
  conversation_id?: string;
  type?: string;
  metadata?: any;
  attempts?: number;
}

/**
 * Custom hook to fetch all available discounts
 * @returns {UseQueryResult} Query result containing all discount data
 * @throws {Error} If discount fetch fails
 * @example
 * const { data: discounts, isLoading } = discountApiQuery();
 */
export const discountApiQuery = () => {
  return useQuery({
    queryKey: ["discountApi"],
    queryFn: async () => {
      try {
        // Use the regular discountApi for initial load
        const response = await discountApi();
        
        // Validate response structure
        if (!response || typeof response !== 'object') {
          console.error('Invalid response structure:', response);
          return [];
        }

        // Ensure results is an array
        const results = Array.isArray(response) ? response : response.results;
        if (!Array.isArray(results)) {
          console.error('Results is not an array:', results);
          return [];
        }

        // Validate each item in results
        return results.filter(item => {
          if (!item || typeof item !== 'object') {
            console.error('Invalid item in results:', item);
            return false;
          }
          return true;
        });
      } catch (error) {
        console.error('Failed to fetch discounts:', error);
        return [];
      }
    },
    retry: 2, // Retry failed requests twice
    staleTime: 5 * 60 * 1000, // Consider data stale after 5 minutes
  });
};

/**
 * Custom hook to fetch all discount categories
 * @returns {UseQueryResult} Query result containing category data
 * @throws {Error} If categories fetch fails
 * @example
 * const { data: categories, isLoading } = categoriesApiQuery();
 */
export const categoriesApiQuery = () => {
  return useQuery({
    queryKey: ["categoriesApi"],
    queryFn: async () => await categoriesApi(),
  });
};

/**
 * Custom hook to fetch nearby discounts based on user location
 * @returns {UseQueryResult} Query result containing nearby discount data
 * @throws {Error} If nearby discounts fetch fails
 * @example
 * const { data: nearbyDiscounts, isLoading } = nearbyApiQuery();
 */
export const nearbyApiQuery = () => {
  return useQuery({
    queryKey: ["nearbyApi"],
    queryFn: async () => await nearbyApi(),
  });
};

/**
 * Custom hook to fetch specific retailer details
 * @param {string} id - The unique identifier of the retailer
 * @returns {UseQueryResult} Query result containing retailer data
 * @throws {Error} If retailer fetch fails
 * @example
 * const { data: retailer, isLoading } = specificRetailerQuery("123");
 */
export const specificRetailerQuery = (id: string) => {
  return useQuery({
    queryKey: ["specificRetailer", id],
    queryFn: async () => await specificRetailerApi(id),
  });
};

/**
 * Custom hook to perform AI-powered discount search
 * @param {Object} params - Search parameters
 * @param {string} params.message - The search message
 * @returns {UseMutationResult} Mutation result containing search results
 * @throws {Error} If search fails
 * @example
 * const { mutate: search, data: results } = useAiSearch();
 */
export const useAiSearch = () => {
  return useMutation({
    mutationFn: async (params: {
      message: string;
    }) => {
      try {
        const response = await aiSearchApi(params);
        
        // Validate response structure
        if (!response || typeof response !== 'object') {
          throw new Error('Invalid response structure');
        }

        // Ensure results is an array
        if (!Array.isArray(response.results)) {
          response.results = [];
        }

        return response as SearchResponse;
      } catch (error) {
        console.error('Search failed:', error);
        throw error;
      }
    },
  });
};

/**
 * Custom hook to refine search based on conversation context
 * @returns {UseMutationResult} Mutation result for refined search
 * @throws {Error} If search refinement fails
 * @example
 * const { mutate: refineSearch, data: refinedResults } = useRefineSearch();
 * refineSearch({
 *   conversation_id: '123',
 *   query: 'Show me more options',
 *   context: {
 *     previous_queries: ['Show me food discounts'],
 *     filters: { price_range: { min: 0, max: 50 } }
 *   }
 * });
 */
export const useRefineSearch = () => {
  return useMutation({
    mutationFn: async (params: {
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
    }) => await refineSearchApi(params),
  });
};
