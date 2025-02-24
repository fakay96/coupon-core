import { Button } from "@/components/ui/button";
import { BsFillSendFill } from "react-icons/bs";
import { options } from "@/constants";
import { Link, useNavigate } from "react-router-dom";
import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { useState } from "react";
const Homepage = () => {
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-2xl mx-auto px-4 sm:px-8">
          <div className="relative">
            <div className="absolute left-0 top-0 w-full">
              <SearchInputNavbar />
            </div>
          </div>
          <>
            <div className="flex-1 flex flex-col justify-center ">
              <div className=" flex flex-col text-center mx-auto space-y-4 sm:space-y-8">
                <div className="max-sm:py-4 space-y-2">
                  <h1 className="font-syne capitalize font-bold text-3xl sm:text-4xl text-vividOrange">
                    What can i help you find?
                  </h1>
                  <p className="font-syne capitalize">
                    Powered by AI to save you time and money
                  </p>
                </div>
              </div>
              <SearchInputAndCategory />
            </div>
          </>
        </div>
      </div>
    </div>
  );
};

export default Homepage;

export const SearchInputAndCategory = () => {
  const navigate = useNavigate();
  const [value, setValue] = useState("");

  return (
    <div className="max-sm:mt-2 space-y-8">
      <div className="flex flex-wrap gap-1.5 sm:gap-6 mx-auto max-w-screen-lg items-center justify-center sm:hidden">
        {options.slice(0, 4).map(({ img, text }, index) => (
          <Link
            to={`/dashboard/category?category=${text}`}
            key={index}
            className="border-[1px] flex gap-1 py-1 px-2 rounded-full border-gray-300 items-center hover:cursor-pointer"
          >
            <img src={img} alt="items" className="size-3" />
            <span className="text-[10px]">{text}</span>
          </Link>
        ))}
      </div>
      <div className="rounded-full max-w-sm sm:max-w-screen-sm mx-auto flex items-center gap-2 p-2 bg-white sm:h-12">
        <img
          alt="dispal"
          src="/images/smilling.svg"
          className="w-5 sm:w-10 h-auto"
        />
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              navigate(`/dashboard/discount?discount=${value}`);
            }
          }}
          placeholder="Deals Near Me"
          className="bg-transparent w-full outline-none focus:outline-none max-sm:text-[12px]"
        />
        <Button
          onClick={() => {
            navigate(`/dashboard/discount?discount=${value}`);
          }}
          className="ml-auto rounded-full py-0 p-1.5 h-auto sm:h-11 sm:-mr-1.5 sm:p-4 bg-vividOrange"
        >
          <span className="hidden sm:flex">Find Deals </span>{" "}
          <BsFillSendFill className="!size-3 sm:size-4" />
        </Button>
      </div>
      <div className="hidden sm:flex flex-wrap gap-4 sm:gap-6 mx-auto max-w-screen-lg items-center justify-center">
        {options.map(({ img, text }, index) => (
          <Link
            to={`/dashboard/category?category=${text}`}
            key={index}
            className="border-[1px] flex gap-4 py-2 px-4 sm:px-8 rounded-full border-gray-300 hover:cursor-pointer"
          >
            <img src={img} alt="" />
            {text}
          </Link>
        ))}
      </div>
    </div>
  );
};
