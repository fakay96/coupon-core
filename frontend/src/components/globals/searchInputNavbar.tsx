import { FaHeart } from "react-icons/fa6";
import { Link } from "react-router-dom";
import { History, Info } from "lucide-react";

const SearchInputNavbar = ({ link }: { link?: string }) => {
  // const { logout } = useAuth();

  return (
    <section className="flex items-center justify-between gap-4">
      <Link to={link ? link : "/dashboard"} className="grid">
        <img
          alt="dispal"
          src="/images/logo.svg"
          className="hover:cursor-pointer hover:scale-105 duration-500 size-[60px] sm:size-[100px] transition-all"
        />
      </Link>
      <div className="flex gap-4 sm:gap-6 items-center justify-center">
        <a
          href="http://www.dishpalinfo.com"
          target="_blank"
          rel="noopener noreferrer"
        >
          <Info />
        </a>
        <Link to="/dashboard/history">
          <History />
        </Link>
        <img
          src="/images/notification.svg"
          alt="notification"
          className=""
        />
        <Link to="/dashboard/reservation">
          <FaHeart className="text-red-500 " />
        </Link>
        <Link
          to="/dashboard/settings"
          className="rounded-full overflow-hidden size-10 focus:outline-none focus:ring-0 focus:border-none"
        >
          <img
            src={"/images/settingsLadyPlaceholderImg.png"}
            alt="lady"
            className=""
          />
        </Link>
        {/* <DropdownMenu>
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
        </DropdownMenu> */}
      </div>
    </section>
  );
};

export default SearchInputNavbar;
