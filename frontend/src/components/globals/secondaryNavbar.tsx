import Logo from "./logo";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cardNavLinks } from "@/constants";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "@/context/authContext";
import { Button } from "../ui/button";
import { LogOut, Menu } from "lucide-react";

import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Dispatch, SetStateAction } from "react";

const SecondaryNavbar = ({
  setTab,
}: {
  setTab?: Dispatch<SetStateAction<string>>;
}) => {
  const pathname = useLocation().pathname;
  const { user, logout } = useAuth();
  return (
    <div className="">
      <div className="flex justify-between items-center py-2">
        {!user ? (
          <DropdownMenu>
            <DropdownMenuTrigger className="focus:outline-none">
              <Menu className="size-9 text-vividOrange" />
            </DropdownMenuTrigger>
            <DropdownMenuContent className="p-4 w-[200px] font-syne ml-8">
              {cardNavLinks?.map(({ title, href, img }, index) => (
                <DropdownMenuItem
                  key={index}
                  className="hover:!bg-slate-100 p-0 rounded-md hover:shadow-md"
                >
                  <Link
                    to={href}
                    className="gap-5 flex items-center w-full p-2"
                  >
                    <img src={img} alt="" />
                    {title}
                  </Link>
                </DropdownMenuItem>
              ))}
              {pathname === "/dashboard" && (
                <div className="rounded-md p-2 hover:cursor-pointer  hover:shadow-md hover:!bg-slate-100">
                  <div className="flex items-center space-x-2 ">
                    <Switch
                      id="card"
                      className="data-[state=checked]:bg-vividOrange"
                      onCheckedChange={(value) => {
                        if (value) return setTab && setTab("card");
                        return setTab && setTab("input");
                      }}
                    />
                    <Label htmlFor="card" className="font-normal">
                      Grid View
                    </Label>
                  </div>
                </div>
              )}

              <div className="flex gap-2 mt-2">
                <Button className="font-syne px-6 bg-vividOrange hover:bg-orange-500/50">
                  <Link to={"/auth/login"}>Log In</Link>
                </Button>
                <Button className="font-syne" variant={"ghost"}>
                  <Link to={"/auth/register"}>Sign Up</Link>
                </Button>
              </div>
            </DropdownMenuContent>
          </DropdownMenu>
        ) : (
          <DropdownMenu>
            <DropdownMenuTrigger className="focus:outline-none">
              <div className="rounded-full overflow-hidden size-10">
                <img
                  src={"/images/settingsLadyPlaceholderImg.png"}
                  alt="lady"
                  className=""
                />
              </div>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="p-4 w-[200px] font-syne ml-8">
              {cardNavLinks?.map(({ title, href, img }, index) => (
                <DropdownMenuItem
                  key={index}
                  className="hover:!bg-slate-100 p-0 rounded-md hover:shadow-md"
                >
                  <Link
                    to={href}
                    className="gap-5 flex items-center w-full p-2"
                  >
                    <img src={img} alt="" />
                    {title}
                  </Link>
                </DropdownMenuItem>
              ))}
              {pathname === "/dashboard" && (
                <div className="rounded-md p-2 hover:cursor-pointer  hover:shadow-md hover:!bg-slate-100">
                  <div className="flex items-center space-x-2 ">
                    <Switch
                      id="card"
                      className="data-[state=checked]:bg-vividOrange"
                      onCheckedChange={(value) => {
                        if (value) return setTab && setTab("card");
                        return setTab && setTab("input");
                      }}
                    />
                    <Label htmlFor="card" className="font-normal">
                      Grid View
                    </Label>
                  </div>
                </div>
              )}

              <Button
                className="text-vividOrange mt-4 w-full"
                variant={"outline"}
                onClick={() => logout()}
              >
                Sign Out <LogOut className="ml-2" />
              </Button>
            </DropdownMenuContent>
          </DropdownMenu>
        )}
        <Logo />
      </div>
    </div>
  );
};

export default SecondaryNavbar;
