import { Swiper, SwiperSlide } from "swiper/react";
//@ts-ignore
import "swiper/css";
//@ts-ignore
import "swiper/css/pagination";

import { Autoplay, Mousewheel, Keyboard } from "swiper/modules";
import { useNavigate } from "react-router-dom";

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
              className="!h-[20svh] sm:!h-[30svh] md:!h-[35svh] !w-auto"
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

export default CategorySwiper;
