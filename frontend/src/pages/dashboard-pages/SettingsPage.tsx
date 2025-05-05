import SearchInputNavbar from "@/components/globals/searchInputNavbar";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/context/authContext";
import { capitalize } from "lodash";
import { FaCheckSquare } from "react-icons/fa";
import { MdCheckBoxOutlineBlank } from "react-icons/md";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { updateUserProfileMutation } from "@/queries/auth-queries";

import { Input } from "@/components/ui/input";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { DeleteUserAccountService } from "@/api/authApi";
import { useConfirm } from "@/hooks/use-confirm";
import { z } from "zod";
import { profileUpdateSchema } from "@/validation-schemas";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";

const SettingsPage = () => {
  const { user, logout } = useAuth();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { mutateAsync: updateUserProfile } = updateUserProfileMutation();
  const [ConfirmDialog, confirm] = useConfirm(
    "Are you sure?",
    "You are about to delete this account"
  );

  const form = useForm<z.infer<typeof profileUpdateSchema>>({
    resolver: zodResolver(profileUpdateSchema),
    defaultValues: {
      first_name: "",
      last_name: "",
      preferences: "",
      phone_number: "",
    },
  });

  function onSubmit(values: z.infer<typeof profileUpdateSchema>) {
    const { preferences, ...others } = values;
    const newPreference = preferences === "" ? {} : preferences;
    toast.promise(
      updateUserProfile({ ...others, preferences: newPreference }),
      {
        loading: `${form.getValues(
          "first_name"
        )}, Dishpal AI is updating your account details.`,
        success: () => {
          setDialogOpen(false);
          return `${form.getValues("first_name")}, Your profile info has been successfully updated!`;
        },
        error: (error) => JSON.stringify(error.message),
      }
    );
  }

  useEffect(() => {
    form.setValue("first_name", user?.first_name || "");
    form.setValue("last_name", user?.last_name || "");
    form.setValue("phone_number", user?.phone_number || "");
  }, [user]);

  const handleDelete = async () => {
    const ok = await confirm();

    if (ok) {
      await DeleteUserAccountService();
      logout();
    }
  };
  return (
    <div className="">
      <div className="bg-bg3xl bg-cover">
        <div className="flex flex-col h-full min-h-screen max-w-screen-xl px-4 sm:px-8 mx-auto">
          <SearchInputNavbar />
          <section className="flex flex-col sm:flex-row my-16 gap-8 w-full">
            <ConfirmDialog />
            <main className="w-full space-y-8">
              <div className="">
                <h1 className="font-bold font-syne text-md pb-2 -mt-2">
                  Basic Information
                </h1>
                <div className="relative flex flex-col bg-white p-4 md:p-8 rounded-xl w-full">
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">
                      FirstName:
                    </span>
                    <span className="font-syne ">
                      {capitalize(user?.first_name)}{" "}
                    </span>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">
                      LastName:
                    </span>
                    <span className="font-syne ">
                      {capitalize(user?.last_name)}
                    </span>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center">
                    <span className="font-bold text-sm font-syne">Phone:</span>
                    <span className="font-syne ">{user?.phone_number}</span>
                  </div>
                  <div className="absolute right-4 bottom-2 flex gap-2 font-syne font-bold">
                    <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
                      <DialogTrigger asChild>
                        <div className="hover:cursor-pointer">Edit</div>
                      </DialogTrigger>
                      <DialogContent className="sm:max-w-[445px] w-[95svw] rounded-xl">
                        <Form {...form}>
                          <form onSubmit={form.handleSubmit(onSubmit)}>
                            <DialogHeader>
                              <DialogTitle className="text-start">
                                Edit profile
                              </DialogTitle>
                              <DialogDescription className="text-start">
                                Hi{" "}
                                <span className="text-vividOrange capitalize">
                                  {user?.first_name}
                                </span>
                                , Make changes to your profile here.
                              </DialogDescription>
                            </DialogHeader>
                            <div className="grid gap-4 py-4">
                              <FormField
                                control={form.control}
                                name="first_name"
                                render={({ field }) => (
                                  <FormItem>
                                    <FormLabel>First Name</FormLabel>
                                    <FormControl>
                                      <Input placeholder="Matthew" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                              <FormField
                                control={form.control}
                                name="last_name"
                                render={({ field }) => (
                                  <FormItem>
                                    <FormLabel>Last Name</FormLabel>
                                    <FormControl>
                                      <Input placeholder="Mark" {...field} />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                              <FormField
                                control={form.control}
                                name="preferences"
                                render={({ field }) => (
                                  <FormItem>
                                    <FormLabel>Preferences</FormLabel>
                                    <FormControl>
                                      <Input
                                        placeholder="flight, travel, tourism"
                                        {...field}
                                      />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                              <FormField
                                control={form.control}
                                name="phone_number"
                                render={({ field }) => (
                                  <FormItem>
                                    <FormLabel>Phone Number</FormLabel>
                                    <FormControl>
                                      <Input
                                        placeholder="+1 (583) 928-8372"
                                        {...field}
                                      />
                                    </FormControl>
                                    <FormMessage />
                                  </FormItem>
                                )}
                              />
                            </div>
                            <Button
                              type="submit"
                              variant={"vivid"}
                              className="w-fit ml-auto"
                            >
                              Update Profile
                            </Button>
                          </form>
                        </Form>
                      </DialogContent>
                    </Dialog>
                  </div>
                </div>
              </div>

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
                  onClick={handleDelete}
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
