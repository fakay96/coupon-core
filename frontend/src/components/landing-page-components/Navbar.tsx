import {
  Disclosure,
  DisclosureButton,
  DisclosurePanel,
} from "@headlessui/react";
import { Bars3Icon, XMarkIcon } from "@heroicons/react/24/outline";

import { Link } from "react-scroll";
import { LanguageSelect } from "./LanguageSelect";
import { useTranslation } from "react-i18next";
import { useState, useEffect } from "react";
import { Button } from "../ui/button";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/authContext";

export default function Navbar() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { t } = useTranslation();
  const [isFixed, setIsFixed] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const scrollThreshold = 550;
      setIsFixed(window.scrollY > scrollThreshold);
    };

    window.addEventListener("scroll", handleScroll);

    return () => {
      window.removeEventListener("scroll", handleScroll);
    };
  }, []);
  const navigation = [
    { name: t("home"), href: "home", current: true },
    { name: t("aboutUs"), href: "why", current: false },
    { name: t("services"), href: "question", current: false },
  ];
  return (
    <Disclosure
      as="nav"
      className={`transition-all duration-300 ${
        isFixed
          ? "fixed top-0 left-0 w-full shadow-2xl  backdrop-blur-3xl z-50"
          : ""
      } `}
    >
      <div
        className={`${
          isFixed ? "h-20 z-50" : ""
        } flex relative justify-between items-center px-4 max-w-screen-xl mx-auto`}
      >
        <Link
          spy={true}
          smooth={true}
          duration={2500}
          offset={-70}
          to="toppage"
          className="hover:cursor-pointer py-2 hover:scale-105 duration-500 transition-all order-2 lg:order-1 lg:absolute lg:left-4 lg:top-0"
        >
          <img
            alt="Your Company"
            src="/assets/mobileLogo.png"
            className="h-12 w-auto lg:hidden hover:cursor-pointer hover:scale-105 duration-500 transition-all"
          />
          <img
            alt="Your Company"
            src="/assets/desktopLogo.png"
            className="h-14 w-auto hidden lg:block hover:cursor-pointer hover:scale-105 duration-500 transition-all"
          />
        </Link>
        <div className="max-lg:hidden gap-8 flex lg:absolute lg:-translate-x-1/2 left-1/2 top-5 ">
          {navigation.map((item) => (
            <Link
              spy={true}
              smooth={true}
              duration={2500}
              offset={-70}
              key={item.name}
              to={item.href}
              className={`text-primary hover:border-accent hover:border-b-2 hover:text-accent
                      px-3 py-2 text-sm font-medium hover:font-bold hover:cursor-pointer capitalize`}
            >
              {item.name}
            </Link>
          ))}
        </div>
        <div className="flex items-center justify-center gap-2 lg:absolute right-2 top-4">
          <div className="hidden lg:flex items-center justify-center gap-4">
            {user ? (
              <Button
                variant={"vivid"}
                className="font-syne !rounded-md px-6 hover:text-black transition-all"
                onClick={() => navigate("/dashboard")}
              >
                Dashboard
              </Button>
            ) : (
              <Button
                variant={"vivid"}
                className="font-syne !rounded-md px-6 hover:text-black transition-all"
                onClick={() => navigate("/auth/login")}
              >
                Login
              </Button>
            )}
            <LanguageSelect />
          </div>
          <DisclosureButton className="lg:hidden">
            <span className="sr-only">Open main menu</span>
            <Bars3Icon
              aria-hidden="true"
              className="block text-[#fe9545] size-8 group-data-[open]:hidden"
            />
            <XMarkIcon
              aria-hidden="true"
              className="hidden text-[#fe9545] size-8 group-data-[open]:block"
            />
          </DisclosureButton>
        </div>
      </div>
      <DisclosurePanel className="flex flex-col p-4 space-y-2 shadow-2xl backdrop-blur-3xl mx-4 rounded-xl">
        {navigation.map((item) => (
          <Link
            key={item.name}
            to={item.href}
            spy={true}
            smooth={true}
            duration={2500}
            offset={-70}
            className="w-full"
          >
            <DisclosureButton
              className={`
                     ${
                       item.current
                         ? " text-primary"
                         : "text-primary hover:bg-accent hover:text-primary"
                     } rounded-md px-3 py-2 text-sm font-medium w-full text-start capitalize`}
            >
              {item.name}
            </DisclosureButton>
          </Link>
        ))}
        <div className="flex flex-row justify-between w-full ">
          <LanguageSelect mobile={true} />
        </div>
        {user ? (
          <Button
            variant={"vivid"}
            className="font-syne !rounded-md px-6 hover:text-black transition-all"
            onClick={() => navigate("/dashboard")}
          >
            Dashboard
          </Button>
        ) : (
          <Button
            variant={"vivid"}
            className="font-syne !rounded-md px-6 hover:text-black transition-all"
            onClick={() => navigate("/auth/login")}
          >
            Login
          </Button>
        )}
      </DisclosurePanel>
    </Disclosure>
  );
}
