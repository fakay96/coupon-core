import SecondaryNavbar from "@/components/globals/secondaryNavbar";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent } from "@/components/ui/tabs";
import { BsFillSendFill } from "react-icons/bs";
import { imgGrid, options } from "@/constants";
import { useState } from "react";
const DashboardPage = () => {
  const [tab, setTab] = useState("input");

  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-2xl mx-auto px-4 sm:px-8 ">
          <SecondaryNavbar setTab={setTab} />
          <>
            <div className="flex-1 flex items-center justify-center">
              <Tabs
                value={tab}
                onValueChange={(value) => {
                  setTab(value);
                }}
                className="w-full"
              >
                <TabsContent
                  value="input"
                  className=" flex flex-col text-center mx-auto space-y-4 md:space-y-8"
                >
                  <div className="">
                    <h1 className="font-syne capitalize font-bold text-3xl md:text-4xl text-vividOrange">
                      What can i help you find?
                    </h1>
                    <p className="font-syne capitalize">
                      Powered by AI to save you time and money
                    </p>
                  </div>
                </TabsContent>
                <TabsContent
                  value="card"
                  className="max-w-xl text-center mx-auto flex flex-col space-y-4 mb-8"
                >
                  <div className="">
                    <h1 className="font-syne capitalize font-bold text-2xl md:text-4xl text-vividOrange">
                      Search for the deals that matter to you
                    </h1>
                    <p className="font-syne capitalize">Follow these steps</p>
                  </div>

                  <div className="grid grid-cols-2 sm:grid-cols-4  justify-center items-center gap-4">
                    {imgGrid.map(({ img, topTitle, bottomTitle }, index) => (
                      <div
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
                      </div>
                    ))}
                  </div>
                </TabsContent>
                <div className="space-y-4 md:space-y-8">
                  <div className="rounded-full max-w-screen-sm mx-auto flex items-center gap-2 p-2 bg-white">
                    <img
                      alt="dispal"
                      src="/images/smilling.svg"
                      className=" w-10 h-auto"
                    />
                    <input
                      placeholder="Deals Near Me"
                      className="bg-transparent w-full outline-none focus:outline-none"
                    />
                    <Button className="ml-auto rounded-full mr-1 p-2.5 sm:p-4 bg-vividOrange">
                      <span className="hidden sm:flex">Find Deals </span>{" "}
                      <BsFillSendFill className="w-2 h-2  sm:size-4" />
                    </Button>
                  </div>
                  <div className="hidden md:flex flex-wrap gap-4 md:gap-6 mx-auto max-w-screen-lg items-center justify-center">
                    {options.map(({ img, text }, index) => (
                      <div
                        key={index}
                        className="border-[1px] flex gap-4 py-2 px-4 sm:px-8 rounded-full border-vividOrange"
                      >
                        <img src={img} alt="" />
                        {text}
                      </div>
                    ))}
                  </div>
                  <div className="flex flex-wrap gap-4 md:gap-6 mx-auto max-w-screen-lg items-center justify-center md:hidden">
                    {options.slice(0, 4).map(({ img, text }, index) => (
                      <div
                        key={index}
                        className="border-[1px] flex gap-1 py-1 px-2 rounded-full border-vividOrange items-center"
                      >
                        <img src={img} alt="items" className="size-3" />
                        <span className="text-[10px]">{text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </Tabs>
            </div>
          </>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
