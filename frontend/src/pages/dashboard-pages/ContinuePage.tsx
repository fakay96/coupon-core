import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { useNavigate } from "react-router-dom";
const ContinuePage = () => {
  const navigate = useNavigate();

  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen px-4 sm:px-8 mx-auto">
        <SearchInputNavbar />
          <div className="flex items-center justify-center flex-col ">
            <img src="/images/timeframe.png" alt="" className="h-[50svh] w-auto" />
            <div className=" items-center flex space-y-4 flex-col justify-center">
            <p className="font-medium font-syne text-2xl text-vividOrange text-center">
              Wait For Few Minutes While You Are Being Redirected...
            </p>
            <Button
              onClick={() => {
                navigate(`/dashboard`);
              }}
              className="px-8 font-syne bg-white text-black"
            >
              Continue Shopping
            </Button>
          </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ContinuePage;
