import NavbarComponent from "@/components/landing-page-components/Navbar";
import HomePageSlider from "@/components/landing-page-components/HomePageSlider";
// import DiscoverDiscount from "@/components/landing-page-components/DiscoverDiscount";
import WhyDishpal from "@/components/landing-page-components/WhyDishpal";
import TakeA60SecondsSurvey from "@/components/landing-page-components/TakeA60SecondsSurvey";
import FAQ from "@/components/landing-page-components/FAQ";
import MissionVision from "@/components/landing-page-components/MissionVision";
import Clients from "@/components/landing-page-components/Clients";
import Socials from "@/components/landing-page-components/Socials";

const LandingPage = () => {
  return (
    <div className="overflow-hidden relative" id="toppage">
      <NavbarComponent />
      <section className="max-w-screen-xl mx-auto lg:mt-16">
        <HomePageSlider />
        {/* <div className="mt-16 sm:mt-32 px-4">
          <DiscoverDiscount />
        </div> */}
        <div className="my-16 sm:my-32">
          <WhyDishpal />
        </div>
        <div className="space-y-16 sm:space-y-32 px-4">
          <TakeA60SecondsSurvey />
          <FAQ />
          <MissionVision />
        </div>
      </section>
      <Clients />
      <div className="max-w-screen-xl mx-auto px-4">
        <Socials />
      </div>
    </div>
  );
};

export default LandingPage;
