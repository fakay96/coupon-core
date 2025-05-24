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
import { Link, useNavigate } from "react-router-dom";
import { forgotPasswordSchema } from "@/validation-schemas";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { passwordReset } from "@/api/authApi";
import { useState } from "react";

const ForgotPasswordPage = () => {
  const navigate = useNavigate();
  const [isPending, setIsPending] = useState(false);

  const form = useForm<z.infer<typeof forgotPasswordSchema>>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: "",
    },
  });

  // Form submit handler
  const onSubmit = async ({ email }: z.infer<typeof forgotPasswordSchema>) => {
    try {
      setIsPending(true);
      await passwordReset({ email, force_resend: false });
      
      toast.success("Password reset link has been sent to your email");
      navigate("/auth/login", {
        replace: true,
      });
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to send reset link");
    } finally {
      setIsPending(false);
    }
  };

  return (
    <div className="h-full min-h-screen bg-bg3xl bg-cover grid  max-2xl:py-8 max-sm:p-4  gap-4 max-2xl:p-8">
      <div className="flex items-center justify-center md:justify-start w-full max-w-lg mx-auto">
        <div className="space-y-6 w-full mb-16">
          <Link to="/" className="flex flex-col items-center">
            <div className="">
              <img src="/images/logo.svg" alt="log" />
            </div>
            <div className="my-6 flex flex-col gap-2">
              <h1 className="font-medium text-xl text-center">
                Forgot Password
              </h1>
              <div className="">
                <p className="text-md text-center text-gray-400">
                  Enter your email address and we'll send you a link to reset your password.
                </p>
              </div>
            </div>
          </Link>
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
                    <Loader className="size-4 animate-spin" />
                  ) : (
                    "Send Reset Link"
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
