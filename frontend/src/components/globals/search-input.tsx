import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SearchIcon, XIcon } from "lucide-react";
import { useRef, useState } from "react";
import { useAiSearch } from "@/queries/geo-discount-queries";
import { useNavigate } from "react-router-dom";

// SearchInput component allows users to input and submit search queries.
export const SearchInput = () => {
  const [searchQuery, setSearchQuery] = useState("");
  const [value, setValue] = useState(searchQuery);
  const [searchStatus, setSearchStatus] = useState<{
    isSearching: boolean;
    currentRadius: number;
    attempts: number;
  }>({
    isSearching: false,
    currentRadius: 0,
    attempts: 0
  });
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { mutate: performSearch, isPending } = useAiSearch();

  // Handle input change event to update the value state.
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  // Handle clear button click event to reset the input value and search state.
  const handleClear = () => {
    setValue("");
    setSearchQuery("");
    setSearchStatus({
      isSearching: false,
      currentRadius: 0,
      attempts: 0
    });
    inputRef.current?.blur();
  };

  // Handle form submit event to set the search state and blur the input.
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSearchQuery(value);
    setSearchStatus({
      isSearching: true,
      currentRadius: 5.0,
      attempts: 0
    });
    inputRef.current?.blur();

    // Get user's location
    try {
      const position = await new Promise<GeolocationPosition>((resolve, reject) => {
        navigator.geolocation.getCurrentPosition(resolve, reject);
      });

      // Perform AI search with progressive radius
      performSearch({
        query: value,
        latitude: position.coords.latitude,
        longitude: position.coords.longitude,
        radius: 5.0, // Start with 5km radius
        maxRadius: 50.0, // Expand up to 50km
        maxRetries: 3 // Try up to 3 times
      }, {
        onSuccess: (data: any) => {
          setSearchStatus({
            isSearching: false,
            currentRadius: data.searchRadius,
            attempts: data.attempts
          });
          
          // Navigate to results page with search results
          navigate('/dashboard/discount', {
            state: {
              searchResults: data,
              query: value,
              searchRadius: data.searchRadius,
              attempts: data.attempts
            }
          });
        },
        onError: (error: Error) => {
          console.error('Search failed:', error);
          setSearchStatus({
            isSearching: false,
            currentRadius: 0,
            attempts: 0
          });
          
          // Navigate to results page with error state
          navigate('/dashboard/discount', {
            state: {
              error: 'Search failed. Please try again.',
              query: value
            }
          });
        }
      });
    } catch (error) {
      console.error('Location error:', error);
      setSearchStatus({
        isSearching: false,
        currentRadius: 0,
        attempts: 0
      });
      
      // Navigate to results page with location error
      navigate('/dashboard/discount', {
        state: {
          error: 'Please enable location services to search for nearby deals.',
          query: value
        }
      });
    }
  };

  return (
    <div className="flex-1 flex items-center justify-center">
      <form onSubmit={handleSubmit} className="relative max-w-[670px] w-full">
        <Input
          value={value}
          onChange={handleChange}
          ref={inputRef}
          placeholder={searchStatus.isSearching 
            ? `Searching within ${searchStatus.currentRadius}km radius...` 
            : "Search for deals near you"}
          className="md:text-base placeholder:max-sm:text-[12px] placeholder:text-neutral-800 px-4 w-full border-none focus-visible:shadow-[0_1px_1px_0_rgba(65,69,73,0.3),0_1px_3px_1px_rgba(65,69,73,0.15)] bg-[#f0f4f8] rounded-full h-[38px] focus-visible:ring-0 focus:bg-white"
          disabled={isPending || searchStatus.isSearching}
        />

        {!value && (
          <Button
            type="submit"
            variant={"ghost"}
            size={"icon"}
            className="absolute right-3 top-1/2 -translate-y-1/2 [&_svg]:size-5 rounded-full"
            disabled={isPending || searchStatus.isSearching}
          >
            <SearchIcon />
          </Button>
        )}
        {value && (
          <Button
            onClick={handleClear}
            type="button"
            variant={"ghost"}
            size={"icon"}
            className="absolute right-3 top-1/2 -translate-y-1/2 [&_svg]:size-5 rounded-full"
            disabled={isPending || searchStatus.isSearching}
          >
            <XIcon />
          </Button>
        )}
      </form>
    </div>
  );
};
