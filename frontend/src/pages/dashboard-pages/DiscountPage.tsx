import { discountProducts } from "@/constants";
import { FaHeart } from "react-icons/fa6";
import { FaRegHeart } from "react-icons/fa";
import { useState } from "react";
import { IoLocationSharp } from "react-icons/io5";
import { MdOutlineStar } from "react-icons/md";
import { Button } from "@/components/ui/button";

import SecondaryNavbar from "@/components/globals/secondaryNavbar";
import { formatCurrency } from "@/lib/utils";
const DiscountPage = () => {
  const [toggleHeart, setToggleHeart] = useState(true);

  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col max-w-screen-2xl mx-auto px-4 sm:px-8">
          <SecondaryNavbar />
          <>
            <p className="font-medium font-syne">Search Result For Groceries</p>
            <div className="flex mx-auto my-12 w-full">
              <div className="grid grid-cols-2  xl:grid-cols-4  gap-4 justify-center w-full">
                {discountProducts.slice(3, 7).map(({ title, img }, index) => (
                  <div
                    key={index}
                    className="bg-white shadow-xl relative w-full"
                  >
                    <div className="p-4 pb-20 flex flex-col h-full space-y-4">
                      <div
                        className="w-fit ml-auto"
                        onClick={() => setToggleHeart(!toggleHeart)}
                      >
                        {toggleHeart ? (
                          <FaRegHeart className="text-gray-500" />
                        ) : (
                          <FaHeart className="text-red-500" />
                        )}
                      </div>
                      <div className="flex-1 justify-center items-center flex">
                        <img src={img} alt="" />
                      </div>
                      <div className="space-y-2.5 capitalize font-syne">
                        <h1 className=" sm:text-xl text-center font-bold">
                          {title}
                        </h1>
                        <p className="text-center max-sm:text-[12px]">
                          {" "}
                          Lorem ipsum dolor sit amet consectetur.{" "}
                        </p>
                        <p className="text-cartGreen text-center max-sm:text-[12px]">
                          2 hours left on deal
                        </p>
                        <div className="flex items-center justify-center gap-2">
                          <IoLocationSharp className="text-vividOrange size-4 shrink-0" />
                          <p className="text-[11px] ">
                            shopping store name (2 miles away)
                          </p>
                        </div>
                        <div className="flex items-center justify-center gap-1 md:gap-4">
                          {[1, 2, 3, 4].map((_, key) => (
                            <div key={key} className="flex">
                              <MdOutlineStar className="text-buttonGreen max-sm:size-3 size-5" />
                            </div>
                          ))}
                          <MdOutlineStar className="text-gray-200 max-sm:size-3 size-5" />
                        </div>
                        <p className="text-cartGreen text-center max-sm:text-[12px]">
                          {formatCurrency(1.04)}
                        </p>
                      </div>
                    </div>
                    <Button className="bg-buttonGreen font-bold font-syne w-full rounded-none h-12 absolute bottom-0">
                      {index % 2 === 0 ? "BUY ONLINE" : "GET DIRECTION"}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
            <p className="font-medium font-syne">Similar Items</p>
            <div className="flex mx-auto my-12 w-full">
              <div className="grid grid-cols-2  xl:grid-cols-4  gap-4 justify-center w-full">
                {discountProducts.slice(3, 7).map(({ title, img }, index) => (
                  <div
                    key={index}
                    className="bg-white shadow-xl relative w-full"
                  >
                    <div className="p-4 pb-20 flex flex-col h-full space-y-4">
                      <div
                        className="w-fit ml-auto"
                        onClick={() => setToggleHeart(!toggleHeart)}
                      >
                        {toggleHeart ? (
                          <FaRegHeart className="text-gray-500" />
                        ) : (
                          <FaHeart className="text-red-500" />
                        )}
                      </div>
                      <div className="flex-1 justify-center items-center flex">
                        <img src={img} alt="" />
                      </div>
                      <div className="space-y-2.5 capitalize font-syne">
                        <h1 className=" sm:text-xl text-center font-bold">
                          {title}
                        </h1>
                        <p className="text-center max-sm:text-[12px]">
                          {" "}
                          Lorem ipsum dolor sit amet consectetur.{" "}
                        </p>
                        <p className="text-cartGreen text-center max-sm:text-[12px]">
                          2 hours left on deal
                        </p>
                        <div className="flex items-center justify-center gap-2">
                          <IoLocationSharp className="text-vividOrange size-4 shrink-0" />
                          <p className="text-[11px] ">
                            shopping store name (2 miles away)
                          </p>
                        </div>
                        <div className="flex items-center justify-center gap-1 md:gap-4">
                          {[1, 2, 3, 4].map((_, key) => (
                            <div key={key} className="flex">
                              <MdOutlineStar className="text-buttonGreen max-sm:size-3 size-5" />
                            </div>
                          ))}
                          <MdOutlineStar className="text-gray-200 max-sm:size-3 size-5" />
                        </div>
                       
                      </div>
                    </div>
                    <Button className="bg-buttonGreen font-bold font-syne w-full rounded-none h-12 absolute bottom-0">
                      {index % 2 === 0 ? "BUY ONLINE" : "GET DIRECTION"}
                    </Button>
                  </div>
                ))}
              </div>
            </div>
            <div className="w-full mb-8 flex justify-center">
              <Button
                variant={"outline"}
                className="font-syne text-xl px-16 rounded-none h-12"
              >
                Load More
              </Button>
            </div>
          </>
        </div>
      </div>
    </div>
  );
};

export default DiscountPage;
