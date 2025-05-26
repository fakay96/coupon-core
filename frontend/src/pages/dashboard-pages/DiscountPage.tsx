import { FaRegHeart } from "react-icons/fa";
import { useEffect, useMemo, useState } from "react";
import { IoLocationSharp } from "react-icons/io5";
import { MdOutlineStar } from "react-icons/md";
import { discountApiQuery, useAiSearch } from "@/queries/geo-discount-queries";
import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { XIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/searchDebounce";
import { DiscountItemT } from "@/types";

const ThinkingAnimation = () => {
  return (
    <div className="flex items-center space-x-2 bg-white/80 backdrop-blur-sm rounded-lg p-4 shadow-lg">
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-vividOrange rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="w-2 h-2 bg-vividOrange rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="w-2 h-2 bg-vividOrange rounded-full animate-bounce"></div>
      </div>
      <span className="text-gray-600 text-sm">Searching for the best deals...</span>
    </div>
  );
};

const DiscountPage = () => {
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const discount = searchParams.get("discount");
  const { data: allDiscounts } = discountApiQuery();
  const { mutate: search, data: searchData, isPending: isSearching } = useAiSearch();

  // Get search results from location state or search data
  const searchResults = location.state?.searchResults || searchData?.results || [];
  const searchMessage = location.state?.message || searchData?.message;

  // Filter discounts based on search results or all discounts
  const filteredDiscounts = useMemo(() => {
    if (Array.isArray(searchResults) && searchResults.length > 0) {
      // If we have AI search results, use those
      return searchResults;
    } else if (discount) {
      // If we have a specific discount query, filter all discounts
      return Array.isArray(allDiscounts) ? allDiscounts.filter((item: DiscountItemT) =>
        item.title.toLowerCase().includes(discount.toLowerCase())
      ) : [];
    }
    // Otherwise show all discounts
    return Array.isArray(allDiscounts) ? allDiscounts : [];
  }, [searchResults, discount, allDiscounts]);

  // Handle initial search from location state
  useEffect(() => {
    if (location.state?.query && !searchData) {
      search({ message: location.state.query });
    }
  }, [location.state?.query, search, searchData]);

  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl mx-auto px-4 sm:px-8">
          <SearchInputNavbar link={"/"} />
          <div className="flex-1 flex-col flex items-center justify-center py-12">
            <div className="max-w-xl text-center mx-auto flex flex-col space-y-4 mb-8">
              <div className="">
                <h1 className="font-syne capitalize font-bold text-2xl sm:text-4xl text-vividOrange max-sm:max-w-sm mx-auto">
                  {discount ? `Results for "${discount}"` : "Available Deals"}
                </h1>
                {searchMessage && (
                  <p className="text-gray-600 mt-2">{searchMessage}</p>
                )}
              </div>
            </div>
            <SearchInputBox 
              discount={discount} 
              onSearch={search}
              isSearching={isSearching}
              initialQuery={location.state?.query}
            />
            {isSearching ? (
              <div className="w-full max-w-screen-xl flex justify-center mb-8">
                <ThinkingAnimation />
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 w-full max-w-screen-xl">
                {filteredDiscounts.map((item: any) => (
                  <div
                    key={item.id}
                    className="bg-white rounded-lg shadow-md overflow-hidden"
                  >
                    <div className="relative">
                      <img
                        src={item.image_url || "/images/placeholder.png"}
                        alt={item.name}
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
                          {item.retailer_name}
                        </span>
                      </div>
                      <h3 className="font-semibold text-lg mb-2">{item.name}</h3>
                      <p className="text-gray-600 text-sm mb-4">{item.description}</p>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-1">
                          <MdOutlineStar className="text-yellow-400" />
                          <span className="text-sm">{item.relevance_score || 4.5}</span>
                        </div>
                        <div className="text-right">
                          <p className="text-vividOrange font-semibold">
                            {item.discount_value}% OFF
                          </p>
                          <a 
                            href={item.product_url} 
                            target="_blank" 
                            rel="noopener noreferrer"
                            className="text-sm text-vividOrange hover:underline"
                          >
                            View Deal
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
            {filteredDiscounts.length === 0 && !isSearching && (
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

const SearchInputBox = ({ 
  discount, 
  onSearch, 
  isSearching,
  initialQuery
}: { 
  discount: string | null;
  onSearch: (params: { message: string }) => void;
  isSearching: boolean;
  initialQuery?: string;
}) => {
  const [value, setValue] = useState(initialQuery || discount || "");
  const debouncedSearch = useDebounce(value);
  const navigate = useNavigate();

  useEffect(() => {
    if (debouncedSearch) {
      navigate(`/dashboard/discount?discount=${debouncedSearch}`);
      onSearch({ message: debouncedSearch });
    }
  }, [debouncedSearch, navigate, onSearch]);

  return (
    <div className="relative max-w-screen-md mx-auto mb-16">
      <Input
        placeholder="Search product"
        className="md:text-base placeholder:pl-7 placeholder:items-center placeholder:max-sm:text-[12px] placeholder:text-neutral-800 px-4 w-full border-none focus-visible:shadow-[0_1px_1px_0_rgba(65,69,73,0.3),0_1px_3px_1px_rgba(65,69,73,0.15)] bg-white rounded-xl h-[44px] focus-visible:ring-0 focus:bg-slate-100"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        disabled={isSearching}
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
            navigate(`/dashboard/discount`);
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
