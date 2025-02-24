import SignInPage from "@/pages/authentication-pages/SigninPage";
import SignUpPage from "@/pages/authentication-pages/SignupPage";
import { Routes, Route } from "react-router-dom";
import DiscountPage from "@/pages/dashboard-pages/DiscountPage";
import DashboardLayout from "@/pages/dashboard-pages/DashboardLayout";
import PricePage from "@/pages/dashboard-pages/PricePage";
import CategoryPage from "@/pages/dashboard-pages/CategoryPage";
import ReservationPage from "@/pages/dashboard-pages/ReservationPage";
import TogetherPage from "@/pages/dashboard-pages/TogetherPage";
import PlanPage from "@/pages/dashboard-pages/PlanPage";
import HistoryPage from "@/pages/dashboard-pages/HistoryPage";
import SettingsPage from "@/pages/dashboard-pages/SettingsPage";
import DashboardPage from "@/pages/dashboard-pages/Dashboard";
import ScrollToTop from "@/hooks/ScrollToTop";
import ForgotPasswordPage from "@/pages/authentication-pages/ForgotPasswordPage";
import CodeVerificationPage from "@/pages/authentication-pages/CodeVerificationPage";
import NotFoundPage from "@/pages/NotFoundPage";
import Homepage from "@/pages/HomePage";
import ContinuePage from "@/pages/dashboard-pages/ContinuePage";
import CategorySearchPage from "@/pages/dashboard-pages/CategorySearchPage";

const AppRoutes = () => {
  return (
    <>
    <ScrollToTop />
    <Routes>
      <Route path="/" element={<Homepage />} />

      <Route path="/auth/login" element={<SignInPage />} />
      <Route path="/auth/register" element={<SignUpPage />} />
      <Route path="/auth/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/auth/verification" element={<CodeVerificationPage />} />
      
      <Route path="/dashboard" element={<DashboardLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="discount" element={<DiscountPage />} />
        <Route path="price" element={<PricePage />} />
        <Route path="category-search" element={<CategorySearchPage />} />
        <Route path="category" element={<CategoryPage />} />
        <Route path="reservation" element={<ReservationPage />} />
        <Route path="together" element={<TogetherPage />} />
        <Route path="plans" element={<PlanPage />} />
        <Route path="continue" element={<ContinuePage />} />
        <Route path="history" element={<HistoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>


        <Route path="*" element={<NotFoundPage />} />
    </Routes>
    </>
  );
};

export default AppRoutes;
