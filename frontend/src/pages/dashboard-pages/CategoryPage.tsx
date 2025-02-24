import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { categoryList, groceryProducts, imgs } from "@/constants";
import { FaHeart } from "react-icons/fa6";
import { FaRegHeart } from "react-icons/fa";
import { IoLocationSharp } from "react-icons/io5";
import { MdOutlineStar } from "react-icons/md";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { Dispatch, SetStateAction, useEffect, useState } from "react";
import { Input } from "@/components/ui/input";
import { useDebounce } from "@/hooks/searchDebounce";
import { X } from "lucide-react";
import CategorySwiper from "@/components/category-page-components/CategorySwiper";
import { isEmpty } from "lodash";


const CategoryPage = () => {
  const [searchParams] = useSearchParams();
  const category = searchParams.get("category");
  // const filter = searchParams.get("filter");

  console.count("CategoryPage");

  const [categoryItems, setCategoryItems] = useState(groceryProducts);
  useEffect(() => {
    if (category) {
      const filtered = groceryProducts.filter((item) => {
        return item.category.toLowerCase() === category.toLowerCase();
      });
      setCategoryItems(filtered);
    } else {
      setCategoryItems(groceryProducts);
    }
    if (category === "All") {
      setCategoryItems(groceryProducts);
    }
  }, [category]);
  const navigate = useNavigate();
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto space-y-4 lg:space-y-8 pb-16">
          <SearchInputNavbar />
          <div className="">
            <h1 className="font-syne font-medium ">Category Page</h1>
            <div className="">
              <Breadcrumb>
                <BreadcrumbList>
                  <BreadcrumbItem>
                    <Link
                      to="/dashboard"
                      className="font-medium font-syne text-black"
                    >
                      Home
                    </Link>
                  </BreadcrumbItem>
                  <BreadcrumbSeparator />
                  <BreadcrumbItem>
                    <Link
                      to={`/dashboard/category-search`}
                      className="font-medium font-syne text-black"
                    >
                      Category
                    </Link>
                  </BreadcrumbItem>
                  <>
                    <BreadcrumbSeparator />
                    <BreadcrumbItem>
                      <BreadcrumbPage className="font-medium font-syne">
                        <DropdownMenu>
                          <DropdownMenuTrigger className="">
                            {category === "All"
                              ? "All Categories"
                              : !category
                              ? "All Categories"
                              : category}
                          </DropdownMenuTrigger>
                          <DropdownMenuContent className="space-y-[1px] p-2 w-44 ">
                            {categoryList
                              .filter((item) => item !== category)
                              .map((item, index) => (
                                <div
                                  key={index}
                                  onClick={() => {
                                    navigate(
                                      `/dashboard/category?category=${item}`
                                    );
                                  }}
                                >
                                  <DropdownMenuItem>
                                    {item === "All" ? "All Categories" : item}
                                  </DropdownMenuItem>
                                </div>
                              ))}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </BreadcrumbPage>
                    </BreadcrumbItem>
                  </>
                </BreadcrumbList>
              </Breadcrumb>
            </div>
          </div>
          <div className="hidden lg:grid grid-cols-2 gap-4 sxx:grid-cols-4 sm:grid-cols-5 md:ml-auto">
            {imgs.map((item, index) => (
              <div
                onClick={() => {
                  navigate(`/dashboard/category?category=${item.href}`);
                }}
                key={index}
              >
                <img
                  src={item.img}
                  alt=""
                  className="h-full w-full max-h-64 hover:cursor-pointer"
                />
              </div>
            ))}
          </div>
          <div className="lg:hidden">
            <CategorySwiper imgs={imgs} />
          </div>
          <div className="">
            <h1 className="font-syne font-bold text-3xl">
              {category === "All"
                ? "All Categories"
                : !category
                ? "All Categories"
                : category}
            </h1>
            <p className="font-syne">{categoryItems.length} Results</p>
          </div>
          <div className="flex mx-auto w-full">
            <div className="grid grid-cols-1 ss:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 justify-center w-full">
              {categoryItems.map(({ title, img }, index) => (
                <div key={index} className="bg-white shadow-xl relative w-full">
                  <div className="p-4 pb-20 flex flex-col h-full space-y-4">
                    <div
                      className="w-fit ml-auto"
                      // onClick={() => setToggleHeart(!toggleHeart)}
                    >
                      {false ? (
                        <FaRegHeart className="text-gray-500" />
                      ) : (
                        <FaHeart className="text-red-500" />
                      )}
                    </div>
                    <div className="flex-1 justify-center items-center flex">
                      <img src={img} alt="" />
                    </div>
                    <div className="space-y-2.5 capitalize font-syne">
                      <h1 className="text-10 text-center font-bold">{title}</h1>
                      <p className="text-cartGreen text-center">
                        2 hours left on deal
                      </p>
                      <div className="flex items-center justify-center gap-2">
                        <IoLocationSharp className="text-vividOrange size-4 shrink-0" />
                        <p className="text-[10px]">
                          shopping store name (2 miles away)
                        </p>
                      </div>
                      <div className="flex items-center justify-center gap-4">
                        {[1, 2, 3, 4].map((_, key) => (
                          <div key={key} className="flex">
                            <MdOutlineStar className="text-buttonGreen" />
                          </div>
                        ))}
                        <MdOutlineStar className="text-gray-200" />
                      </div>
                      <div className="flex gap-2 justify-center font-monst pt-4">
                        <p className="font-semibold">80.29 </p>
                        <div className="relative">
                          {formatCurrency(18.29)}
                          <div className="absolute -translate-y-1/2 top-1/2 h-[1px] w-8 bg-vividOrange" />
                        </div>
                      </div>
                    </div>
                  </div>
                  <Button className="font-monst w-full rounded-none font-semibold h-12 absolute bottom-0">
                    Secure Deal
                  </Button>
                </div>
              ))}
            </div>
          </div>
          <div className="">
            <SearchInputBox
              setCategoryItems={setCategoryItems}
              categoryItems={categoryItems}
              category={category}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default CategoryPage;

const SearchInputBox = ({
  categoryItems,
  setCategoryItems,
  category,
}: {
  categoryItems: {
    title: string;
    img: string;
    category: string;
  }[];
  setCategoryItems: Dispatch<
    SetStateAction<
      {
        title: string;
        img: string;
        category: string;
      }[]
    >
  >;
  category: string | null;
}) => {
  const [value, setValue] = useState("");
  const debouncedSearch = useDebounce(value);
  const navigate = useNavigate();

  useEffect(() => {
    const filtered = categoryItems.filter((item) => {
      return item?.title?.toLowerCase().includes(debouncedSearch.toLowerCase());
    });

    setCategoryItems(filtered);
  }, [debouncedSearch]);

  return (
    <div className="relative max-w-screen-md mx-auto">
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
      {(value || isEmpty(categoryItems)) && (
        <div
          onClick={() => {
            setValue("");
            navigate(`/dashboard/category${category ? "" : "?category=All"}`);
          }}
          className="absolute top-1/2 right-2 -translate-y-1/2 hover:bg-slate-200 p-1 rounded-full"
        >
          <X className="" />
        </div>
      )}
    </div>
  );
};
