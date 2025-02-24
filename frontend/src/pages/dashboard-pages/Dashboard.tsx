import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { imgGrid, options } from "@/constants";
import { useState } from "react";
import { BsFillSendFill } from "react-icons/bs";
import { Link, useNavigate } from "react-router-dom";
const DashboardPage = () => {
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-2xl mx-auto px-4 sm:px-8 ">
          <SearchInputNavbar link={"/"} />
          <>
            <div className="flex-1 flex-col flex items-center justify-center">
              <div className="max-w-xl text-center mx-auto flex flex-col space-y-4 mb-8">
                <div className="">
                  <h1 className="font-syne capitalize font-bold text-2xl sm:text-4xl text-vividOrange max-sm:max-w-sm mx-auto">
                    Search for the deals that matter to you
                  </h1>
                  <p className="font-syne capitalize">Follow these steps</p>
                </div>
                <div className="max-sm:max-w-sm mx-auto">
                  <div className="grid grid-cols-2 sm:grid-cols-4  justify-center items-center gap-4">
                    {imgGrid.map(
                      ({ img, topTitle, bottomTitle, href }, index) => (
                        <Link
                          to={href}
                          key={index}
                          className="relative h-36 rounded-3xl overflow-hidden "
                        >
                          <img src={img} alt="" />
                          <div className="absolute bottom-0 pb-2 bg-gradient-to-t from-black to-transparent w-full pl-4">
                            <p className="text-white font-syne text-start font-bold">
                              {topTitle}
                            </p>
                            <p className="text-white font-syne text-start font-bold -mt-2">
                              {bottomTitle}
                            </p>
                          </div>
                        </Link>
                      )
                    )}
                  </div>
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

export default DashboardPage;

export const SearchInputAndCategory = () => {
  const navigate = useNavigate();
  const [value, setValue] = useState("");

  return (
    <div className="max-sm:mt-2 space-y-4 sm:space-y-8">
      <div className="rounded-full max-w-screen-sm mx-auto flex items-center gap-2 p-2 bg-white sm:h-12">
        <img
          alt="dispal"
          src="/images/image.svg"
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
      <div className="flex flex-wrap gap-1.5 sm:gap-6 mx-auto max-w-screen-lg items-center justify-center sm:hidden">
        {options.slice(0, 4).map(({ img, text }, index) => (
          <Link
            to={`/dashboard/category?category=${text}`}
            key={index}
            className="border-[1px] flex gap-1 py-1 px-2 rounded-full border-gray-400 items-center"
          >
            <img src={img} alt="items" className="size-3" />
            <span className="text-[10px]">{text}</span>
          </Link>
        ))}
      </div>
      <div className="hidden sm:flex flex-wrap gap-4 sm:gap-6 mx-auto max-w-screen-lg items-center justify-center">
        {options.map(({ img, text }, index) => (
          <Link
            to={`/dashboard/category?category=${text}`}
            key={index}
            className="border-[1px] border-gray-400 flex gap-4 py-2 px-4 sm:px-8 rounded-full"
          >
            <img src={img} alt="" />
            {text}
          </Link>
        ))}
      </div>
    </div>
  );
};
