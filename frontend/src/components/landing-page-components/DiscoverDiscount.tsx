// import { useTranslation } from "react-i18next";

const DiscoverDiscount = () => {
  // const { t } = useTranslation();

  return (
    <section id="why">
      <h1 className="mt-2 sm:text-xl md:text-2xl lg:text-4xl text-center font-semibold font-syne tracking-tight capitalize text-[#fe9545] mb-8">
        {/* {t("whyChooseT")} */}
        Discover Discounts With Ease
      </h1>
      <div className="flex justify-center ">
        <div className="w-[118px] xxx:grid gap-4 hidden">
          <div className="bg-vividOrange px-4 rounded-xl font-medium w-fit text-white py-2 text-[10px] size-fit max-w-[250px] row-start-2 justify-self-end">
            1. Search Item
          </div>
          <div className="bg-vividOrange px-4 rounded-xl font-medium w-fit text-white py-2 text-[10px] size-fit max-w-[250px] row-start-7">
            3. Make Payment
          </div>
          <div className="row-start-11" />
        </div>
        <div className="col-span-5 shrink-0">
          <img
            src="/assets/whatcanIhelpyoufind.png"
            alt="phone image"
            className="h-[300px] lg:w-auto lg:h-[500px]"
          />
        </div>
        <div className="w-[118px] xxx:grid gap-4 hidden">
          <div className="bg-vividOrange px-4 rounded-xl font-medium w-fit text-white py-2 text-[10px] size-fit max-w-[250px] row-start-3">
            2. Search Product
          </div>
          <div className="bg-vividOrange px-4 rounded-xl font-medium  text-white py-2 text-[10px] size-fit w-fit row-start-10">
            4. Purchase Completed
          </div>
          <div className="row-start-11" />
        </div>
      </div>
    </section>
  );
};

export default DiscoverDiscount;
