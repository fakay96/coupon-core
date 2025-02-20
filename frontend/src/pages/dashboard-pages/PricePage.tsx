import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { discountProducts } from "@/constants";
import { formatCurrency } from "@/lib/utils";
import { IoLocationSharp } from "react-icons/io5";
import { Textarea } from "@/components/ui/textarea";
import { FaStar } from "react-icons/fa6";

const PricePage = () => {
 
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SearchInputNavbar />
          <div className="space-y-8 py-8">
            <div className="flex gap-4 sm:gap-8 flex-col md:flex-row">
              <div className=" flex justify-center">
                <img
                  src="/images/laptop.png"
                  className="md:w-auto md:h-auto md:max-w-[550px]"
                  alt=""
                />
              </div>
              <div className="space-y-4 sm:space-y-8 font-monst max-w-lg  w-full flex flex-col pt-8 md:pt-12">
                <div className="flex gap-4 font-monst">
                  <p className="font-semibold text-xl">80.29</p>
                  <div className="relative text-[10px] flex items-center">
                    {formatCurrency(18.29)}
                    <div className="absolute -translate-y-1/2 top-1/2 h-[1px] w-6 bg-vividOrange" />
                  </div>
                </div>
                <p className="">
                  Lorem ipsum, dolor sit amet consectetur adipisicing elit.
                  Ipsa, asperiores animi porro dignissimos labore.
                </p>
                <div className="space-y-4">
                  <div className="flex items-center gap-4">
                    {[1, 2, 3, 4].map((_, key) => (
                      <div key={key} className="flex">
                        <FaStar className="text-buttonGreen size-6" />
                      </div>
                    ))}
                    <FaStar className="text-gray-200 size-6" />
                  </div>
                  <div className="flex items-center gap-2">
                    <IoLocationSharp className="text-vividOrange size-5 shrink-0" />
                    <p className="text-[12px] text-nowrap">
                      shopping store name (2 miles away)
                    </p>
                  </div>
                </div>
                <div className="space-y-4 max-w-sm">
                  <Button
                    variant={"outline"}
                    className=" w-full max-w-sm rounded-none h-12 font-syne font-semibold "
                  >
                    Add To Reserve
                  </Button>
                  <Button className="bg-buttonGreen  w-full max-w-sm rounded-none h-12 font-syne font-semibold ">
                    Buy Now
                  </Button>
                </div>
              </div>
            </div>
            <div className="bg-white/50 p-4 sm:p-8">
              <div className="">
                <h1 className="font-syne font-bold text-xl">Reviews</h1>
                <Separator />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 sm:gap-8">
                <div className="space-y-4 font-monst mt-4">
                  <div className="">
                    <h1 className="font-medium text-3xl font-monst">4.5</h1>
                    <p className="font-monst">Average Ratings</p>
                  </div>
                  <div className="">
                    <div className="flex items-center gap-1 font-monst mb-1">
                      {[1, 2, 3, 4].map((_, key) => (
                        <div key={key} className="flex">
                          <FaStar className="text-gray-400" />
                        </div>
                      ))}
                      <FaStar className="text-gray-200" />
                    </div>
                    <h1 className="font-semibold text-xl font-syen">
                      Paul Felix
                    </h1>
                    <p className="font-monst">
                      Lorem, ipsum dolor sit amet consectetur adipisicing elit.
                      Quos eligendi cupiditate sapiente reprehenderit quibusdam
                      minima.
                    </p>
                  </div>
                  <div className="">
                    <div className="flex items-center gap-1 font-monst mb-1">
                      {[1, 2, 3, 4].map((_, key) => (
                        <div key={key} className="flex">
                          <FaStar className="text-gray-400" />
                        </div>
                      ))}
                      <FaStar className="text-gray-200" />
                    </div>
                    <h1 className="font-semibold text-xl font-syen">
                      John Doe
                    </h1>
                    <p className="font-monst">
                      Lorem, ipsum dolor sit amet consectetur adipisicing elit.
                      Quos eligendi cupiditate sapiente reprehenderit quibusdam
                      minima.
                    </p>
                  </div>
                </div>
                <div className="py-4">
                  <div className="">
                    <div className="flex items-center mb-4 gap-1">
                      {[1, 2, 3, 4].map((_, key) => (
                        <div key={key} className="flex">
                          <FaStar className="text-yellow-400 size-5" />
                        </div>
                      ))}
                      <FaStar className="text-gray-200 size-5" />
                    </div>
                  </div>
                  <div className="space-y-6">
                    <form className="space-y-6">
                      <div className="flex gap-6 w-full">
                        <Input
                          className="h-12 bg-white border-none rounded-none  placeholder:font-monst  placeholder:!text-gray-300 placeholder:ml-8"
                          placeholder="First Name"
                        />
                        <Input
                          className="h-12 bg-white border-none rounded-none  placeholder:font-monst  placeholder:!text-gray-300 placeholder:ml-8"
                          placeholder="Email"
                          type="email"
                        />
                      </div>
                      <div className="flex flex-col space-y-6">
                        <div className="relative">
                          <Textarea
                            className="bg-white border-none rounded-none    placeholder:font-monst  placeholder:!text-gray-300 resize-none"
                            placeholder="Your review"
                            rows={6}
                          ></Textarea>
                        </div>
                      </div>
                      <Button
                        type="submit"
                        className="w-full bg-black py-6 rounded-none hover:bg-orange-600/60 text-white font-semibold font-monst"
                      >
                        {"Submit Review"}
                      </Button>
                    </form>
                  </div>
                </div>
              </div>
            </div>
            <div className="flex mx-auto my-12 w-full ">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 w-full">
                {discountProducts?.slice(0, 4)?.map(({ title, img }, index) => (
                  <div
                    key={index}
                    className="bg-white shadow-xl relative w-full"
                  >
                    <div className="p-4 pb-20 flex flex-col h-full space-y-4">
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
                        <div className="flex items-center gap-2 justify-center">
                          <IoLocationSharp className="text-vividOrange size-4 shrink-0" />
                          <p className="text-[11px] text-nowrap">
                            shopping store name (2 miles away)
                          </p>
                        </div>
                        <div className="flex items-center justify-center gap-4">
                          {[1, 2, 3, 4].map((_, key) => (
                            <div key={key} className="flex">
                              <FaStar className="text-buttonGreen" />
                            </div>
                          ))}
                          <FaStar className="text-gray-200" />
                        </div>
                        <div className="flex gap-2 justify-center font-monst pt-4">
                          <div className="relative">
                            18.29
                            <div className="absolute -translate-y-1/2 top-1/2 h-[2px] w-10 bg-vividOrange" />
                          </div>
                          <p className="font-semibold">
                            {formatCurrency(80.29)}
                          </p>
                        </div>
                      </div>
                    </div>
                    <Button className="font-monst w-full rounded-none font-semibold h-12 absolute bottom-0 bg-buttonGreen">
                      Secure Deal
                    </Button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PricePage;
