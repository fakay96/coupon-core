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
  setUser: () => {},
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
    category: "Grocery",
  },
  {
    title: "Green Beans with Cracked Pepper & Sea Salt",
    img: "/images/greenBeans.png",
    category: "Grocery",
  },
  {
    title: "Organic Grade A Amber Maple Syrup, 32 Fl",
    img: "/images/ambersyrup.png",
    category: "Grocery",
  },
  {
    title: "Organic Buttermilk Pancake & Waffle Mix, 32 Ounce",
    img: "/images/butterMilk.png",
    category: "Grocery",
  },
  {
    title: "Gray Sweatshirt",
    img: "/images/sweater.png",
    category: "Fashion",
  },
  {
    title: "Brown Cargo Pant",
    img: "/images/trousers.png",
    category: "Fashion",
  },
  {
    title: "Skirt",
    img: "/images/skirt.png",
    category: "Fashion",
  },
  {
    title: "Hoodie",
    img: "/images/jacket.png",
    category: "Fashion",
  },
  {
    title: "Fan",
    img: "/images/fan.png",
    category: "Electronics",
  },
  {
    title: "Iron",
    img: "/images/iron.png",
    category: "Electronics",
  },
  {
    title: "Samsung Galaxy",
    img: "/images/mobile.png",
    category: "Electronics",
  },
  {
    title: "HP Laptop",
    img: "/images/laptop2.png",
    category: "Electronics",
  },
  {
    title: "Table",
    img: "/images/table.png",
    category: "Furniture",
  },
  {
    title: "Rustic Wooden Stool",
    img: "/images/stool.png",
    category: "Furniture",
  },
  {
    title: "Gray Fabric Chair",
    img: "/images/fabric_chair.png",
    category: "Furniture",
  },
  {
    title: "HP Laptop",
    img: "/images/laptop2.png",
    category: "Furniture",
  },
  {
    title: "Flight Ticket",
    img: "/images/flight.png",
    category: "Flights",
  },
  {
    title: "Flight Ticket",
    img: "/images/flight.png",
    category: "Flights",
  },
  {
    title: "Flight Ticket",
    img: "/images/flight.png",
    category: "Flights",
  },
  {
    title: "Flight Ticket",
    img: "/images/flight.png",
    category: "Flights",
  },
];

export const categoryList = [
  "All",
  "Flights",
  "Furniture",
  "Grocery",
  "Fashion",
  "Electronics",
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
    img: "/images/flight.svg",
    text: "Flights",
  },
  {
    img: "/images/electronics.svg",
    text: "Electronics",
  },
];
export const imgGrid = [
  {
    img: "/images/world.png",
    topTitle: "Select",
    bottomTitle: "Location",
    href: "",
  },
  {
    img: "/images/clothes.png",
    topTitle: "Select",
    bottomTitle: "Category",
    href: "/dashboard/category-search",
  },
  {
    img: "/images/discount.png",
    topTitle: "Find",
    bottomTitle: "Discount",
    href: "",
  },
  {
    img: "/images/ladyTrophy.png",
    topTitle: "Claim",
    bottomTitle: "Discount",
    href: "",
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
    title: "Bread",
    img: "/images/bread.svg",
  },
  
];

export const imgs = [
  { img: "/images/groceries.png", href: "Grocery" },
  { img: "/images/aeroplane.png", href: "Flights" },
  { img: "/images/fashionGirl.png", href: "Fashion" },
  { img: "/images/electronicsImg.png", href: "Electronics" },
  { img: "/images/furniture.png", href: "Furniture" },
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

export const discountFilters = [
  {
    title: "Sort By",
    item1: "Distance",
    item2: "Rating",
    item3: "Price Ascending",
    item4: "Price Descending",
  },
  {
    title: "Category",
    item1: "Groceries",
    item2: "Furniture",
    item3: "Electronics",
    item4: "Fashion",
  },
  {
    title: "Past 7 Days",
    item1: "Milk",
    item2: "cheap Flights",
    item3: "Brown Furniture Chair",
    item4: "Laptop Charger",
  },
  {
    title: "Past 30 Days",
    item1: "Milk",
    item2: "cheap Flights",
    item3: "Brown Furniture Chair",
    item4: "Laptop Charger",
  },
];
