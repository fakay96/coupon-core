import SecondaryNavbar from "@/components/globals/secondaryNavbar";
import { Button } from "@/components/ui/button";
import { planCard } from "@/constants";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { formatCurrency, formatCurrencyNormal } from "@/lib/utils";
import { AnimatedTooltip } from "@/components/ui/animated-tooltip";
const people = [
  {
    id: 1,
    name: "Jane Doe",
    designation: "Dishpal AI is awesome",
    image: "/images/settingsLadyPlaceholderImg.png",
  },
  {
    id: 2,
    name: "Emily Johnson",
    designation: "I Shop everyday with Dishpal AI",
    image: "/images/muslemGirl.png",
  },
  {
    id: 3,
    name: "Serah Smith",
    designation: "Dishpal AI - Best discount provider",
    image: "/images/blackGirl.png",
  },
];
function AnimatedTooltipPreview() {
  return (
    <div className="flex flex-row items-center justify-center w-full">
      <AnimatedTooltip items={people} />
    </div>
  );
}
const PlanPage = () => {
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SecondaryNavbar />
          <>
            <div className="py-8">
              <h1 className="font-syne font-bold text-3xl text-center">
                Pricing Plan
              </h1>
              <p className="font-syne text-vividOrange capitalize text-center py-2">
                Our pricing plans are designed to be affordable, flexible and
                tailored to your specific needs
              </p>
              <div className="">
                <AnimatedTooltipPreview />
              </div>
              <p className="text-center mt-2 font-syne">550+ happy customers</p>
            </div>
            <div className="max-w-screen-lg mx-auto mb-8">
              <div>
                <Tabs defaultValue="Month" className="">
                  <TabsList className="w-full bg-transparent h-full">
                    <div className="relative flex">
                      <TabsTrigger
                        value="Month"
                        className="rounded-none h-10 px-6 text-black data-[state=active]:bg-vividOrange data-[state=active]:text-black bg-vividOrange"
                      >
                        Monthly
                      </TabsTrigger>
                      <TabsTrigger
                        value="Year"
                        className="rounded-none h-10 px-8 text-white data-[state=active]:bg-black data-[state=active]:text-white bg-black"
                      >
                        Yearly
                      </TabsTrigger>
                    </div>
                  </TabsList>
                  <TabsContent
                    value="Month"
                    className="grid grid-cols-1 sm:grid-cols-3 gap-4"
                  >
                    {planCard.map((item, key) => (
                      <div
                        key={key}
                        className={`${
                          key == 1
                            ? "bg-buttonGreen"
                            : key == 2
                            ? "bg-buttonYellow"
                            : "bg-white"
                        } p-4 md:p-8`}
                      >
                        <p className="font-syne font-bold text-xl my-4">
                          {item.planType}
                        </p>
                        <div className="">
                          <span
                            className={`${
                              key == 0 ? "text-black " : "text-white"
                            } font-monst font-semibold text-2xl md:text-5xl`}
                          >
                            {formatCurrencyNormal(item.price || 0)}
                          </span>
                          <span
                            className={`${
                              key == 0 ? "text-black " : "text-white"
                            } font-monst`}
                          >
                            /per month
                          </span>
                        </div>
                        <div className="flex justify-between font-syne">
                          <Button variant={"link"} className="p-0">
                            Features
                          </Button>
                          <Button variant={"link"} className="p-0">
                            All
                          </Button>
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Daily Access
                          </Button>
                          <Checkbox
                            className={` ${
                              key == 1
                                ? "data-[state=checked]:text-green-500"
                                : key == 2
                                ? "data-[state=checked]:text-yellow-500"
                                : "data-[state=checked]:text-black"
                            } data-[state=checked]:bg-white border-none size-5`}
                            id="terms"
                            checked
                          />
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Number Of Saved Deals
                          </Button>
                          <p className="">{item.numberOfSavedDeals}</p>
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Exclusive Deals
                          </Button>

                          {key == 0 ? (
                            <img src="/images/cancel.svg" />
                          ) : (
                            <Checkbox
                              className={` ${
                                key == 1
                                  ? "data-[state=checked]:text-green-500"
                                  : key == 2 &&
                                    "data-[state=checked]:text-yellow-500"
                              } data-[state=checked]:bg-white border-none size-5`}
                              id="terms"
                              defaultChecked={item.exclusiveDeals}
                            />
                          )}
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Notification
                          </Button>
                          <p className="text-nowrap ml-4">
                            {key == 2 ? (
                              <Checkbox
                                id="terms"
                                className={` ${
                                  key === 2 &&
                                  "data-[state=checked]:text-yellow-500"
                                } data-[state=checked]:bg-white border-none size-5`}
                                checked
                              />
                            ) : (
                              item.notification
                            )}
                          </p>
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Cash Back Offer
                          </Button>
                          {key == 0 ? (
                            <img src="/images/cancel.svg" />
                          ) : (
                            <Checkbox
                              className={` ${
                                key == 1
                                  ? "data-[state=checked]:text-green-500"
                                  : key == 2 &&
                                    "data-[state=checked]:text-yellow-500"
                              } data-[state=checked]:bg-white border-none size-5`}
                              id="terms"
                              defaultChecked={item.cashBackOffer}
                            />
                          )}
                        </div>
                        <div className="flex justify-between items-center font-syne">
                          <Button className="p-0" variant={"link"}>
                            Priority Support
                          </Button>
                          <p className="text-nowrap ml-4">
                            {key == 0 ? (
                              <img src="/images/cancel.svg" />
                            ) : key == 1 ? (
                              "Email"
                            ) : (
                              "24/7 Priority Support"
                            )}
                          </p>
                        </div>
                      </div>
                    ))}
                  </TabsContent>
                  <TabsContent
                    value="Year"
                    className="grid grid-cols-1 sm:grid-cols-3 gap-4"
                  >
                    {planCard.map((item, key) => (
                      <div
                        key={key}
                        className={`${
                          key == 1
                            ? "bg-buttonGreen"
                            : key == 2
                            ? "bg-buttonYellow"
                            : "bg-white"
                        } p-4 md:p-8`}
                      >
                        <p className="font-syne font-bold text-xl my-4">
                          {item.planType}
                        </p>
                        <div className="">
                          <span
                            className={`${
                              key == 0 ? "text-black " : "text-white"
                            } font-monst font-semibold text-2xl md:text-5xl`}
                          >
                            {key === 0
                              ? formatCurrencyNormal((item.price || 0) * 12)
                              : formatCurrency((item.price || 0) * 12)}
                          </span>
                          <span
                            className={`${
                              key == 0 ? "text-black " : "text-white"
                            } font-monst`}
                          >
                            /per month
                          </span>
                        </div>
                        <div className="flex justify-between font-syne">
                          <Button variant={"link"} className="p-0">
                            Features
                          </Button>
                          <Button variant={"link"} className="p-0">
                            All
                          </Button>
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Daily Access
                          </Button>
                          <Checkbox
                            className={` ${
                              key == 1
                                ? "data-[state=checked]:text-green-500"
                                : key == 2
                                ? "data-[state=checked]:text-yellow-500"
                                : "data-[state=checked]:text-black"
                            } data-[state=checked]:bg-white border-none size-5`}
                            id="terms"
                            checked
                          />
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Number Of Saved Deals
                          </Button>
                          <p className="">{item.numberOfSavedDeals}</p>
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Exclusive Deals
                          </Button>

                          {key == 0 ? (
                            <img src="/images/cancel.svg" />
                          ) : (
                            <Checkbox
                              className={` ${
                                key == 1
                                  ? "data-[state=checked]:text-green-500"
                                  : key == 2 &&
                                    "data-[state=checked]:text-yellow-500"
                              } data-[state=checked]:bg-white border-none size-5`}
                              id="terms"
                              defaultChecked={item.exclusiveDeals}
                            />
                          )}
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Notification
                          </Button>
                          <p className="text-nowrap ml-4">
                            {key == 2 ? (
                              <Checkbox
                                id="terms"
                                className={` ${
                                  key === 2 &&
                                  "data-[state=checked]:text-yellow-500"
                                } data-[state=checked]:bg-white border-none size-5`}
                                checked
                              />
                            ) : (
                              item.notification
                            )}
                          </p>
                        </div>
                        <div className="flex justify-between font-syne ">
                          <Button className="p-0" variant={"link"}>
                            Cash Back Offer
                          </Button>
                          {key == 0 ? (
                            <img src="/images/cancel.svg" />
                          ) : (
                            <Checkbox
                              className={` ${
                                key == 1
                                  ? "data-[state=checked]:text-green-500"
                                  : key == 2 &&
                                    "data-[state=checked]:text-yellow-500"
                              } data-[state=checked]:bg-white border-none size-5`}
                              id="terms"
                              defaultChecked={item.cashBackOffer}
                            />
                          )}
                        </div>
                        <div className="flex justify-between items-center font-syne">
                          <Button className="p-0" variant={"link"}>
                            Priority Support
                          </Button>
                          <p className="text-nowrap ml-4">
                            {key == 0 ? (
                              <img src="/images/cancel.svg" />
                            ) : key == 1 ? (
                              "Email"
                            ) : (
                              "24/7 Priority Support"
                            )}
                          </p>
                        </div>
                      </div>
                    ))}
                  </TabsContent>
                </Tabs>
              </div>
            </div>
          </>
        </div>
      </div>
    </div>
  );
};

export default PlanPage;
