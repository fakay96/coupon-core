import { Link } from "react-router-dom";

const AuthHeader = ({
  title,
  description,
}: {
  title: string;
  description: string;
}) => {
  return (
    <Link to="/" className="flex flex-col items-center md:hidden">
      <div className="">
        <img src="/images/logo.svg" alt="log" />
      </div>
      <div className="my-6 flex flex-col gap-2">
        <h1 className="font-medium text-xl text-center">{title}</h1>
        <div className="">
          <p className="text-md text-center text-gray-400">{description}</p>
          
        </div>
      </div>
    </Link>
  );
};

export default AuthHeader;
