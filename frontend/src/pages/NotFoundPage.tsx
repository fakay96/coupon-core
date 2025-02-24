import SearchInputNavbar from "@/components/globals/searchInputNavbar";
const NotFoundPage = () => {
  return (
    <div className="">
      <div className="h-full min-h-screen bg-bg3xl bg-cover ">
        <div className="flex flex-col max-w-screen-2xl mx-auto px-4 sm:px-8">
          <SearchInputNavbar />
          <div className="h-[80svh] flex flex-col items-center justify-center gap-8 w-full">
            <img src="/images/404.png" alt="" className="h-[50svh] w-auto" />
            <p className="font-medium font-syne text-vividOrange">
              No Result Found.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
