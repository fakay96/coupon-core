import { MouseEventHandler } from "react";

const GoogleButton = ({
  onClick,
}: {
  onClick: MouseEventHandler<HTMLDivElement>;
}) => {
  return (
    <div
      onClick={onClick}
      className="md:hidden flex gap-1 items-center justify-center hover:cursor-pointer"
    >
      <img
        src={"/images/google1.png"}
        alt=""
        width={28}
        height={28}
        className="mr-2"
      />
      <p className="font-syne text-lg font-bold">Google</p>
    </div>
  );
};

export default GoogleButton;
