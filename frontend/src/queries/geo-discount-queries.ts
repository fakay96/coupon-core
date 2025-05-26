import { categoriesApi, nearbyApi, specificRetailerApi, aiSearchApi, refineSearchApi } from "@/api/geoDiscountApi";
import { useQuery, useMutation } from "@tanstack/react-query";

/**
 * Custom hook to fetch all available discounts using AI search
 * @returns {UseQueryResult} Query result containing all discount data
 * @throws {Error} If discount fetch fails
 * @example
 * const { data: discounts, isLoading } = discountApiQuery();
 */
export const discountApiQuery = () => {
  return useQuery({
    queryKey: ["discountApi"],
    queryFn: async () => {
      const response = await aiSearchApi({
        message: "Show me all available discounts"
      });
      return response.results;
    },
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
    }) => await aiSearchApi(params),
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
