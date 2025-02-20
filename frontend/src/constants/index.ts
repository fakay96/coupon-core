import { FaXTwitter } from "react-icons/fa6";
import { RiInstagramFill } from "react-icons/ri";
import { MdOutlineFacebook } from "react-icons/md";
import { FaWindows } from "react-icons/fa";
import { FaApple } from "react-icons/fa";
import { FaUbuntu } from "react-icons/fa6";

export const clientImages = [
  {
    img: "/assets/KWF_weiss.png",
    title: "",
    href: "https://kwf.at",
  },
  {
    img: "/assets/OIP.png",
    title: "",
    href: "https://build.or.at/en/",
  },
  {
    img: "/assets/aau.png",
    title: "",
    href: "https://www.aau.at",
  },
  {
    img: "/assets/eu.png",
    title: "",
    href: "https://european-union.europa.eu/index_en",
  },
];

export const socials = [
  {
    icon: MdOutlineFacebook,
  },
  {
    icon: RiInstagramFill,
  },
  {
    icon: FaXTwitter,
  },
];

export const appDonwload = [
  {
    icon: FaWindows,
    title: "Windows",
  },
  {
    icon: FaApple,
    title: "Mac",
  },
  {
    icon: FaUbuntu,
    title: "Linux",
  },
];

export const authContextDefault = {
  user: null,
  logout: () => {},
  isLoading: false,
  setUser: () => {}
};



export const cardNavLinks = [
  {
    title: "Discount",
    href: "/dashboard/discount",
    img: "/images/discount.svg",
  },
  {
    title: "Price",
    href: "/dashboard/price",
    img: "/images/share.svg",
  },
  {
    title: "Cart",
    href: "/dashboard/category",
    img: "/images/shopping-cart.svg",
  },
  {
    title: "Reservation",
    href: "/dashboard/reservation",
    img: "/images/discount.svg",
  },
  {
    title: "People",
    href: "/dashboard/together",
    img: "/images/people.svg",
  },
  {
    title: "Plans",
    href: "/dashboard/plans",
    img: "/images/plans.svg",
  },
  {
    title: "History",
    href: "/dashboard/history",
    img: "/images/history.svg",
  },
  {
    title: "Account",
    href: "/dashboard/settings",
    img: "/images/settings.svg",
  },
];

export const groceryProducts = [
  {
    title: "Organic Grade A Amber Maple Syrup",
    img: "/images/amber.png",
  },
  {
    title: "Green Beans with Cracked Pepper & Sea Salt",
    img: "/images/greenBeans.png",
  },
  {
    title: "Organic Grade A Amber Maple Syrup, 32 Fl",
    img: "/images/ambersyrup.png",
  },
  {
    title: "Organic Buttermilk Pancake & Waffle Mix, 32 Ounce",
    img: "/images/butterMilk.png",
  },
];

export const options = [
  {
    img: "/images/grocery.svg",
    text: "Grocery",
  },
  {
    img: "/images/furniture.svg",
    text: "Furniture",
  },
  {
    img: "/images/fashion.svg",
    text: "Fashion",
  },
  {
    img: "/images/electronics.svg",
    text: "Electronics",
  },
  {
    img: "/images/flight.svg",
    text: "Flights",
  },
];
export const imgGrid = [
  {
    img: "/images/world.png",
    topTitle: "Select",
    bottomTitle: "Location",
  },
  {
    img: "/images/clothes.png",
    topTitle: "Select",
    bottomTitle: "Category",
  },
  {
    img: "/images/discount.png",
    topTitle: "Find",
    bottomTitle: "Discount",
  },
  {
    img: "/images/ladyTrophy.png",
    topTitle: "Claim",
    bottomTitle: "Discount",
  },
];

export const discountProducts = [
  {
    title: "vegetables",
    img: "/images/vegetables.svg",
  },
  {
    title: "Milk",
    img: "/images/milk.svg",
  },
  {
    title: "Chicken Fillet",
    img: "/images/chicken.svg",
  },
  {
    title: "Loaf Of Bread",
    img: "/images/bread.svg",
  },
  {
    title: "vegetables",
    img: "/images/vegetables.svg",
  },
  {
    title: "Milk",
    img: "/images/milk.svg",
  },
  {
    title: "Chicken Fillet",
    img: "/images/chicken.svg",
  },
  {
    title: "Loaf Of Bread",
    img: "/images/bread.svg",
  },
  {
    title: "vegetables",
    img: "/images/vegetables.svg",
  },
  {
    title: "Milk",
    img: "/images/milk.svg",
  },
  {
    title: "Chicken Fillet",
    img: "/images/chicken.svg",
  },
  {
    title: "Loaf Of Bread",
    img: "/images/bread.svg",
  },
];

export const planCard = [
  {
    planType: "Free",
    price: 0,
    dailyAccess: true,
    numberOfSavedDeals: "5",
    exclusiveDeals: false,
    notification: "Basic",
    cashBackOffer: false,
    prioritySupport: "false",
  },
  {
    planType: "Saver",
    price: 10.9,
    dailyAccess: true,
    numberOfSavedDeals: "25",
    exclusiveDeals: true,
    notification: "Customizable",
    cashBackOffer: true,
    prioritySupport: "Email",
  },
  {
    planType: "Ultimate Save",
    price: 19.9,
    dailyAccess: true,
    numberOfSavedDeals: "Unlimited",
    exclusiveDeals: true,
    notification: "true",
    cashBackOffer: true,
    prioritySupport: "24/7 Priority Support",
  },
];
