import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Link, useNavigate } from "react-router-dom";
import { EyeIcon, EyeOff } from "lucide-react";
import { useState } from "react";
import { Loader } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import { signUpSchema } from "@/validation-schemas";
import { registerUserMutation } from "@/queries/auth-queries";
import { toast } from "sonner";
import AuthHeader from "@/components/auth-component/header";

// SignUpPage component for user registration
const SignUpPage = () => {
  const navigate = useNavigate();
  const [eyeToggle, setEyeToggle] = useState(true);
  const [eyeToggleConfirm, setEyeToggleConfirm] = useState(true);

  // Mutation for registering the user
  const { isPending, mutateAsync: registerUser } = registerUserMutation();
  const form = useForm<z.infer<typeof signUpSchema>>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      email: "",
      password: "",
      password_confirmation: "",
      terms: true,
    },
  });

  // Form submit handler
  const onSubmit = async ({
    email,
    password,
    password_confirmation
  }: z.infer<typeof signUpSchema>) => {
    const username = email?.split("@")[0];

    const validatedUser = {
      email,
      username: username,
      password,
      confirm_password: password,
      password_confirmation,
    };
    toast.promise(
      registerUser(validatedUser).then(() => {
        navigate("/auth/resend-email", {
          replace: true,
          state: { username, email },
        });
      }),
      {
        loading: `${username}, Dishpal AI is creating your account.`,
        success: `${username}, Dishpal AI created your account successfully! Please verify your email to continue.`,
        error: (error) => JSON.stringify(error),
      }
    );
  };

  return (
    <div className="h-full min-h-screen flex bg-bg3xl bg-cover md:grid  md:grid-cols-2 gap-4 md:gap-8 max-sm:p-6 max-2xl:p-8 justify-center items-center 2xl:gap-16">
      <img
        src="/images/signup.png"
        width={500}
        height={600}
        alt=""
        className="hidden md:block place-self-center 2xl:ml-auto"
      />
    
      <div className="flex items-center justify-center md:justify-start 2xl:mr-auto w-full max-w-lg mb-16">
        <div className="space-y-4 sm:space-y-6 w-full">
          <div className="space-y-3 mb-12 hidden md:block">
            <h1 className="font-bold text-xl xxx:text-3xl  xl:text-5xl max-xx:text-center xl:text-center font-syne">
              Create An Account
            </h1>
            <p className="space-x-6 flex flex-wrap justify-center xx:justify-start">
              <span className="font-syne text-center ">
                Already Have An Account?
              </span>
              <Link
                to={"/auth/login"}
                className="font-syne font-bold text-vividOrange hover:underline hover:cursor-pointer"
              >
                Log In
              </Link>
            </p>
          </div>
          <AuthHeader title="Welcome" description="Create Your Account" />

          <div className="space-y-6">
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-6"
              >
                <div className="flex flex-col space-y-6">
                  <FormField
                    control={form.control}
                    name="email"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <Input
                            className="h-12 bg-white border-none rounded-none placeholder:font-semibold placeholder:font-syne  placeholder:!text-gray-300 placeholder:truncate placeholder:line-clamp-1"
                            placeholder="Email Address"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="password"
                    render={({ field }) => (
                      <FormItem>
                        <div className="relative">
                          <FormControl>
                            <Input
                              className="h-12 bg-white border-none rounded-none  placeholder:font-semibold  placeholder:font-syne  placeholder:!text-gray-300"
                              type={eyeToggle ? "password" : "text"}
                              placeholder="••••••••••"
                              {...field}
                            />
                          </FormControl>
                          {eyeToggle ? (
                            <EyeIcon
                              onClick={() => setEyeToggle(!eyeToggle)}
                              className="size-5 hover:cursor-pointer absolute top-1/2 right-1 -translate-y-1/2 -translate-x-1/2"
                            />
                          ) : (
                            <EyeOff
                              onClick={() => setEyeToggle(!eyeToggle)}
                              className="size-5 hover:cursor-pointer absolute top-1/2 right-1 -translate-y-1/2 -translate-x-1/2"
                            />
                          )}
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="password_confirmation"
                    render={({ field }) => (
                      <FormItem>
                        <div className="relative">
                          <FormControl>
                            <Input
                              className="h-12 bg-white border-none rounded-none  placeholder:font-semibold  placeholder:font-syne  placeholder:!text-gray-300"
                              type={eyeToggleConfirm ? "password" : "text"}
                              placeholder="••••••••••"
                              {...field}
                            />
                          </FormControl>
                          {eyeToggleConfirm ? (
                            <EyeIcon
                              onClick={() => setEyeToggleConfirm(!eyeToggleConfirm)}
                              className="size-5 hover:cursor-pointer absolute top-1/2 right-1 -translate-y-1/2 -translate-x-1/2"
                            />
                          ) : (
                            <EyeOff
                              onClick={() => setEyeToggleConfirm(!eyeToggleConfirm)}
                              className="size-5 hover:cursor-pointer absolute top-1/2 right-1 -translate-y-1/2 -translate-x-1/2"
                            />
                          )}
                        </div>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
                <div className="">
                  <FormField
                    control={form.control}
                    name="terms"
                    render={({ field }) => (
                      <FormItem className="flex flex-row items-center space-x-3 space-y-0 py-4">
                        <FormControl>
                          <Checkbox
                            className="data-[state=checked]:bg-white data-[state=checked]:text-vividOrange border-none size-5"
                            checked={field.value}
                            onCheckedChange={field.onChange}
                          />
                        </FormControl>
                        <div className="space-x-1 leading-none">
                          <FormLabel className="font-syne">
                            I Agree To The
                          </FormLabel>
                          <FormLabel className="font-syne md:text-vividOrange hover:underline md:hover:cursor-pointer">
                            Terms & Condition
                          </FormLabel>
                        </div>
                      </FormItem>
                    )}
                  />
                </div>
                <Button
                  type="submit"
                  className="w-full bg-vividOrange py-6 md:rounded-none hover:bg-orange-600/60 text-black font-semibold font-syne max-md:text-white"
                  disabled={isPending}
                >
                  {isPending ? (
                    <Loader className=" size-4 animate-spin" />
                  ) : (
                    "Create Account"
                  )}
                </Button>
              </form>
            </Form>
            <div className="space-y-6 hidden md:flex md:flex-col">
              <div className="flex gap-6 items-center justify-center overflow-hidden">
                <Separator className="bg-black w-full" />
                <div className="font-syne text-nowrap hidden md:block">
                  Or Register With
                </div>
                <div className="font-syne text-nowrap md:hidden">
                  Or Continue With
                </div>
                <Separator className="bg-black w-full" />
              </div>
              <div className="hidden md:flex gap-6 justify-center items-center">
                <div className="p-4 rounded-full hover:shadow-xl hover:cursor-pointer">
                  <img
                    src={"/images/google.png"}
                    alt=""
                    width={32}
                    height={32}
                  />
                </div>
                <div className="p-4 rounded-full hover:shadow-xl hover:cursor-pointer">
                  <img
                    src={"/images/instagram.png"}
                    alt=""
                    width={32}
                    height={32}
                  />
                </div>
                <div className="p-4 rounded-full hover:shadow-xl hover:cursor-pointer">
                  <img src={"/images/x.png"} alt="" width={32} height={32} />
                </div>
                <div className="p-4 rounded-full hover:shadow-xl hover:cursor-pointer">
                  <img
                    src={"/images/apple.png"}
                    alt=""
                    width={32}
                    height={32}
                  />
                </div>
              </div>
            </div>
            <div className="space-y-6 md:hidden flex justify-center">
              <div className="flex gap-2">
                <div className="font-syne">Already Have An Account ?</div>
                <Link
                  to="/auth/login"
                  className="font-syne text-vividOrange font-bold hover:underline hover:cursor-pointer"
                >
                  Log In
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignUpPage;
