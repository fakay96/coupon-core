import { categoriesApi, discountApi, nearbyApi, specificRetailerApi, aiSearchApi } from "@/api/geoDiscountApi";
import { useQuery, useMutation } from "@tanstack/react-query";

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
    queryFn: async () => await discountApi(),
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
 * @param {string} params.query - The search query
 * @param {number} params.latitude - User's latitude
 * @param {number} params.longitude - User's longitude
 * @param {number} params.radius - Initial search radius in kilometers
 * @param {number} params.maxRadius - Maximum search radius in kilometers
 * @param {number} params.maxRetries - Maximum number of retry attempts
 * @returns {UseMutationResult} Mutation result containing search results
 * @throws {Error} If search fails
 * @example
 * const { mutate: search, data: results } = useAiSearch();
 */
export const useAiSearch = () => {
  return useMutation({
    mutationFn: async (params: {
      query: string;
      latitude: number;
      longitude: number;
      radius?: number;
      maxRadius?: number;
      maxRetries?: number;
    }) => await aiSearchApi(params),
  });
};
