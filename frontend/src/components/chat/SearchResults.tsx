import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { formatCurrency } from '@/lib/utils';

interface Discount {
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

interface SearchResultsProps {
  results: Discount[];
}

export const SearchResults: React.FC<SearchResultsProps> = ({ results }) => {
  if (!results.length) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
      {results.map((discount) => (
        <Card key={discount.id} className="overflow-hidden hover:shadow-lg transition-shadow">
          <CardHeader className="pb-2">
            <CardTitle className="text-lg font-semibold line-clamp-2">
              {discount.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600 mb-2 line-clamp-2">
              {discount.description}
            </p>
            <div className="flex justify-between items-center mb-2">
              <span className="text-sm font-medium text-gray-500">
                {discount.retailer.name}
              </span>
              <span className="text-xs text-gray-500">
                {discount.retailer.location}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-lg font-bold text-vividOrange">
                  {formatCurrency(discount.discounted_price)}
                </span>
                <span className="text-sm text-gray-500 line-through">
                  {formatCurrency(discount.original_price)}
                </span>
              </div>
              <span className="text-sm font-medium text-green-600">
                {Math.round(
                  ((discount.original_price - discount.discounted_price) /
                    discount.original_price) *
                    100
                )}
                % OFF
              </span>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}; 