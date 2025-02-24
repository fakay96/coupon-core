import { Link } from "react-router-dom";
const Logo = () => {
  return (
    <Link to="/" className="grid">
      <img
       
        alt="dispal"
        src="/images/logo.svg"
        className="hover:cursor-pointer hover:scale-105 duration-500 size-[60px] sm:size-[100px] transition-all"
      />
    </Link>
  );
};

export default Logo;
