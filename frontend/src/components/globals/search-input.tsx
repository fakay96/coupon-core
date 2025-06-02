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
  const [isSearching, setIsSearching] = useState(false);
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
    setIsSearching(false);
    inputRef.current?.blur();
  };

  // Handle form submit event to set the search state and blur the input.
  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSearchQuery(value);
    setIsSearching(true);
    inputRef.current?.blur();

    try {
      // Perform AI search
      performSearch({
        message: value
      }, {
        onSuccess: (data: any) => {
          setIsSearching(false);
          
          // If no results, navigate to chat interface
          if (!data.results || data.results.length === 0) {
            navigate('/dashboard/chat', {
              state: {
                initialMessage: value,
                conversation_id: data.conversation_id
              }
            });
            return;
          }
          
          // If results found, navigate to results page
          navigate('/dashboard/discount', {
            state: {
              searchResults: data.results,
              query: value,
              message: data.message,
              conversation_id: data.conversation_id
            }
          });
        },
        onError: (error: Error) => {
          console.error('Search failed:', error);
          setIsSearching(false);
          
          // On error, navigate to chat interface
          navigate('/dashboard/chat', {
            state: {
              initialMessage: value,
              error: 'Search failed. Please try rephrasing your question.'
            }
          });
        }
      });
    } catch (error) {
      console.error('Search error:', error);
      setIsSearching(false);
      
      // On error, navigate to chat interface
      navigate('/dashboard/chat', {
        state: {
          initialMessage: value,
          error: 'Search failed. Please try rephrasing your question.'
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
          placeholder={isSearching 
            ? "Searching for deals..." 
            : "Search for deals"}
          className="md:text-base placeholder:max-sm:text-[12px] placeholder:text-neutral-800 px-4 w-full border-none focus-visible:shadow-[0_1px_1px_0_rgba(65,69,73,0.3),0_1px_3px_1px_rgba(65,69,73,0.15)] bg-[#f0f4f8] rounded-full h-[38px] focus-visible:ring-0 focus:bg-white"
          disabled={isPending || isSearching}
        />

        {!value && (
          <Button
            type="submit"
            variant={"ghost"}
            size={"icon"}
            className="absolute right-3 top-1/2 -translate-y-1/2 [&_svg]:size-5 rounded-full"
            disabled={isPending || isSearching}
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
            disabled={isPending || isSearching}
          >
            <XIcon />
          </Button>
        )}
      </form>
    </div>
  );
};
