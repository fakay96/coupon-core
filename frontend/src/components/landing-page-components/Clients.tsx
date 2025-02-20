import { clientImages } from "@/constants";

const Clients = () => {
  return (
    <section className="dark:bg-white/30 bg-black mt-16 sm:mt-32">
      <div className=" flex justify-center items-center h-24 sm:h-[138px]">
        {clientImages?.map(({ href, img }, index) => (
          <a
            key={index}
            rel="noopener noreferrer"
            target="_blank"
            href={href}
            className="w-full flex justify-evenly items-center"
          >
            <img
              src={img}
              className={`${
                index === 0 || index === 1 ? "max-sm:w-8" : "max-sm:!w-20"
              } ${
                index === 0 || index === 1 ? "sm:w-[90px]" : "sm:w-[200px]"
              } `}
              alt={href}
            />
          </a>
        ))}
      </div>
    </section>
  );
};

export default Clients;
