import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
// import { Checkbox } from "@/components/ui/checkbox";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  // FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  InputOTP,
  InputOTPGroup,
  InputOTPSlot,
} from "@/components/ui/input-otp";
// import { EyeIcon, EyeOff } from "lucide-react";
// import { useRef, useState } from "react";
import { Loader } from "lucide-react";
import {
  //  Link,useLocation, 
   useNavigate } from "react-router-dom";
import { Separator } from "@/components/ui/separator";
import { 
  // signInSchema,
   verificationCodeSchema } from "@/validation-schemas";
// import { Input } from "@/components/ui/input";
// import { axiosGoogleLogin } from "@/api/authApi";
// import { useGoogleLogin } from "@react-oauth/google";
import { toast } from "sonner";
import { loginUserQuery } from "@/queries/auth-queries";
import AuthHeader from "@/components/auth-component/header";
// import GoogleButton from "@/components/auth-component/google-button";

// SignInPage component for user login
const CodeVerificationPage = () => {
  // const location = useLocation();
  // const firstname = location.state?.firstname;
  // let googleInfo = useRef({ email: "", name: "" });
  const navigate = useNavigate();
  // const [eyeToggle, setEyeToggle] = useState(true);

  // Mutation for logging in the user
  const { isPending,
    //  mutateAsync: loginUser
     } = loginUserQuery();

  const form = useForm<z.infer<typeof verificationCodeSchema>>({
    resolver: zodResolver(verificationCodeSchema),
    defaultValues: {
      pin: "",
    },
  });

  const onSubmit = ({ pin }: z.infer<typeof verificationCodeSchema>) => {
    toast.success(pin);
    return navigate("/dashboard", { replace: true });
    // return;
    // toast.promise(
    //   loginUser(userInfo).then(() => {
    //     navigate("/dashboard", { replace: true });
    //   }),
    //   {
    //     loading: `${
    //       firstname || userInfo?.username
    //     }, Dishpal AI is logging you into your account now.`,
    //     success: `${
    //       firstname || userInfo?.username
    //     }, Here is your dashboard! Explore!`,
    //     error: `${
    //       firstname || userInfo?.username
    //     }, Check your email and password and try again!`,
    //   }
    // );
  };

  return (
    <div className="h-full min-h-screen bg-bg3xl bg-cover grid md:grid-cols-2 max-2xl:py-8 max-sm:p-4  gap-4 max-2xl:p-8">
      <img
        src="/images/loginImg.png"
        width={500}
        height={600}
        alt=""
        className="hidden md:block 2xl:hidden place-self-center "
      />
      <div className="relative hidden 2xl:grid">
        <img
          src="/images/coverSigninImg.png"
          alt=""
          className="2xl:absolute 2xl:h-full 2xl:w-full place-self-center justify-self-end "
        />
        <img
          src="/images/logo.svg"
          alt=""
          className="2xl:absolute 2xl:w-[150px] h-auto left-4 top-4"
        />
        <h1 className="font-syne z-30 absolute top-1/2 left-1/2 text-5xl font-bold -translate-x-1/2 -translate-y-1/2 leading- text-white">
          Welcome <br /> Back
        </h1>
      </div>
      <div className="flex items-center justify-center md:justify-start w-full max-w-lg mx-auto">
        <div className="space-y-6 w-full mb-16">
          <div className="hidden md:block space-y-3 mb-3">
            <h1 className="font-bold text-xl xxx:text-3xl  xl:text-5xl max-xx:text-center  font-syne">
              Sign In
            </h1>
            <p className="space-x-6 flex flex-wrap justify-center xx:justify-start">
              <span className="font-syne max-xx:text-center ">
                Welcome Back, Please Enter Your Details
              </span>
            </p>
          </div>
          <AuthHeader
            title="Verification Code"
            description="Please Enter The Verification Code Sent To "
          />

          <div className="md:flex gap-6 items-center justify-center overflow-hidden hidden">
            <Separator className="bg-black w-full" />
            <div className="font-syne text-nowrap">Or</div>
            <Separator className="bg-black w-full" />
          </div>

          <div className="space-y-6">
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 flex flex-col items-center"
              >
                <FormField
                  control={form.control}
                  name="pin"
                  render={({ field }) => (
                    <FormItem className="w-full">
                      <FormControl>
                        <InputOTP className="w-full" maxLength={4} {...field}>
                          <InputOTPGroup className="flex justify-around  w-full">
                            <InputOTPSlot className="border-none hover:shadow-xl bg-white size-12" index={0} />
                            <InputOTPSlot className="border-none hover:shadow-xl bg-white size-12" index={1} />
                            <InputOTPSlot className="border-none hover:shadow-xl bg-white size-12" index={2} />
                            <InputOTPSlot className="border-none hover:shadow-xl bg-white size-12" index={3} />
                          </InputOTPGroup>
                        </InputOTP>
                      </FormControl>

                      <FormMessage />
                    </FormItem>
                  )}
                />

                <Button
                  type="submit"
                  className="w-full bg-vividOrange py-6 md:rounded-none hover:bg-orange-600/60 md:text-black font-semibold font-syne"
                  disabled={isPending}
                >
                  {isPending ? (
                    <Loader className=" size-4 animate-spin" />
                  ) : (
                    <>Send</>
                  )}
                </Button>
              </form>
            </Form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CodeVerificationPage;
