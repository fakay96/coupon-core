import { Swiper, SwiperSlide } from "swiper/react";
//@ts-ignore
import "swiper/css";
//@ts-ignore
import "swiper/css/effect-coverflow";
//@ts-ignore
import "swiper/css/pagination";

import "../../styles.css";
import { useTranslation } from "react-i18next";

import {
  Autoplay,
  EffectCoverflow,
  Mousewheel,
  Keyboard,
} from "swiper/modules";

const WhyDishpal = () => {
  const { t } = useTranslation();

  const whyChooseUs = [
    {
      title: t("locationBasedT"),
      des: t("locationBasedD"),
    },
    {
      title: t("personRecommendationT"),
      des: t("personRecommendationD"),
    },
    {
      title: t("neverMissDiscountT"),
      des: t("neverMissDiscountD"),
    },
    {
      title: t("saveMoneyT"),
      des: t("saveMoneyD"),
    },
    {
      title: t("sustainableShoppingT"),
      des: t("sustainableShoppingD"),
    },
    {
      title: t("reduceFoodWasteT"),
      des: t("reduceFoodWasteD"),
    },
  ];
  return (
    <section>
      <h1 className="mt-2 text-[14px] xx:text-[16px] sm:text-xl md:text-3xl lg:text-5xl text-center font-semibold font-syne tracking-tight capitalize text-[#fe9545]">
        {t("whyChooseT")}
      </h1>
      <p className="my-2 lg:my-6 text-[13px] ss:text-sm  xss:text-[20px] text-center max-w-screen-md mx-auto px-4 capitalize">
        {t("whyChooseD1")}
      </p>

      <>
        <Swiper
          loop
          effect={"coverflow"}
          slidesPerView={"auto"}
          mousewheel={{
            forceToAxis: true,
            releaseOnEdges: true,
          }}
          keyboard={true}
          coverflowEffect={{
            rotate: 50,
            stretch: 0,
            depth: 10,
            modifier: 1,
            slideShadows: false,
          }}
          spaceBetween={50}
          centeredSlides={true}
          autoplay={{
            delay: 5500,
            disableOnInteraction: false,
            pauseOnMouseEnter: true,
          }}
          modules={[Autoplay, EffectCoverflow, Mousewheel, Keyboard]}
        >
          {whyChooseUs.map(({ title, des }, index) => (
            <SwiperSlide
              className="!flex  !border-white !w-[290px]  sm:!w-[350px]  !h-[280px] md:!h-[350px] md:!w-[380px]"
              key={index}
            >
              <div className="bg-gradient-to-t  from-[#fe9545]  !to-white size-full rounded-3xl items-center flex px-8">
                <div className="w-full">
                  <h1 className="font-syne text-black font-bold text-center text-lg md:text-3xl text-wrap overflow-hidden ">
                    {title}
                  </h1>
                  <p className="mt-4 text-[13px] ss:text-sm sxx:text-[16px] xss:text-[20px] font-light text-wrap overflow-hidden text-center capitalize font-syne">
                    {des}
                  </p>
                </div>
              </div>
            </SwiperSlide>
          ))}
        </Swiper>
      </>
    </section>
  );
};

export default WhyDishpal;
