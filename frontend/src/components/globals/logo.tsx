import { Link } from "react-router-dom";
const Logo = () => {
  return (
    <Link to="/dashboard" className="grid">
      <img
       
        alt="dispal"
        src="/images/logo1.svg"
        className="hover:cursor-pointer hover:scale-105 duration-500 size-[60px] sm:size-[100px] transition-all"
      />
    </Link>
  );
};

export default Logo;
