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