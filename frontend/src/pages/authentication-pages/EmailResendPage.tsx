import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { retryEmailTokenMutation } from "@/queries/auth-queries";
import AuthHeader from "@/components/auth-component/header";

const EmailResendPage = () => {
  const { state } = useLocation();
  const name = state?.email?.split("@")[0];
  const { mutateAsync } = retryEmailTokenMutation();
  const navigate = useNavigate();
  const retryEmailToken = async () => {
    if (!state?.email) {
      toast.error("Email required. Login Again");
      return navigate("/auth/login");
    }
    toast.promise(mutateAsync({ email: state?.email, force_resend: true }), {
      loading: `${name}, Dishpal AI is sending your verification email now`,
      success: `${name}, Check your email now to get your verification code`,
      error: (error) => error.message,
    });
  };

  return (
    <div className="h-full min-h-screen bg-bg3xl bg-cover   gap-4 max-2xl:p-8">
      <div className="flex flex-col items-center justify-center md:justify-start w-full max-w-lg mx-auto">
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
              Check Your Inbox
            </h1>
            <p className="">
              Click The Link Sent To Your Mail{" "}
              {state?.email &&
                state?.email?.charAt(0) +
                  "***********" +
                  state?.email?.split("@")[1]}{" "}
            </p>
            <p className="text-center hidden md:flex w-full justify-center">
              Email Not Sent?{" "}
              <span
                className="text-vividOrange mx-1 hover:cursor-pointer"
                onClick={retryEmailToken}
              >
                Try Again
              </span>{" "}
              or{" "}
              <span
                onClick={() =>
                  navigate(`/auth/verification`, {
                    state: { email: state?.email },
                  })
                }
                className="text-vividOrange mx-1 hover:cursor-pointer"
              >
                Verify
              </span>
            </p>
          </div>
          <div className="">
            <AuthHeader title="Check Your Inbox" />

            <div className="text-center flex flex-col text-slate-400 md:hidden">
              <p className="">Please Click The Link Sent To You</p>
              <p className="">
                Didn't Receive Any Mail?
                <span
                  onClick={retryEmailToken}
                  className="text-vividOrange hover:cursor-pointer"
                >
                  {" "}
                  Try Again
                </span>
                <span className="mx-1">or</span>
                <span
                  onClick={() =>
                    navigate(`/auth/verification`, {
                      state: { email: state?.email },
                    })
                  }
                  className="text-vividOrange hover:cursor-pointer"
                >
                  Verify
                </span>
              </p>
            </div>
          </div>
          <div className="space-y-6 flex justify-center">
            <img src="/images/message.png" className="max-sm:size-96" alt="" />
          </div>
        </div>
      </div>
    </div>
  );
};

export default EmailResendPage;
