import isEmpty from "lodash/isEmpty";
import { discountFilters, discountProducts } from "@/constants";
import { FaHeart } from "react-icons/fa6";
import { FaRegHeart } from "react-icons/fa";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import { IoLocationSharp } from "react-icons/io5";
import { MdOutlineStar } from "react-icons/md";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
// import { getDiscounts } from "@/api/authApi";
import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { XIcon } from "lucide-react";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/searchDebounce";
const DiscountPage = () => {
  const navigate = useNavigate();

  const [searchParams] = useSearchParams();
  const discount = searchParams.get("discount");
  console.count("Discount Page");
  const [toggleHeart, setToggleHeart] = useState(true);
  const [discountItems, setDiscountItems] = useState(discountProducts);
  const pathname = useLocation().pathname;

  useEffect(() => {
    if (discount === "All") {
      setDiscountItems(discountProducts);
    } else if (discount) {
      const filtered = discountProducts.filter((item) => {
        return item?.title?.toLowerCase().includes(discount?.toLowerCase());
      });

      setDiscountItems(filtered);
    } else {
      setDiscountItems(discountProducts);
    }
  }, [discount, pathname]);

  // useEffect(() => {
  //   const fetchAllDiscounts = async () => {
  //     try {
  //       // const allDiscounts = await getDiscounts();
  //       // console.log(allDiscounts);
  //     } catch (error) {
  //       console.error(error);
  //     }
  //   };

  //   fetchAllDiscounts();
  // }, []);

  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col max-w-screen-2xl mx-auto min-h-screen px-4 sm:px-8">
          <SearchInputNavbar />
          <div className="sm:flex sm:gap-8">
            <div className="w-[300px] hidden sm:flex flex-col">
              <div className="space-y-6 py-6">
                {discountFilters.map((item, index) => (
                  <div className="" key={index}>
                    <div className="bg-[#FCE9DB] p-2 px-4">{item.title}</div>
                    <div className="p-2 px-4">{item.item1}</div>
                    <div className="p-2 px-4">{item.item2}</div>
                    <div className="p-2 px-4">{item.item3}</div>
                    <div className="p-2 px-4">{item.item4}</div>
                  </div>
                ))}
              </div>
            </div>

            {isEmpty(discountItems) ? (
              <div className="flex flex-col justify-center items-center w-full relative">
                <div
                  onClick={() => {
                    navigate(
                      `/dashboard/discount${discount ? "" : "?discount=All"}`
                    );
                    // navigate(`/dashboard/discount`);
                  }}
                  className="absolute right-2 top-2 p-2 rounded-full hover:bg-slate-100 hover:cursor-pointer"
                >
                  <XIcon className="size-8" />
                </div>
                <img
                  src="/images/404.png"
                  alt=""
                  className="h-[50svh] w-auto"
                />
                <p className="font-medium font-syne text-vividOrange">
                  No Result Found.
                </p>
              </div>
            ) : (
              <div className="w-full">
                <div className="flex mx-auto mt-6 mb-12 w-full">
                  <div className="grid grid-cols-1 md:grid-cols-2  xl:grid-cols-4  gap-4 justify-center w-full">
                    {discountItems.map(({ title, img }, index) => (
                      <div
                        key={index}
                        className="bg-white shadow-xl relative w-full"
                      >
                        <div className="p-4 pb-20 flex flex-col h-full space-y-4">
                          <div className="flex justify-between">
                            <img src="/images/messageicon.svg" alt="" />
                            <div
                              className="w-fit "
                              onClick={() => setToggleHeart(!toggleHeart)}
                            >
                              {toggleHeart ? (
                                <FaRegHeart className="text-gray-500" />
                              ) : (
                                <FaHeart className="text-red-500" />
                              )}
                            </div>
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
                        <Button
                          onClick={() => {
                            navigate(`/dashboard/continue`);
                          }}
                          className="bg-buttonGreen font-bold font-syne w-full rounded-none h-12 absolute bottom-0"
                        >
                          {index % 2 === 0 ? "BUY ONLINE" : "GET DIRECTION"}
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="w-full mb-8 flex justify-center">
                  <Button
                    variant={"ghost"}
                    className="font-syne text-xl px-16 rounded-none h-12"
                  >
                    See More...
                  </Button>
                </div>
                <div className="">
                  <p className="font-medium font-syne">Recommendations</p>
                  <img src="/images/progress.svg" alt="" />
                </div>

                <div className="flex mx-auto my-12 w-full">
                  <div className="grid grid-cols-1 md:grid-cols-2  xl:grid-cols-4  gap-4 justify-center w-full">
                    {discountItems.map(({ title, img }, index) => (
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
                        <Button className="bg-buttonGreen font-bold font-syne w-full rounded-none h-12 absolute bottom-0"  onClick={() => {
                            navigate(`/dashboard/continue`);
                          }}>
                          {index % 2 === 0 ? "BUY ONLINE" : "GET DIRECTION"}
                        </Button>
                      </div>
                    ))}
                  </div>
                </div>
                <SearchInputBox
                  discount={discount}
                  discountItems={discountItems}
                  setDiscountItems={setDiscountItems}
                />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DiscountPage;

const SearchInputBox = ({
  discountItems,
  setDiscountItems,
  discount,
}: {
  discount: string | null;
  discountItems: {
    title: string;
    img: string;
  }[];
  setDiscountItems: Dispatch<
    SetStateAction<
      {
        title: string;
        img: string;
      }[]
    >
  >;
}) => {
  const [value, setValue] = useState("");
  const debouncedSearch = useDebounce(value);
  const navigate = useNavigate();

  useEffect(() => {
    const filtered = discountItems.filter((item) => {
      return item?.title?.toLowerCase().includes(debouncedSearch.toLowerCase());
    });

    setDiscountItems(filtered);
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
      {value && (
        <div
          onClick={() => {
            console.log(discount);
            setValue("");
            navigate(`/dashboard/discount${discount ? "" : "?discount=All"}`);
          }}
          className="absolute top-1/2 right-2 -translate-y-1/2 hover:bg-slate-200 p-1 rounded-full"
        >
          <XIcon className="" />
        </div>
      )}
    </div>
  );
};
