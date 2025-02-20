import Logo from "./logo";
import { SearchInput } from "./search-input";
import { FaHeart } from "react-icons/fa6";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cardNavLinks } from "@/constants";
import { Link } from "react-router-dom";
import { useAuth } from "@/context/authContext";
import { Button } from "../ui/button";
import { LogOut } from "lucide-react";

const SearchInputNavbar = () => {
  const { logout } = useAuth();

  return (
    <section className="flex items-center justify-between gap-4">
      <Logo />
      <SearchInput />
      <div className="flex gap-4 sm:gap-8 items-center justify-center">
        <img
          src="/images/notification.svg"
          alt="notification"
          className=" max-sm:hidden"
        />
        <FaHeart className="text-red-500 max-sm:hidden" />

        <DropdownMenu>
          <DropdownMenuTrigger className="rounded-full  overflow-hidden size-10 focus:outline-none focus:ring-0 focus:border-none">
            <img
              src={"/images/settingsLadyPlaceholderImg.png"}
              alt="lady"
              className=""
            />
          </DropdownMenuTrigger>
          <DropdownMenuContent className="p-4 w-[200px] font-syne ml-8">
            {cardNavLinks?.map(({ title, href, img }, index) => (
              <DropdownMenuItem
                key={index}
                className="hover:!bg-slate-100 hover:shadow-md"
              >
                <Link to={href} className="gap-5 flex items-center w-full ">
                  <img src={img} alt="" className="" />
                  {title}
                </Link>
              </DropdownMenuItem>
            ))}
            <Button
              className="text-vividOrange mt-4 w-full"
              variant={"outline"}
              onClick={() => logout()}
            >
              Sign Out <LogOut className="ml-2" />
            </Button>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </section>
  );
};

export default SearchInputNavbar;
