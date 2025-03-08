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
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { axiosGoogleLogin, loginUserService } from "@/api/authApi";
import { loginCredentials } from "@/types";
import { useGoogleLogin } from "@react-oauth/google";
import { registerUserQuery } from "@/queries/auth-queries";
import { toast } from "sonner";
import AuthHeader from "@/components/auth-component/header";
import GoogleButton from "@/components/auth-component/google-button";

// SignUpPage component for user registration
const SignUpPage = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [eyeToggle, setEyeToggle] = useState(true);

  // Mutation for logging in the user
  const { mutateAsync: loginUser } = useMutation<
    unknown,
    Error,
    loginCredentials
  >({
    mutationFn: async (value: loginCredentials) =>
      await loginUserService(value),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["userInfo"] });
    },
  });

  // Mutation for registering the user
  const { isPending, mutateAsync: registerUser } = registerUserQuery();
  const form = useForm<z.infer<typeof signUpSchema>>({
    resolver: zodResolver(signUpSchema),
    defaultValues: {
      firstname: "",
      lastname: "",
      email: "",
      password: "",
      terms: true,
    },
  });

  // Google login handler
  const googleLogin = useGoogleLogin({
    onSuccess: async (tokenResponse) => {
      const { email, name } = await axiosGoogleLogin(tokenResponse);
      const googleCredentials = {
        email,
        password: import.meta.env.VITE_GOOGLE_PASS,
        username: email?.split("@")[0],
        confirm_password: import.meta.env.VITE_GOOGLE_PASS,
      };
      const { confirm_password, ...restOfLoginCredentials } = googleCredentials;
      toast.promise(
        registerUser(googleCredentials).then(() => {
          loginUser(restOfLoginCredentials).then(() => {
            navigate("/dashboard", { replace: true });
          });
        }),
        {
          loading: `${name}, Dishpal AI is creating your account.`,
          success: `${name}, Here is your dashboard! Explore!`,
          error: `${name}, Your email is already registered.`,
        }
      );
    },
    onError: () => {
      console.error("Login Failed");
    },
  });

  // Form submit handler
  const onSubmit = async ({
    email,
    password,
    firstname,
  }: z.infer<typeof signUpSchema>) => {
    const validatedUser = {
      email,
      username: email?.split("@")[0],
      password,
      confirm_password: password,
    };
    toast.promise(
      registerUser(validatedUser).then(() => {
        navigate("/auth/login", { replace: true, state: { firstname } });
      }),
      {
        loading: `${firstname}, Dishpal AI is creating your account.`,
        success: `${firstname}, Dishpal AI created your account successfully! Please login to continue.`,
        error: `${firstname}, Your email is already registered.`,
      }
    );
  };

  return (
    <div className="h-full min-h-screen flex bg-bg3xl bg-cover md:grid  md:grid-cols-2 gap-4 md:gap-8 max-sm:p-6 max-2xl:p-8 justify-center items-center">
      <img
        src="/images/signup.png"
        width={500}
        height={600}
        alt=""
        className="hidden md:block 2xl:hidden place-self-center "
      />
      <div className="relative hidden 2xl:grid">
        <img
          src="/images/logo.svg"
          alt=""
          className="2xl:absolute 2xl:w-[150px] h-auto left-4 top-4 z-50"
        />
        <img
          src="/images/coverSignupImg.png"
          alt=""
          className="2xl:absolute 2xl:h-full 2xl:w-full place-self-center justify-self-end "
        />
      </div>
      <div className="flex items-center justify-center md:justify-start 2xl:mx-auto w-full max-w-lg mb-16 ">
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
                <div className="flex gap-6 w-full">
                  <FormField
                    control={form.control}
                    name="firstname"
                    render={({ field }) => (
                      <FormItem className="w-full">
                        <FormControl>
                          <Input
                            className="h-12 bg-white border-none rounded-none placeholder:font-semibold placeholder:font-syne  placeholder:!text-gray-300 placeholder:text-center"
                            placeholder="First Name"
                            {...field}
                          />
                        </FormControl>

                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="lastname"
                    render={({ field }) => (
                      <FormItem className="w-full">
                        <FormControl>
                          <Input
                            className="h-12 bg-white border-none rounded-none placeholder:font-semibold placeholder:font-syne  placeholder:!text-gray-300 placeholder:text-center"
                            placeholder="Last Name"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                </div>
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
                              placeholder="Password"
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
            <div
              onClick={() => {
                googleLogin();
              }}
              className="hidden md:flex gap-6 justify-center items-center"
            >
              <div className="p-4 rounded-full hover:shadow-xl hover:cursor-pointer">
                <img src={"/images/google.png"} alt="" width={32} height={32} />
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
                <img src={"/images/apple.png"} alt="" width={32} height={32} />
              </div>
            </div>
            <GoogleButton
              onClick={() => {
                googleLogin();
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignUpPage;
