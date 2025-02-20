import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { groceryProducts } from "@/constants";
import { FaHeart } from "react-icons/fa6";
import { FaRegHeart } from "react-icons/fa";
import { IoLocationSharp } from "react-icons/io5";
import { MdOutlineStar } from "react-icons/md";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
const imgs = [
  "/images/groceries.png",
  "/images/fashionGirl.png",
  "/images/electronicsImg.png",
  "/images/cafe.png",
];
const CategoryPage = () => {
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SearchInputNavbar />
          <>
            <div className="py-8 grid grid-cols-2 sxx:grid-cols-4 sm:grid-cols-4  md:ml-auto sm:mr-7">
              {imgs.map((item, index) => (
                <div key={index}>
                  <img src={item} alt="" className="h-full w-full max-h-64" />
                </div>
              ))}
            </div>
            <div className="flex mx-auto my-12 px-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 justify-center">
                {groceryProducts.map(({ title, img }, index) => (
                  <div
                    key={index}
                    className="bg-white shadow-xl relative max-w-80"
                  >
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
                        <h1 className="text-10 text-center font-bold">
                          {title}
                        </h1>
                        <p className="text-cartGreen text-center">
                          2 hours left on deal
                        </p>
                        <div className="flex items-center gap-2">
                          <IoLocationSharp className="text-vividOrange size-5 shrink-0" />
                          <p className="text-[12px] text-nowrap">
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
          </>
        </div>
      </div>
    </div>
  );
};

export default CategoryPage;
