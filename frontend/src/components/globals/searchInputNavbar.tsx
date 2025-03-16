import { FaHeart } from "react-icons/fa6";
import { Link, useNavigate } from "react-router-dom";
import { History, Info, LogOut } from "lucide-react";
import { useAuth } from "@/context/authContext";
import { Button } from "../ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../ui/dropdown-menu";
import { Skeleton } from "../ui/skeleton";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cardNavLinks } from "@/constants";

const SearchInputNavbar = ({ link }: { link?: string }) => {
  const { logout, user, isLoading } = useAuth();

  const navigate = useNavigate();

  return (
    <section className="flex items-center justify-between pt-2 gap-4">
      <Link to={link ? link : "/dashboard"} className="grid">
        <img
          alt="dispal"
          src="/images/logo.svg"
          className="hover:cursor-pointer hover:scale-105 duration-500 size-[60px] transition-all"
        />
      </Link>
      {isLoading ? (
        <div className="flex items-center gap-2">
          <Skeleton className="w-28 h-8" />
          <Skeleton className="rounded-full size-10" />
        </div>
      ) : user ? (
        <div className="flex gap-4 sm:gap-6 items-center justify-center">
          <a
            href="http://www.dishpalinfo.com"
            target="_blank"
            rel="noopener noreferrer"
          >
            <Info className="size-4" />
          </a>
          <Link to="/dashboard/history">
            <History className="size-4" />
          </Link>
          <img
            src="/images/notification.svg"
            alt="notification"
            className="size-4"
          />
          <Link to="/dashboard/reservation">
            <FaHeart className="text-red-500 size-4" />
          </Link>
          <DropdownMenu>
            <DropdownMenuTrigger className="focus:outline-none">
              <Avatar className="size-10">
                {/* <AvatarImage src={user} alt="@avatar" /> */}
                <AvatarFallback className="uppercase">
                  {user?.user?.username?.charAt(0) || user?.user?.first_name}
                </AvatarFallback>
              </Avatar>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {cardNavLinks?.map(({ title, href, img }, index) => (
                <DropdownMenuItem
                  className="hover:!bg-slate-100"
                  key={index}
                  onClick={() => navigate(href)}
                >
                  <img src={img} alt="" className="" /> {title}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="hover:!bg-slate-100"
                onClick={() => logout()}
              >
                <LogOut className="mr-2" /> Sign Out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ) : (
        <div className="flex gap-2">
          <Button
            onClick={() => {
              navigate("/auth/register");
            }}
            variant={"vivid"}
          >
            Sign up
          </Button>
          <Button
            onClick={() => {
              navigate("/auth/login");
            }}
            className="hover:text-white"
            variant={"ghost"}
          >
            Login
          </Button>
        </div>
      )}
    </section>
  );
};

export default SearchInputNavbar;
