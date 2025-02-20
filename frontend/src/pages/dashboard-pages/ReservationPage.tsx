import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { formatCurrency } from "@/lib/utils";
import React from "react";

const reservations = [
  {
    img: "/images/ladyInRed.png",
    price: 12.29,
    totalPrice: 12.29,
    size: 42,
    color: "red",
    time: "2 Hours Left On Deal",
    title: "Renaissance-Style Gown.",
    cta: "BUY ONLINE",
  },
  {
    img: "/images/fruits.png",
    price: 10.9,
    totalPrice: 12.29,
    size: 42,
    color: "red",
    time: "1 Hours Left On Deal",
    title: "Vegetable",
    cta: "GET DIRECTION",
  },
  {
    img: "/images/girlDress.png",
    price: 10.9,
    totalPrice: 21.8,
    size: 42,
    color: "red",
    time: "30 Minutes Left On Deal",
    title: "Renaissance-Style Gown.",
    cta: "BUY ONLINE",
  },
];

const ReservationPage = () => {
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SearchInputNavbar />

          <div className="md:hidden mt-4 flex gap-4 flex-col mb-8">
            {reservations.map((item, index) => (
              <div key={index}>
                <div className="bg-white p-2 px-4 space-y-2" key={index}>
                  <div className="flex justify-between text-[12px]">
                    <p className="font-syne">Product</p>
                    <p className="font-syne">Price</p>
                  </div>
                  <div className="flex gap-4 items-center">
                    <div className="bg-imgBg rounded-xl flex items-end justify-center shrink-0">
                      <img src={item.img} alt="" className="h-32 w-24" />
                    </div>
                    <div className="font-syne capitalize text-[12px]">
                      {index === 0 && <p>Size {item.size}</p>}
                      {(index === 0 || index === 2) && (
                        <p>Color {item.color}</p>
                      )}
                      {(index === 0 || index === 2) && (
                        <p
                          className={`${
                            index === 0 ? "text-green-500" : "text-red-500"
                          }`}
                        >
                          {item.time}
                        </p>
                      )}
                      <p>{item.title}</p>
                      {index === 1 && (
                        <p className={`text-vividOrange`}>{item.time}</p>
                      )}
                    </div>
                  </div>
                  <p className="font-monst ml-auto w-fit">
                    {formatCurrency(item.price)}
                  </p>
                </div>
                <Button className="bg-green-500 rounded-none">{item.cta}</Button>
              </div>
            ))}
          </div>
          <div className="hidden md:flex flex-wrap gap-4 sm:gap-8">
            <div className="space-y-4 py-8 max-md:w-full">
              <CardComponent
                img="/images/ladyInRed.png"
                price={10.9}
                totalPrice={21.8}
              >
                <div className="flex gap-4 sm:gap-8">
                  <div className="space-y-8 font-syne flex flex-col justify-between">
                    <div className="mt-8">
                      <h1 className="text-mutedText">FASHION</h1>
                      <p className="font-bold">Renaissance-Style Gown.</p>
                    </div>
                    <div className="">
                      <p className="">
                        <span className="text-gray-400">Color: </span>
                        <span className="">Red</span>
                      </p>
                      <p className="">
                        <span className="text-gray-400">Size: </span>
                        <span className="">42</span>
                      </p>
                      <p className="">
                        <span className="text-gray-400">Time: </span>
                        <span className="text-buttonGreen">
                          2 Hours Left On Deal
                        </span>
                      </p>
                    </div>
                  </div>
                </div>
              </CardComponent>
              <CardComponent
                img="/images/fruits.png"
                price={10.9}
                totalPrice={12.29}
                first={false}
              >
                <div className="flex gap-4 sm:gap-8">
                  <div className="space-y-8 font-syne justify-between flex flex-col">
                    <div className="mt-8">
                      <h1 className="text-mutedText">GROCERY</h1>
                      <p className="font-bold">Vegetables</p>
                    </div>
                    <p className="">
                      <span className="text-gray-400">Time: </span>
                      <span className="text-vividOrange">
                        1 Hours Left On Deal
                      </span>
                    </p>
                  </div>
                </div>
              </CardComponent>
              <CardComponent
                img="/images/girlDress.png"
                price={12.29}
                totalPrice={12.29}
                first={false}
              >
                <div className="flex gap-4 sm:gap-8">
                  <div className="space-y-8 font-syne justify-between flex flex-col">
                    <div className="mt-8">
                      <h1 className="text-mutedText">GROCERY</h1>
                      <p className="font-bold">Dress</p>
                    </div>
                    <p className="">
                      <span className="text-gray-400">Time: </span>
                      <span className="text-red-500">
                        30 Minutes Left On Deal
                      </span>
                    </p>
                  </div>
                </div>
              </CardComponent>
            </div>
            <div className="bg-white font-syne my-8 p-4 sm:p-8 space-y-4 sm:space-y-8 capitalize max-w-sm h-fit">
              <h1 className="font-bold text-xl">Coupon Code</h1>
              <p className="text-mutedText">
                Lorem ipsum, dolor sit amet consectetur adipisicing elit. Iusto
                debitis dicta molestiae quisquam veritatis provident tempora,
                quasi, corporis cumque porro voluptatem, omnis quo nihil illum
                illo ea perspiciatis fugit praesentium.
              </p>
              <div className="space-y-4">
                <Button
                  className="w-full rounded-full h-12"
                  variant={"outline"}
                >
                  Coupon Code
                </Button>
                <Button className="w-full rounded-full h-12">Apply</Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReservationPage;

const CardComponent = ({
  children,
  img,
  price,
  totalPrice,
  first = true,
}: {
  children: React.ReactNode;
  img: string;
  price: number;
  totalPrice: number;
  first?: boolean;
}) => {
  return (
    <div className="flex flex-col md:flex-row font-syne bg-white w-full p-4 gap-4 min-h-56 shrink-0 justify-center">
      <div className="bg-imgBg rounded-xl flex items-end justify-center shrink-0">
        <img
          src={img}
          alt="image"
          className="h-auto w-auto max-h-44 min-w-36 "
        />
      </div>
      {children}
      <div className="flex flex-col justify-between lg:ml-auto">
        <div
          className={`${
            first ? "" : "mt-16"
          } flex gap-4 sm:gap-8 md:gap-16 flex-1`}
        >
          <div className="flex flex-col gap-10">
            {first && <p className="text-mutedText">Price</p>}
            <p className="font-bold font-monst">{price}€</p>
          </div>
          <div className="flex flex-col gap-10">
            {first && <p className="text-mutedText">Quantity</p>}
            <div className="flex gap-2 items-center">
              <div className="rounded-md size-4 border border-mutedText flex justify-center items-center ">
                -
              </div>
              <div className=" flex justify-center items-center font-bold font-monst">
                2
              </div>
              <div className="rounded-md size-4 border border-mutedText flex justify-center items-center ">
                +
              </div>
            </div>
          </div>
          <div className="flex flex-col gap-10">
            {first && <p className="text-mutedText">Total Price</p>}
            <p className="font-bold font-monst">{totalPrice}€</p>
          </div>
        </div>
        <div className="mt-8">
          <Button className="bg-buttonGreen w-full rounded-none h-12 ">
            Buy Now
          </Button>
        </div>
      </div>
    </div>
  );
};
