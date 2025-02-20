import { Button } from "@/components/ui/button";
import { useTranslation } from "react-i18next";
const TakeA60SecondsSurvey = () => {
  const { t } = useTranslation();
 

  return (
    <main className="">
      <section className="hidden md:flex flex-col items-center justify-center">
        <p className="font-syne font-bold text-[13px] xx:text-[16px] sm:text-xl md:text-3xl lg:text-5xl text-[#282828]/80 dark:text-white text-center max-w-[300px] sm:max-w-screen-sm mx-auto">
          {t("take6")}
        </p>
        <p className="font-syne font-bold text-[13px] xx:text-[16px] sm:text-xl md:text-3xl lg:text-5xl mb-16 text-[#282828]/80 dark:text-white text-center">
          {t("0Seconds")}
        </p>
        <div className="flex items-center flex-row gap-4 md:gap-16">
          <div className="justify-center flex">
            <img
              alt="ladyHoldingPhone"
              src="/assets/takesurvey.png"
              className="w-full h-full "
            />
          </div>
        </div>
        <Button className="mt-8 w-full max-w-sm capitalize">
          <a
            href="https://docs.google.com/forms/d/e/1FAIpQLSdIkdLs8DG4GcupB7vbWela5_vWOODO6nU1UXFVA4P9SGirhw/viewform"
            rel="noopener noreferer"
            target="_blank"
          >
            {t("helpusImproveT")}
          </a>
        </Button>
      </section>
      {/* Mobile */}
      <section className="flex flex-col md:hidden items-center justify-center">
        <p className="font-syne font-bold text-xl sm:text-2xl text-[#282828]/80 dark:text-white text-center">
          {t("quickSurvey")}
        </p>
        <div className="flex items-center flex-row gap-4 md:gap-16">
          <p className="mt-2 w-1/2 text-[11px] xxxx:text-[16px] font-syne">
            {t("surveyMobile")}
          </p>

          <div className="w-1/2 justify-center flex shrink-0">
            <img
              alt="ladyHoldingPhone"
              src="/assets/bigPhoneWithPeople.png"
              className="w-full h-full "
            />
          </div>
        </div>
        <Button className="mt-8 w-full max-w-sm">
          <a
            href="https://docs.google.com/forms/d/e/1FAIpQLSdIkdLs8DG4GcupB7vbWela5_vWOODO6nU1UXFVA4P9SGirhw/viewform"
            rel="noopener noreferer"
            target="_blank"
          >
            {t("helpusImproveT")}
          </a>
        </Button>
      </section>
    </main>
  );
};

export default TakeA60SecondsSurvey;
