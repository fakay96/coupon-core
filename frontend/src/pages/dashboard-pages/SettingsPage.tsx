import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/authContext";
import { capitalize } from "lodash";
import { FaCheckSquare } from "react-icons/fa";
import { MdCheckBoxOutlineBlank } from "react-icons/md";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { DeleteUserAccountService, updateUserProfile } from "@/api/authApi";

const SettingsPage = () => {
  const { user, logout } = useAuth();
  const [username, setUsername] = useState(user?.user?.username);
  const [email, setEmail] = useState(user?.user?.email);
  const [firstname, setFirstname] = useState("");
  const [lastname, setLastname] = useState("");
  // const [preference, setPreference] = useState({});
  const [location, setLocation] = useState("");
  const handleSummit = async () => {
    const user = {
      username,
      email,
      first_name: firstname,
      last_name: lastname,
      location,
    };
    toast.promise(updateUserProfile(user), {
      loading: `${username}, Dishpal AI is updating your account details.`,
      success: `${username}, Your profile info have been successfully updated!`,
      error: (error) => error.message,
    });
  };

  useEffect(() => {
    setUsername(user?.user?.username);
    setEmail(user?.user?.email);
  }, [user]);

  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SearchInputNavbar />
          <section className="flex flex-col sm:flex-row my-16 gap-8 w-full">
            {/* {user?.user?.image && (
              <aside className="space-y-8 w-full sm:max-w-64 md:shrink-0 flex flex-col items-center">
                <div className="rounded-xl overflow-hidden size-60">
                  <img src={user?.user?.image} alt="notification" className="" />
                </div>
              </aside>
            )} */}
            <main className="w-full space-y-8">
              <div className="">
                <h1 className="font-bold font-syne text-md pb-2 -mt-2">
                  Basic Information
                </h1>
                <div className="relative flex flex-col bg-white p-4 md:p-8 rounded-xl w-full">
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">Name:</span>
                    <span className="font-syne ">
                      {capitalize(user?.user?.username)} {capitalize(user?.user?.last_name)}
                    </span>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">
                      Email Address:
                    </span>
                    <span className="font-syne ">
                      {capitalize(user?.user?.email)}
                    </span>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">Phone:</span>
                    <span className="font-syne ">
                      {user?.user?.phone_number}
                    </span>
                  </div>
                  <div className="absolute right-4 bottom-2 flex gap-2 font-syne font-bold">
                    <Dialog>
                      <DialogTrigger asChild>
                        <div className="hover:cursor-pointer">Edit</div>
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-[425px] w-[95svw] rounded-xl">
                        <DialogHeader>
                          <DialogTitle className="text-start">
                            Edit profile
                          </DialogTitle>
                          <DialogDescription className="text-start">
                            Hi{" "}
                            <span className="text-vividOrange capitalize">
                              {user?.user?.username}
                            </span>
                            , Make changes to your profile here.
                          </DialogDescription>
                        </DialogHeader>
                        <div className="grid gap-4 py-4">
                          <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="username" className="">
                              Username
                            </Label>
                            <Input
                              id="username"
                              onChange={(e) => setUsername(e.target.value)}
                              value={username}
                              className="col-span-3"
                            />
                          </div>
                          <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="firstname" className="">
                              Firstname
                            </Label>
                            <Input
                              id="firstname"
                              onChange={(e) => setFirstname(e.target.value)}
                              value={firstname}
                              className="col-span-3"
                            />
                          </div>
                          <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="lastname" className="">
                              Lastname
                            </Label>
                            <Input
                              id="lastname"
                              onChange={(e) => setLastname(e.target.value)}
                              value={lastname}
                              className="col-span-3"
                            />
                          </div>
                          <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="email" className="">
                              Email
                            </Label>
                            <Input
                              id="email"
                              onChange={(e) => setEmail(e.target.value)}
                              value={email}
                              className="col-span-3"
                            />
                          </div>
                          <div className="grid grid-cols-4 items-center gap-4">
                            <Label htmlFor="location" className="">
                              Location
                            </Label>
                            <Input
                              id="location"
                              onChange={(e) => setLocation(e.target.value)}
                              value={location}
                              className="col-span-3"
                            />
                          </div>
                        </div>
                        <DialogClose>
                          <Button
                            type="submit"
                            variant={"vivid"}
                            className="w-fit ml-auto"
                            onClick={handleSummit}
                          >
                            Update Profile
                          </Button>
                        </DialogClose>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </div>
              {/*  <div className="">
                <h1 className="font-bold font-syne text-md pb-2 ">
                  Location And Preference
                </h1>
               <CardComponent
                  values={[
                    // { key: "Location", value: "Vienna Austria" },
                    {
                      key: "Preferred Shopping Category",
                      value: "Fashion, Groceries, Electronic",
                    },
                    // { key: "Spending Budget", value: "10€ - 90€" },
                  ]}
                /> 
              </div>*/}
              <div className="">
                <h1 className="font-bold font-syne text-md pb-2 ">
                  Basic Information
                </h1>
                <div className="relative flex flex-col text-white p-4 md:p-8 rounded-xl w-full bg-gradient-to-r from-black  to-[#FFA5A5]">
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">
                      Notification Preference:
                    </span>
                    <span className="font-syne flex items-center gap-2 ">
                      <FaCheckSquare className="text-white" /> Email{" "}
                      <FaCheckSquare className="text-white" /> App Notification
                      <MdCheckBoxOutlineBlank className="text-white" /> Sms
                    </span>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">
                      Frequency Of Notifications:
                    </span>
                    <span className="font-syne flex items-center gap-2 ">
                      <MdCheckBoxOutlineBlank className="text-white" /> Daily{" "}
                      <MdCheckBoxOutlineBlank className="text-white" /> Weekly
                      <FaCheckSquare className="text-white" /> Instant Alert
                    </span>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">
                      Favorite Deal Times:
                    </span>
                    <span className="font-syne flex items-center gap-2 ">
                      <MdCheckBoxOutlineBlank className="text-white" /> Mornings{" "}
                      <MdCheckBoxOutlineBlank className="text-white" /> Evenings
                      <FaCheckSquare className="text-white" />
                      Weekends
                    </span>
                  </div>
                  <div className="absolute right-4 bottom-4 flex gap-2 font-syne font-bold">
                    <span className="max-sm:hidden text-black">Edit</span>
                  </div>
                </div>
              </div>
              <div className="w-full flex justify-end">
                <Button
                  onClick={async () => {
                    await DeleteUserAccountService();
                    logout();
                  }}
                  variant="destructive"
                  className="font-syne px-8 font-bold"
                >
                  Delete Account
                </Button>
                {/* <Button variant="outline" className="font-syne px-8 font-bold">
                  Save & continue
                </Button> */}
              </div>
            </main>
          </section>
        </div>
      </div>
    </div>
  );
};

export default SettingsPage;
