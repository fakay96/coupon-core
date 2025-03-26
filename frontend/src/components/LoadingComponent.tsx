import BounceLoader from "react-spinners/BounceLoader";

const LoadingComponent = () => {
  return (
    <div className="h-screen w-full flex justify-center items-center">
      <div className="flex flex-col items-center space-y-8">
        <BounceLoader
          color="#f08c02"
          loading
          size={91}
          speedMultiplier={1}
        />
        <h1 className="text-5xl text-orange-50 animate-pulse font-bold">
          REMITELY
        </h1>
      </div>
    </div>
  );
};

export default LoadingComponent;
