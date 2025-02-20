import { appDonwload, socials } from "@/constants";
import { useTranslation } from "react-i18next";

const Socials = () => {
  const { t } = useTranslation();

  return (
    <main className="md:dark:bg-[#212529] space-y-16 mt-16">
        <div className="flex flex-col sm:flex-row gap-8 justify-between items-center">
          <div className="flex gap-4 order-2 sm:order-1">
            {socials?.map(({ icon }: any, index) => {
              const Icon = icon;
              return (
                <Icon
                  key={index}
                  className="size-10 md:size-12 hover:cursor-pointer"
                />
              );
            })}
          </div>
          <div className="flex flex-col order-1 sm:order-2 ">
            <h1 className=" text-[#fe9545] text-sm capitalize sm:text-lg font-bold font-syne max-sm:text-center mb-2">
              {t("available")}
            </h1>
            <div className="flex flex-wrap items-center bg-black dark:bg-[#212529] justify-center gap-4 md:gap-8 p-4 dark:shadow-2xl  dark:invertinsetphism rounded-full ">
              {appDonwload?.map(({ icon, title }: any, index) => {
                const Icon = icon;
                return (
                  <div
                    key={index}
                    className="items-center justify-center flex gap-2  hover:cursor-pointer"
                  >
                    <Icon className="size-6 text-white" />
                    <p className="font-syne text-white">{title}</p>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
        <div className="flex items-center justify-center ">
          <div className="text-sm text-gray-500 sm:text-center flex  items-center dark:text-gray-400 font-syne space-x-4 md:space-x-6 mb-4">
            <img src="/assets/copywhite.svg" className="dark:hidden" alt="" />{" "}
            <a
              href="https://www.dishpalinfo.com/"
              className="hover:underline font-syne"
            >
              2024 Dishpal Info Website All Rights Reserved.
            </a>
          </div>
        </div>
    </main>
  );
};

export default Socials;
