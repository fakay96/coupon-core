import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { SearchIcon, XIcon } from "lucide-react";
import { useRef, useState } from "react";

// SearchInput component allows users to input and submit search queries.
export const SearchInput = () => {
  const [search, setSearch] = useState("");

  const [value, setValue] = useState(search);

  const inputRef = useRef<HTMLInputElement>(null);

  // Handle input change event to update the value state.
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setValue(e.target.value);
  };

  // Handle clear button click event to reset the input value and search state.
  const handleClear = () => {
    setValue("");
    setSearch("");
    inputRef.current?.blur();
  };

  // Handle form submit event to set the search state and blur the input.
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setSearch(value);
    inputRef.current?.blur();
  };

  return (
    <div className="flex-1 flex items-center justify-center">
      <form onSubmit={handleSubmit} className="relative max-w-[670px] w-full">
        <Input
          value={value}
          onChange={handleChange}
          ref={inputRef}
          placeholder="search product"
          className="md:text-base  placeholder:max-sm:text-[12px] placeholder:text-neutral-800 px-4 w-full border-none focus-visible:shadow-[0_1px_1px_0_rgba(65,69,73,0.3),0_1px_3px_1px_rgba(65,69,73,0.15)] bg-[#f0f4f8] rounded-full h-[38px] focus-visible:ring-0 focus:bg-white"
        />

        {!value && (
          <Button
            type="submit"
            variant={"ghost"}
            size={"icon"}
            className="absolute right-3 top-1/2 -translate-y-1/2 [&_svg]:size-5 rounded-full"
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
          >
            <XIcon />
          </Button>
        )}
      </form>
    </div>
  );
};
