import SearchInputNavbar from "@/components/globals/searchInputNavbar";

const HistoryPage = () => {
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SearchInputNavbar />
          <div className="space-y-8 py-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className="bg-white p-4 sm:p-8 font-syne relative overflow-hidden">
                <h1 className="font-bold text-xl">Claimed Discount</h1>
                <p className=" max-w-sm pr-16">
                  you claimed over 60% discount this month, keep going you can
                  make it 100%.
                </p>
                <div className="absolute -right-6 -bottom-8">
                  <img src="/images/divide.svg" alt="" className="size-28" />
                </div>
              </div>
              <div className="bg-white p-4 sm:p-8 font-syne  relative overflow-hidden">
                <h1 className="font-bold text-xl">Claimed Discount</h1>
                <p className=" max-w-sm pr-16">
                  you claimed over 60% discount this month, keep going you can
                  make it 100%.
                </p>
                <div className="absolute -right-0 -bottom-10">
                  <img src="/images/tree.svg" alt="" className="size-28" />
                </div>
              </div>
              <div className="bg-white p-4 sm:p-8 font-syne  relative overflow-hidden">
                <h1 className="font-bold text-xl">Claimed Discount</h1>
                <p className=" max-w-sm pr-16">
                  you claimed over 60% discount this month, keep going you can
                  make it 100%.
                </p>
                <div className="absolute -right-4 -bottom-6">
                  <img src="/images/moneyBag.svg" alt="" className="size-28" />
                </div>
              </div>
            </div>

            <div className="font-syne font-bold text-xl">Purchases</div>
            <div className="font-syne flex flex-wrap gap-8 justify-between">
              <div className="">
                <div className="h1 font-bold">Item</div>
                <p className="">Yelow Dress</p>
                <p className="">Groceries</p>
                <p className="">Furniture</p>
                <p className="">Groceries</p>
                <p className="">Furniture</p>
                <p className="">Yelow Dress</p>
              </div>
              <div className="">
                <div className="h1 font-bold">Price</div>
                <p className="">$12</p>
                <p className="">$10</p>
                <p className="">$28</p>
                <p className="">$12</p>
                <p className="">$10</p>
                <p className="">$28</p>
              </div>
              <div className="">
                <div className="h1 font-bold">Date</div>
                <p className="">03/01/2025</p>
                <p className="">03/01/2025</p>
                <p className="">03/01/2025</p>
                <p className="">03/01/2025</p>
                <p className="">03/01/2025</p>
                <p className="">03/01/2025</p>
              </div>
              <div className="font-syne">
                <div className="h1 font-bold">Transaction Status</div>
                <p className="flex items-center gap-1">
                  <img src="/images/good.svg" alt="" className="size-3" />{" "}
                  Successful
                </p>
                <p className="flex items-center gap-1">
                  <img src="/images/pending.svg" alt="" className="size-3" />{" "}
                  Pending
                </p>
                <p className="flex items-center gap-1">
                  <img src="/images/failed.svg" alt="" className="size-3" />{" "}
                  Failed
                </p>
                <p className="flex items-center gap-1">
                  <img src="/images/good.svg" alt="" className="size-3" />{" "}
                  Successful
                </p>
                <p className="flex items-center gap-1">
                  <img src="/images/pending.svg" alt="" className="size-3" />{" "}
                  Pending
                </p>
                <p className="flex items-center gap-1">
                  <img src="/images/failed.svg" alt="" className="size-3" />{" "}
                  Failed
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default HistoryPage;
