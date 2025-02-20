import * as React from "react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
export function LanguageSelect({ mobile = false }) {
  const { i18n } = useTranslation();
  const [lang, setLang] = React.useState("en");
  const changeLang = (value: any) => {
    setLang(value);
    i18n.changeLanguage(value);
  };

  React.useEffect(() => {
    const lang = localStorage.getItem("i18nextLng");
    setLang(lang?.substring(0, 2)!);
  }, [lang]);

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          className="border-none hover:!bg-transparent hover:scale-105 transition-transform !p-2 uppercase  hover:cursor-pointer focus:outline-none focus:border-none"
        >
          <>
            {lang}
            {lang == "en" ? (
              <img src="/assets/uk.png" alt="" />
            ) : (
              <img src="/assets/deusche.png" alt="" />
            )}
          </>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent className="!w-8 !min-w-24 shadow-2xl z-50  hover:scale-105 transition-transform bg-white" side={mobile ? "right" : "bottom"}>
        <DropdownMenuRadioGroup value={lang} onValueChange={changeLang}>
          <DropdownMenuRadioItem
            value="en"
            className={`${
              lang == "en" ? "hidden" : "flex"
            } !p-0 !pl-4 space-x-2 hover:!bg-transparent hover:scale-105 transition-transform hover:cursor-pointer`}
          >
            EN <img src="/assets/uk.png" alt="" />{" "}
          </DropdownMenuRadioItem>{" "}
          <DropdownMenuRadioItem
            value="de"
            className={`${
              lang == "de" ? "hidden" : "flex"
            } !p-2 !pl-4 space-x-2 hover:!bg-transparent hover:scale-105 transition-transform hover:cursor-pointer`}
          >
            DE <img src="/assets/deusche.png" alt="" />{" "}
          </DropdownMenuRadioItem>{" "}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
