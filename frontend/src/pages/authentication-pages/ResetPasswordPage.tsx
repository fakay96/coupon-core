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
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { resetPasswordSchema } from "@/validation-schemas";
import { Input } from "@/components/ui/input";
import { toast } from "sonner";
import { resetPassword } from "@/api/authApi";
import { useState, useEffect } from "react";

const ResetPasswordPage = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [isPending, setIsPending] = useState(false);
  const [isValidToken, setIsValidToken] = useState(true);

  // Get token and email from URL
  const token = searchParams.get("token");
  const email = searchParams.get("email");

  useEffect(() => {
    // Validate that we have both token and email
    if (!token || !email) {
      console.log("Missing token or email:", { token, email });
      setIsValidToken(false);
      toast.error("Invalid or missing reset token");
      navigate("/auth/forgot-password");
    } else {
      console.log("Token and email found:", { token, email });
    }
  }, [token, email, navigate]);

  const form = useForm<z.infer<typeof resetPasswordSchema>>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      new_password: "",
      confirm_password: "",
    },
  });

  const onSubmit = async (data: z.infer<typeof resetPasswordSchema>) => {
    if (!token || !email) {
      console.log("Missing token or email in onSubmit");
      return;
    }

    try {
      console.log("Submitting reset password request:", {
        token,
        email,
        new_password: data.new_password,
      });
      
      setIsPending(true);
      const response = await resetPassword({
        token,
        email,
        new_password: data.new_password,
      });
      
      console.log("Reset password response:", response);
      toast.success("Password has been reset successfully");
      navigate("/auth/login", { replace: true });
    } catch (error) {
      console.error("Reset password error:", error);
      if (error instanceof Error) {
        toast.error(error.message);
      } else if (typeof error === 'object' && error !== null && 'message' in error) {
        toast.error((error as { message: string }).message);
      } else {
        toast.error("Failed to reset password. Please try again.");
      }
    } finally {
      setIsPending(false);
    }
  };

  if (!isValidToken) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="h-full min-h-screen bg-bg3xl bg-cover grid max-2xl:py-8 max-sm:p-4 gap-4 max-2xl:p-8">
      <div className="flex items-center justify-center md:justify-start w-full max-w-lg mx-auto">
        <div className="space-y-6 w-full mb-16">
          <Link to="/" className="flex flex-col items-center">
            <div className="">
              <img src="/images/logo.svg" alt="logo" />
            </div>
            <div className="my-6 flex flex-col gap-2">
              <h1 className="font-medium text-xl text-center">
                Reset Password
              </h1>
              <div className="">
                <p className="text-md text-center text-gray-400">
                  Enter your new password below.
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
                    name="new_password"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <Input
                            type="password"
                            className="h-12 bg-white border-none rounded-none placeholder:font-semibold placeholder:font-syne placeholder:md:text-center"
                            placeholder="New Password"
                            {...field}
                          />
                        </FormControl>
                        <FormMessage />
                      </FormItem>
                    )}
                  />
                  <FormField
                    control={form.control}
                    name="confirm_password"
                    render={({ field }) => (
                      <FormItem>
                        <FormControl>
                          <Input
                            type="password"
                            className="h-12 bg-white border-none rounded-none placeholder:font-semibold placeholder:font-syne placeholder:md:text-center"
                            placeholder="Confirm New Password"
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
                    "Reset Password"
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

export default ResetPasswordPage; 