import isEmpty from "lodash/isEmpty";
import {
  discountFilters,
} from "@/constants";
import { FaHeart } from "react-icons/fa6";
import { FaRegHeart } from "react-icons/fa";
import { useEffect, useMemo, useState } from "react";
import { IoLocationSharp } from "react-icons/io5";
import { MdOutlineStar } from "react-icons/md";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import { discountApiQuery } from "@/queries/geo-discount-queries";
import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { XIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/searchDebounce";
import { DiscountItemT } from "@/types";

const DiscountPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const discount = searchParams.get("discount");
  const { data: allDiscounts } = discountApiQuery();

  // Get search results from location state
  const searchResults = location.state?.searchResults;
  const searchError = location.state?.error;
  const searchQuery = location.state?.query;
  const searchRadius = location.state?.searchRadius;
  const searchAttempts = location.state?.attempts;

  // Filter discounts based on search results or all discounts
  const filteredDiscounts = useMemo(() => {
    if (searchResults) {
      // If we have AI search results, use those
      return searchResults.results || [];
    } else if (discount) {
      // If we have a specific discount query, filter all discounts
      return allDiscounts?.filter((item: DiscountItemT) =>
        item.title.toLowerCase().includes(discount.toLowerCase())
      ) || [];
    }
    // Otherwise show all discounts
    return allDiscounts || [];
  }, [searchResults, discount, allDiscounts]);

  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl mx-auto px-4 sm:px-8">
          <SearchInputNavbar link={"/"} />
          <div className="flex-1 flex-col flex items-center justify-center py-12">
            <div className="max-w-xl text-center mx-auto flex flex-col space-y-4 mb-8">
              <div className="">
                <h1 className="font-syne capitalize font-bold text-2xl sm:text-4xl text-vividOrange max-sm:max-w-sm mx-auto">
                  {searchQuery ? `Results for "${searchQuery}"` : "Available Deals"}
                </h1>
                {searchError && (
                  <p className="text-red-500 mt-2">{searchError}</p>
                )}
                {searchRadius && (
                  <p className="text-gray-600 mt-2">
                    Found {filteredDiscounts.length} deals within {searchRadius}km radius
                    {searchAttempts > 1 && ` (after ${searchAttempts} attempts)`}
                  </p>
                )}
              </div>
            </div>
            <SearchInputBox discount={discount} />
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-screen-xl">
              {filteredDiscounts.map((item: DiscountItemT) => (
                <div
                  key={item.id}
                  className="bg-white rounded-lg shadow-md overflow-hidden"
                >
                  <div className="relative">
                    <img
                      src={item.image}
                      alt={item.title}
                      className="w-full h-48 object-cover"
                    />
                    <div className="absolute top-2 right-2">
                      <FaRegHeart className="text-white text-xl" />
                    </div>
                  </div>
                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-2">
                      <IoLocationSharp className="text-vividOrange" />
                      <span className="text-sm text-gray-600">
                        {item.location}
                      </span>
                    </div>
                    <h3 className="font-semibold text-lg mb-2">{item.title}</h3>
                    <p className="text-gray-600 text-sm mb-4">{item.description}</p>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-1">
                        <MdOutlineStar className="text-yellow-400" />
                        <span className="text-sm">{item.rating}</span>
                      </div>
                      <div className="text-right">
                        <p className="text-vividOrange font-semibold">
                          {formatCurrency(item.price)}
                        </p>
                        <p className="text-sm text-gray-500 line-through">
                          {formatCurrency(item.originalPrice)}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {isEmpty(filteredDiscounts) && !searchError && (
              <div className="text-center mt-8">
                <p className="text-gray-600">No deals found. Try a different search term.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

const SearchInputBox = ({ discount }: { discount: string | null }) => {
  const [value, setValue] = useState("");
  const debouncedSearch = useDebounce(value);
  const navigate = useNavigate();
  useEffect(() => {
    navigate(`/dashboard/discount?discount=${value}`);
  }, [debouncedSearch]);

  return (
    <div className="relative max-w-screen-md mx-auto mb-16">
      <Input
        placeholder="Search product"
        className="md:text-base placeholder:pl-7 placeholder:items-center placeholder:max-sm:text-[12px] placeholder:text-neutral-800 px-4 w-full border-none focus-visible:shadow-[0_1px_1px_0_rgba(65,69,73,0.3),0_1px_3px_1px_rgba(65,69,73,0.15)] bg-white rounded-xl h-[44px] focus-visible:ring-0 focus:bg-slate-100"
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      {!value && (
        <div className="absolute top-1/2 left-2 -translate-y-1/2 bg-vividOrange p-2 rounded-full">
          <img src="/images/search.svg" className="!size-3 text-white " />
        </div>
      )}
      {(value || discount) && (
        <div
          onClick={() => {
            setValue("");
            navigate(`/dashboard`);
          }}
          className="absolute top-1/2 right-2 -translate-y-1/2 hover:bg-slate-200 p-1 rounded-full"
        >
          <XIcon className="" />
        </div>
      )}
    </div>
  );
};

export default DiscountPage;
