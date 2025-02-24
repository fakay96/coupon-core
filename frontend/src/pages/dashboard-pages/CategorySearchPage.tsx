import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { imgs, options } from "@/constants";
import { useState } from "react";
import { BsFillSendFill } from "react-icons/bs";
import { Swiper, SwiperSlide } from "swiper/react";
//@ts-ignore
import "swiper/css";
//@ts-ignore
import "swiper/css/pagination";

import { Autoplay, Mousewheel, Keyboard } from "swiper/modules";
import { Link, useNavigate } from "react-router-dom";
const CategorySearchPage = () => {
  const navigate = useNavigate();
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-2xl mx-auto px-4 sm:px-8 ">
          <SearchInputNavbar link={"/"} />
          <>
            <div className="flex-1 flex-col flex items-center justify-center md:space-y-16">
              <div className="max-w-screen-sm lg:max-w-screen-xl text-center mx-auto flex flex-col space-y-8 mb-8 md:space-y-16 ">
                <div className="">
                  <h1 className="font-syne capitalize font-bold text-2xl sm:text-5xl text-vividOrange max-w-xl mx-auto">
                    Select Your Favorite Category
                  </h1>
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
                <div className="lg:hidden w-full">
                  <CategorySwiper imgs={imgs} />
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

export default CategorySearchPage;

export const SearchInputAndCategory = () => {
  const navigate = useNavigate();
  const [value, setValue] = useState("");

  return (
    <div className="max-sm:mt-2 space-y-4 sm:space-y-8">
      <div className="rounded-full max-w-screen-sm lg:max-w-screen-2xl mx-auto flex items-center gap-2 p-2 bg-white sm:h-12">
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
              navigate(`/dashboard/category?category=${value}`);
            }
          }}
          placeholder="Deals Near Me"
          className="bg-transparent w-full outline-none focus:outline-none max-sm:text-[12px]"
        />
        <Button
          onClick={() => {
            navigate(`/dashboard/category?category=${value}`);
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


const CategorySwiper = ({
  imgs,
}: {
  imgs: {
    img: string;
    href: string;
  }[];
}) => {
  const navigate = useNavigate();

  return (
    <div>
      <div className="lg:hidden">
        <Swiper
          loop
          spaceBetween={20}
          slidesPerView="auto"
          mousewheel={{
            forceToAxis: true,
            releaseOnEdges: true,
          }}
          keyboard={true}
          autoplay={{
            delay: 4500,
            disableOnInteraction: false,
            pauseOnMouseEnter: true,
          }}
          modules={[Autoplay, Mousewheel, Keyboard]}
        >
          {imgs?.map(({ img, href }, index) => (
            <SwiperSlide
              key={index}
              className="!h-[20svh]  !w-auto"
            >
              <div
                className="h-full w-auto hover:cursor-pointer"
                onClick={() => {
                  navigate(`/dashboard/category?category=${href}`);
                }}
              >
                <img src={img} className="h-full w-auto" alt="" />
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </div>
    </div>
  );
};

