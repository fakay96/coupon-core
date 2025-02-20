import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

// Utility function to merge Tailwind CSS classes with conditional class names
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Function to format a number as currency with two decimal places
export const formatCurrency = (amount: number) => {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  })
    .format(amount)
    .replace(",", ".");
};

// Function to format a number as currency without decimal places
export const formatCurrencyNormal = (amount: number) => {
  return new Intl.NumberFormat("de-DE", {
    style: "currency",
    currency: "EUR",
    maximumFractionDigits: 0,
  })
    .format(amount)
    .replace(",", ".");
};
