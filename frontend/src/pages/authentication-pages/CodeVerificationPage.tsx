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
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { verificationCodeSchema } from "@/validation-schemas";
import { toast } from "sonner";
import { verifyEmailTokenMutation } from "@/queries/auth-queries";
import AuthHeader from "@/components/auth-component/header";
import { Input } from "@/components/ui/input";
import { useState, useEffect } from "react";
import { resetPassword } from "@/api/authApi";

const resetPasswordSchema = z.object({
  code: z.string().min(1, { message: "Verification code is required" }),
  userEmail: z.string().email({ message: "Enter a valid email" }),
  new_password: z.string().min(8, { message: "Password must be at least 8 characters" }),
  confirm_password: z.string().min(8, { message: "Password must be at least 8 characters" }),
}).refine((data) => data.new_password === data.confirm_password, {
  message: "Passwords don't match",
  path: ["confirm_password"],
});

const CodeVerificationPage = () => {
  const [emailField, setEmailField] = useState(false);
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { state } = useLocation();
  const { mutateAsync, isPending: isVerifying } = verifyEmailTokenMutation();
  const [isResetting, setIsResetting] = useState(false);
  const [pageMode, setPageMode] = useState<"activation" | "reset" | "verification">("verification");

  const form = useForm<z.infer<typeof verificationCodeSchema | typeof resetPasswordSchema>>({
    resolver: zodResolver(pageMode === "reset" ? resetPasswordSchema : verificationCodeSchema),
    defaultValues: {
      code: "",
      userEmail: "",
      new_password: "",
      confirm_password: "",
    },
  });

  const name = state?.email?.split("@")[0] ?? form.getValues("userEmail");

  // Check if this is a password reset request
  useEffect(() => {
    const token = searchParams.get("token");
    const email = searchParams.get("email");
    const mode = searchParams.get("mode");

    if (token && email) {
      if (mode === "reset") {
        setPageMode("reset");
      } else if (mode === "activation") {
        setPageMode("activation");
      } else {
        setPageMode("verification");
      }
      form.setValue("userEmail", email);
      form.setValue("code", token);
      form.clearErrors();
      form.reset(form.getValues());
    }
  }, [searchParams, form]);

  const onSubmit = async (data: any) => {
    const { code, userEmail, new_password } = data;
    if (!state?.email && !userEmail) {
      setEmailField(true);
      return toast.error("Email required");
    }

    const email = state?.email ?? userEmail;

    if (pageMode === "reset") {
      try {
        setIsResetting(true);
        const response = await resetPassword({
          token: code,
          email,
          new_password,
        });
        toast.success(response.message || "Password has been reset successfully");
        navigate("/auth/login", { replace: true });
      } catch (error) {
        toast.error(error instanceof Error ? error.message : "Failed to reset password");
      } finally {
        setIsResetting(false);
      }
    } else {
      toast.promise(
        mutateAsync({ email, token: code }).then(() => {
          const successMessage = pageMode === "activation" 
            ? "Your account has been activated successfully"
            : "Your email has been verified successfully";
          toast.success(successMessage);
          navigate("/auth/login", { replace: true });
        }),
        {
          loading: `${name}, Dishpal AI is ${pageMode === "activation" ? "activating your account" : "verifying your token"} now`,
          success: `${name}, Dishpal AI has successfully ${pageMode === "activation" ? "activated your account" : "verified your token"}.`,
          error: (error) => error.message,
        }
      );
    }
  };

  return (
    <div className="h-full min-h-screen bg-bg3xl bg-cover gap-4 max-2xl:p-8">
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
            <h1 className="font-bold text-xl xxx:text-3xl max-xx:text-center font-syne">
              {pageMode === "activation" ? "Activate Account" : pageMode === "reset" ? "Reset Password" : "Verification Code"}
            </h1>
            <p className="">
              {pageMode === "activation" 
                ? "Please enter the activation code to activate your account"
                : pageMode === "reset"
                ? "Please enter your new password"
                : "Please Enter Verification Code Sent To Your Mail"}{" "}
              {state?.email &&
                (state?.email ?? form.getValues("userEmail"))?.charAt(0) +
                  "***********" +
                  (state?.email ?? form.getValues("userEmail"))?.split("@")[1]}{" "}
            </p>
          </div>
          <AuthHeader
            title={pageMode === "activation" ? "Activate Account" : pageMode === "reset" ? "Reset Password" : "Verification Code"}
            description={
              pageMode === "activation"
                ? "Enter the activation code to activate your account"
                : pageMode === "reset"
                ? "Enter your new password"
                : "Please Enter The Verification Code Sent To "
            }
          />

          <div className="space-y-6">
            <Form {...form}>
              <form
                onSubmit={form.handleSubmit(onSubmit)}
                className="space-y-8 flex flex-col items-center max-w-96 mx-auto"
              >
                {pageMode !== "reset" && (
                  <FormField
                    control={form.control}
                    name="code"
                    render={({ field }) => (
                      <FormItem className="w-full">
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
                )}

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

                {pageMode === "reset" && (
                  <>
                    <FormField
                      control={form.control}
                      name="new_password"
                      render={({ field }) => (
                        <FormItem className="w-full">
                          <FormLabel>New Password</FormLabel>
                          <FormControl>
                            <Input
                              type="password"
                              className="w-full placeholder:text-gray-300 bg-white hover:shadow-2xl"
                              placeholder="Enter your new password"
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
                        <FormItem className="w-full">
                          <FormLabel>Confirm Password</FormLabel>
                          <FormControl>
                            <Input
                              type="password"
                              className="w-full placeholder:text-gray-300 bg-white hover:shadow-2xl"
                              placeholder="Confirm your new password"
                              {...field}
                            />
                          </FormControl>
                          <FormMessage />
                        </FormItem>
                      )}
                    />
                  </>
                )}

                <Button
                  type="submit"
                  className="w-full bg-vividOrange py-6 md:rounded-none hover:bg-orange-600/60 md:text-black font-semibold font-syne"
                  disabled={isVerifying || isResetting}
                >
                  {(isVerifying || isResetting) ? (
                    <Loader className="size-4 animate-spin" />
                  ) : (
                    <>{pageMode === "reset" ? "Reset Password" : pageMode === "activation" ? "Activate Account" : "Verify"}</>
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
