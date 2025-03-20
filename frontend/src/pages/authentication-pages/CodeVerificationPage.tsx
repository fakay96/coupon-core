import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Loader } from "lucide-react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { verificationCodeSchema } from "@/validation-schemas";
import { toast } from "sonner";
import { verifyEmailTokenMutation } from "@/queries/auth-queries";
import AuthHeader from "@/components/auth-component/header";
import { Input } from "@/components/ui/input";
import { useState } from "react";

const CodeVerificationPage = () => {
  const [emailField, setEmailField] = useState(false);
  // const [userEmail, setUserEmail] = useState("");
  const form = useForm<z.infer<typeof verificationCodeSchema>>({
    resolver: zodResolver(verificationCodeSchema),
    defaultValues: {
      code: "",
      userEmail: "",
    },
  });
  const navigate = useNavigate();
  const { state } = useLocation();
  const name = state?.email?.split("@")[0] ?? form.getValues("userEmail");
  const { mutateAsync, isPending } = verifyEmailTokenMutation();


  const onSubmit = ({ code,userEmail }: z.infer<typeof verificationCodeSchema>) => {
    if (state === null && !userEmail) {
      setEmailField(true);
      return toast.error("Email required");
    }
    toast.promise(
      mutateAsync({ email: state?.email ?? userEmail, token: code }).then(
        () => {
          navigate("/auth/login", { replace: true });
        }
      ),
      {
        loading: `${name}, Dishpal AI is verifying your token now`,
        success: `${name}, Dishpal AI have successfully verified your token.`,
        error: (error) => error.message,
      }
    );
  };

  return (
    <div className="h-full min-h-screen bg-bg3xl bg-cover   gap-4 max-2xl:p-8">
      <div className="flex flex-col items-center justify-center md:justify-start w-full max-w-xl mx-auto">
        <Link
          to="/"
          className="hidden flex-col items-center my-8 mb-16 md:flex"
        >
          <div className="">
            <img src="/images/logo.svg" alt="log" />
          </div>
        </Link>
        <div className="space-y-6 w-full mb-16">
          <div className="hidden md:block space-y-3 mb-3 text-center">
            <h1 className="font-bold text-xl xxx:text-3xl max-xx:text-center  font-syne">
              Verification Code
            </h1>
            <p className="">
              Please Enter Verification Code Sent To Your Mail{" "}
              {state?.email &&
                (state?.email ?? form.getValues("userEmail"))?.charAt(0) +
                  "***********" +
                  (state?.email ?? form.getValues("userEmail"))?.split("@")[1]}{" "}
            </p>
          </div>
          <AuthHeader
            title="Verification Code"
            description="Please Enter The Verification Code Sent To "
          />

          <div className="space-y-6">
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 flex flex-col items-center max-w-96 mx-auto"
              >
                <FormField
                  control={form.control}
                  name="code"
                  render={({ field }) => (
                    <FormItem className=" w-full">
                      <FormLabel>Verification Code</FormLabel>
                      <FormControl>
                        <Input
                          className="w-full placeholder:text-gray-300 bg-white hover:shadow-2xl"
                          placeholder="28e9a89a-9220-4d42-b28f-1efaa26d6303"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />

                {emailField && (
                  <div className="w-full">
                    <FormField
                      control={form.control}
                      name="userEmail"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Email</FormLabel>
                          <FormControl>
                            <Input placeholder="email@gmail.com" {...field} />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </div>
                )}

                <Button
                  type="submit"
                  className="w-full bg-vividOrange py-6 md:rounded-none hover:bg-orange-600/60 md:text-black font-semibold font-syne"
                  disabled={isPending}
                >
                  {isPending ? (
                    <Loader className=" size-4 animate-spin" />
                  ) : (
                    <>Verify</>
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
