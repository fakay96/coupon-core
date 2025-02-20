import { useTranslation } from "react-i18next";
const MissionVision = () => {
  const { t } = useTranslation();
  const missionVision = [
    {
      title: t("missionT"),
      des: t("missionD"),
    },
    {
      title: t("visionT"),
      des: t("visionD"),
    },
  ];
  return (
    <>
      <section className=" w-full hidden lg:block space-y-8" id="about">
        <div className=" md:pl-[5%] ">
          <h1 className="text-[13px] xx:text-[16px] sm:text-xl md:text-3xl lg:text-5xl font-semibold max-md:text-center font-syne tracking-tight capitalize text-[#fe9545]">
            {t("aboutUs")}
          </h1>
        </div>
        <div className="flex flex-col md:grid md:grid-cols-2 lg:grid-cols-3 items-center justify-center gap-8">
          <div className="h-[500px] w-full flex items-center justify-center">
            <img
              src="/assets/thinkingR.gif"
              alt=""
              className="object-cover object-top h-full w-auto "
            />
          </div>
          {missionVision?.map(({ title, des }, index) => (
            <div
              key={index}
              className="bg-[#F9F9F9] dark:bg-white max-md:max-w-[500px] rounded-3xl h-[450px] lgx:h-[550px] xl:h-[450px] p-8 justify-center items-start flex shadow-xl overflow-hidden"
            >
              <div className="overflow-hidden">
                <h1 className="text-3xl md:text-5xl text-center font-bold font-syne tracking-tight text-black capitalize mb-6 ">
                  {title}
                </h1>
                <p className="text-black text-center capitalize lgx:text-xl">
                  {des}
                </p>
              </div>
            </div>
          ))}
        </div>
      </section>
      {/* mobile */}
      <section className=" w-full lg:hidden space-y-8" id="about">
        <div className=" md:pl-[5%] ">
          <h1 className="text-[13px] xx:text-[16px] sm:text-xl md:text-3xl lg:text-5xl font-bold max-lg:text-center font-syne tracking-tight capitalize text-[#fe9545]">
            {t("aboutUs")}
          </h1>
        </div>
        <div className="relative max-xx:flex max-xx:flex-col max-xx:gap-8">
          <div className="bg-gray-100 xxxx:ml-4 xxx:h-[275px] sx:ml-8 md: mdx:ml-16 rounded-3xl p-4 sm:p-8 justify-start items-start flex shadow-xl max-xx:w-full xx:w-[220px] ss:w-[270px] sx:w-[270px] sm:w-[350px] md:h-[420px] xss:h-[420px] xss:w-[320px] md:w-[400px] mx:w-[450px] mx:h-[300px]">
            <div className="overflow-hidden">
              <h1 className="text-sm sx:text-2xl sm:text-3xl lg:text-5xl text-start mb-2 font-bold font-syne tracking-tight text-black capitalize">
                {t("missionT")}
              </h1>
              <p className="text-black text-[12px] sx:text-[14px] xss:text-xl mx:text-xl mx:h-[200px] capitalize">
                {t("missionD")}
              </p>
            </div>
          </div>
          <div className="flex flex-col xx:grid xx:grid-cols-2 ">
            <div className="order-2 xx:order-1 h-full flex items-center justify-center">
              <img
                src="/assets/thinkingR.gif"
                alt=""
                className="object-cover object-top h-full w-full"
              />
            </div>
            <div className="bg-gray-100 order-1 xx:order-2 rounded-3xl sm:p-8 p-4 justify-start items-start flex xx:-mt-4 xx:-ml-8 xxx:h-[275px] xxxx:h-60 sx:h-[280px] sxx:w-[270px] ss:w-[270px] sm:h-[400px] md:h-[420px] sm:w-[350px] md:w-[400px] mdx: sx:-mt-[17px] xss:h-[420px] xss:w-[320px] xss:-mt-8 shadow-xl mx:w-[450px] mx:h-[300px] z-20 ">
              <div className="overflow-hidden ">
                <h1 className="text-sm sx:text-2xl sm:text-3xl lg:text-5xl text-start mb-2 font-bold font-syne tracking-tight text-black capitalize">
                  {t("visionT")}
                </h1>
                <p className="text-black text-pretty text-[12px] sx:text-[14px] xss:text-lg mx:text-xl mx:h-[200px] capitalize">
                  {t("visionD")}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default MissionVision;
