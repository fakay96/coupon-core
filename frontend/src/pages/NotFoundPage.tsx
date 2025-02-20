import SecondaryNavbar from "@/components/globals/secondaryNavbar";
const NotFoundPage = () => {
  return (
    <div className="">
      <div className="h-full min-h-screen bg-bg3xl bg-cover ">
        <div className="flex flex-col max-w-screen-2xl mx-auto px-4 sm:px-8">
          <SecondaryNavbar />
          <div className="h-[80svh] flex flex-col items-center justify-center gap-8">
            <img src="/images/NotFound.png" alt="" />
          <p className="font-medium font-syne text-vividOrange">No Result Found.</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotFoundPage;
