import { Swiper, SwiperSlide } from "swiper/react";
import { useTranslation } from "react-i18next";
//@ts-ignore
import "swiper/css";
//@ts-ignore
import "swiper/css/pagination";
import "../../styles.css";

import { Button } from "@/components/ui/button";

import { Autoplay, Pagination, Mousewheel, Keyboard } from "swiper/modules";

const HomePageSlider = () => {
  const { t } = useTranslation();

  const mobilePageText = [
    {
      h1Tag: (
        <>
          <p className=" lg:text-balance">Dishpal AI: {t("discounted")}</p>
          <p className="lg:text-balance">
            <span className="text-[#fe9545]">{t("discountWord")}</span>{" "}
            {t("finder")}
          </p>
        </>
      ),
      pTag: <>{t("helpingYouD")}</>,
      gif: "/assets/helpingyoufind.png",
      gifD: "/assets/helpingyoufind.png",
    },
    {
      h1Tag: (
        <>
          <p className="text-nowrap lg:text-balance">{t("opportunityT")}</p>
          <p className="text-nowrap lg:text-balance">
            {t("onGreat")} <span className="text-[#fe9545]">{t("saved")}</span>
          </p>
        </>
      ),
      pTag: <>{t("opportunityD")}</>,
      gif: "/assets/dontmissout.png",
      gifD: "/assets/dontmissout.png",
    },

    {
      h1Tag: (
        <>
          <p className="lg:text-balance">{t("personalShopperT")} </p>
          <p className="lg:text-balance">
            <span className="text-[#fe9545] capitalize">Personal</span> Shopper
          </p>
        </>
      ),
      pTag: <>{t("personalShopperD")}</>,
      gif: "/assets/computerR.gif",
      gifD: "/assets/newaithinkinwhitebigger.gif",
    },
    {
      h1Tag: (
        <>
          <p className="lg:text-balance">
            {t("buyS")}{" "}
            <span className="text-[#fe9545] capitalize">{t("buyM")}</span>
          </p>
          <p className="lg:text-balance">{t("buyE")}</p>
        </>
      ),
      pTag: <>{t("buyD")}</>,
      gif: "/assets/shopbasket.svg",
      gifD: "/assets/shopbasket.svg",
    },
  ];

  const pagination = {
    clickable: true,
    renderBullet: function (index: number, className: any) {
      return '<span class="' + className + '">' + index + "</span>";
    },
  };
  return (
      <div className="mb-16 sm:mb-3 px-4">
        <Swiper
          loop
          slidesPerView={1}
          mousewheel={{
            forceToAxis: true,
            releaseOnEdges: true,
          }}
          keyboard={true}
          autoplay={{
            delay: 5500,
            disableOnInteraction: false,
            pauseOnMouseEnter: true,
          }}
          pagination={pagination}
          modules={[Autoplay, Mousewheel, Keyboard, Pagination]}
        >
          {mobilePageText?.map(({ h1Tag, pTag, gif, gifD }, index) => (
            <SwiperSlide
              key={index}
              className="!flex !flex-row items-center justify-center gap-4 sx:gap-8 sm:gap-16 md:px-8"
            >
              <div className="w-1/2 flex flex-col gap-4 ">
                <h1 className="font-syne font-semibold text-[13px] xx:text-[16px] sm:text-xl md:text-3xl lg:text-5xl capitalize">
                  {h1Tag}
                </h1>
                <p className="font-syne capitalize text-[13px] ss:text-sm sxx:text-[16px] xss:text-[20px]">
                  {pTag}
                </p>
                <Button variant={"vivid"} className="w-full md:w-fit sm:!p-7">
                  <a
                    href="https://forms.gle/MKruJpmf2w1AM9ZUA"
                    rel="noopener noreferer"
                    target="_blank"
                    className="capitalize text-[10px] xxx:text-[12px] sx:text-sm"
                  >
                    {t("signUp")}
                  </a>
                </Button>
              </div>
              <div className="w-1/2 dark:hidden flex justify-center items-center">
                <img src={gifD} alt="" className="lg:max-h-[450px]" />
              </div>
              <div className="w-1/2 hidden dark:flex justify-center items-center">
                <img src={gif} alt="" className="lg:max-h-[450px]" />
              </div>
            </SwiperSlide>
          ))}
          <div className="h-16 "/>
          <div className="mb-4 mt-8 font-syne capitalize dark:text-white text-center text-black text-[12px] sm:text-sm md:text-xl">
            Web App is still under Development.
          </div>
        </Swiper>
    </div>
  );
};

export default HomePageSlider;
