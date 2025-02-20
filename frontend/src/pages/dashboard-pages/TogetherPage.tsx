import SecondaryNavbar from "@/components/globals/secondaryNavbar";
import { Button } from "@/components/ui/button";

const Together = () => {
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SecondaryNavbar />
          <div className="space-y-8 py-8">
            <div className="">
              <h1 className="font-syne font-bold text-3xl text-center">
                Buy Together
              </h1>
              <p className="font-syne text-vividOrange capitalize text-center">
                Buy With <span>Friends</span> And Get A Discount
              </p>
            </div>
            <div className="w-full flex justify-center">
              <div className="lg:flex flex-col justify-evenly  z-10 hidden">
                <div className="-mr-8 flex justify-end">
                  <div className="bg-white rounded-full p-1 overflow-hidden gap-4 flex pr-6 w-fit">
                    <div className="rounded-full flex-1 overflow-hidden">
                      <img src="/images/mac.png" alt="" className="size-8" />
                    </div>
                    <div className="font-syne">
                      <h1 className="text-buttonGreen text-[12px]">Room 8</h1>
                      <div className="flex gap-2">
                        <p className="font-monst text-[8px]">
                          4 Member Active{" "}
                        </p>
                        <p className="font-monst text-[10px] font-semibold">
                          Item : Imac
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="mr-8 flex justify-start">
                  <div className="bg-white rounded-full p-1 overflow-hidden gap-4 flex  pr-6">
                    <div className="rounded-full flex-1 overflow-hidden">
                      <img
                        src="/images/girlDress.png"
                        alt=""
                        className="size-8"
                      />
                    </div>
                    <div className="font-syne">
                      <h1 className="text-buttonGreen text-[12px]">Room 5</h1>
                      <div className="flex gap-2">
                        <p className="font-monst text-[8px]">
                          5 Member Active{" "}
                        </p>
                        <p className="font-monst text-[10px] font-semibold">
                          Item : Vintage Gown
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
              <div className="max-w-sm rounded-3xl overflow-hidden">
                <img src="/images/together.png" alt="" />
              </div>
              <div className="lg:flex flex-col justify-evenly  z-10  hidden">
                <div className="-ml-8 flex">
                  <div className="bg-white rounded-full p-1 overflow-hidden gap-4 flex pr-6 w-fit">
                    <div className="rounded-full flex-1 overflow-hidden">
                      <img
                        src="/images/bagOfRice.png"
                        alt=""
                        className="size-8"
                      />
                    </div>
                    <div className="font-syne">
                      <h1 className="text-buttonGreen text-[12px]">Room 3</h1>
                      <div className="flex gap-2">
                        <p className="font-monst text-[8px]">
                          4 Member Active{" "}
                        </p>
                        <p className="font-monst text-[10px] font-semibold">
                          Item : A Bag of Rice
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="ml-8 flex justify-start mt-16">
                  <div className="bg-white rounded-full p-1 overflow-hidden gap-4 flex  pr-6">
                    <div className="rounded-full flex-1 overflow-hidden">
                      <img
                        src="/images/basketOfFruits.png"
                        alt=""
                        className="size-8"
                      />
                    </div>
                    <div className="font-syne">
                      <h1 className="text-buttonGreen text-[12px]">Room 8</h1>
                      <div className="flex gap-2">
                        <p className="font-monst text-[8px]">
                          5 Member Active{" "}
                        </p>
                        <p className="font-monst text-[10px] font-semibold">
                          Item : Groceries
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div className=" flex justify-center">

            <Button className="bg-vividOrange  w-full max-w-[300px] rounded-none h-12 font-syne font-semibold ">
              Join Room
            </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Together;
