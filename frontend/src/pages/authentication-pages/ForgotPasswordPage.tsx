import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormMessage,
} from "@/components/ui/form";
import { Loader } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { forgotPasswordSchema } from "@/validation-schemas";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { loginUserQuery } from "@/queries/auth-queries";
import AuthHeader from "@/components/auth-component/header";

const ForgotPasswordPage = () => {
  const navigate = useNavigate();

  // Mutation for logging in the user
  const { isPending, 
    // mutateAsync: loginUser
   } = loginUserQuery();
  const form = useForm<z.infer<typeof forgotPasswordSchema>>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  // Form submit handler
  const onSubmit = ({ email }: z.infer<typeof forgotPasswordSchema>) => {
    toast.success(email);
    return navigate("/auth/verification", { replace: true });
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
            title="Forgot Password"
            description="Please Enter Your Email Address To send The Verification Link To Reset Your Password."
          />
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
                            className="h-12 bg-white border-none rounded-none placeholder:font-semibold placeholder:font-syne  placeholder:md:text-center"
                            placeholder="Email Address"
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

export default ForgotPasswordPage;
