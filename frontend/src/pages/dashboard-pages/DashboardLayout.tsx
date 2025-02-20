import { Outlet } from "react-router-dom";
// import { getUserInfoQuery } from "@/queries/auth-queries";
// import { Navigate } from "react-router-dom";
const DashboardLayout = () => {
  return <Outlet />
  // const { isLoading, data: user } = getUserInfoQuery();
  // if (isLoading) {
  //   return <></>;
  // } else {
  //   if (user) {
  //     return (
  //       <div>
  //         <Outlet />
  //       </div>
  //     );
  //   } else return <Navigate to="/auth/login" />;
  // }
};

export default DashboardLayout;
