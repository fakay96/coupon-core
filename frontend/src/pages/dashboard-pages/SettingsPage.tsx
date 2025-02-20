import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/authContext";

const SettingsPage = () => {
  const { user } = useAuth();
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SearchInputNavbar />
          <section className="flex flex-col sm:flex-row my-16 gap-8 w-full">
            <aside className="space-y-8 w-full sm:max-w-64 md:shrink-0 flex flex-col items-center">
              <div className="rounded-xl overflow-hidden size-60">
                <img
                  src={"/images/settingsLadyPlaceholderImg.png"}
                  alt="notification"
                  className=""
                />
              </div>

              <div className="w-full">
                <h1 className="font-bold font-syne text-md">History</h1>
                <div className="space-y-4 mt-4 bg-white rounded-xl p-4">
                  <div className="space-y-4 font-syne ">
                    <h1 className="font-bold text-vividOrange">Today</h1>
                    <p className="">
                      Lorem, ipsum dolor sit amet Lorem ipsum dolor sit amet
                    </p>
                    <p className="">Lorem, ipsum dolor sit amet</p>
                  </div>
                  <div className="space-y-4 font-syne ">
                    <h1 className="font-bold text-vividOrange">Yesterday</h1>
                    <p className="">Lorem, ipsum dolor sit amet</p>
                    <p className="">
                      Lorem, ipsum dolor sit amet consectetur adipisicing elit.
                    </p>
                  </div>
                  <div className="space-y-4 font-syne ">
                    <h1 className="font-bold text-vividOrange">
                      Previous 7 Days
                    </h1>
                    <p className="">
                      Lorem, ipsum dolor sit amet Temporibus, maiores ex.
                    </p>
                    <p className="">Lorem, ipsum dolor sit amet</p>
                  </div>
                </div>
              </div>
            </aside>
            <main className="w-full space-y-8">
              <div className="">
                <h1 className="font-bold font-syne text-md pb-2 -mt-2">
                  Basic Information
                </h1>
                <CardComponent
                  values={[
                    {
                      key: "Name",
                      value: user?.username ? user?.username : "Grace Hopper",
                    },
                    {
                      key: "Email Address",
                      value: user?.email
                        ? user?.email
                        : "gracehopper@gmail.com",
                    },
                    { key: "Phone", value: "+43-098-7686" },
                  ]}
                />
              </div>
              <div className="">
                <h1 className="font-bold font-syne text-md pb-2 ">
                  Location And Preference
                </h1>
                <CardComponent
                  values={[
                    { key: "Location", value: "Vienna Austria" },
                    {
                      key: "Preferred Shopping Category",
                      value: "Fashion, Groceries, Electronic",
                    },
                    { key: "Spending Budget", value: "10€ - 90€" },
                  ]}
                />
              </div>
              <div className="">
                <h1 className="font-bold font-syne text-md pb-2 ">
                  Basic Information
                </h1>
                <CardComponent
                  values={[
                    {
                      key: "Notification Preference",
                      value: "Email App Notificaion Sms",
                    },
                    { key: "Frequency of notifications", value: "8 per day" },
                    { key: "Favorite Deal Times", value: "Groceries" },
                  ]}
                />
              </div>
              <div className="w-full flex justify-end">
                <Button variant="outline" className="font-syne px-8">
                  Save & continue
                </Button>
              </div>
            </main>
          </section>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;

const CardComponent = ({
  values,
}: {
  values: { key: string; value: string }[];
}) => {
  return (
    <div className="relative flex flex-col bg-white p-4 md:p-8 rounded-xl w-full">
      {values.map(({ key, value }, index) => (
        <div key={index} className="flex gap-2 flex-wrap">
          <span className="font-medium font-syne">{key}:</span>
          <span className="font-syne  ">{value}</span>
        </div>
      ))}
      <div className="absolute right-4 bottom-4 flex gap-2 font-syne font-bold">
        <span className="max-sm:hidden">Edit</span>
        <img src="/images/edit.svg" alt="" className="size-6 " />
      </div>
    </div>
  );
};
