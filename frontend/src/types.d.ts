import { AxiosResponse } from "axios";

interface loginCredentials {
  password: string;
  email: string;
}

interface authContextType {
  user: userT | null | undefined;
  logout: () => void;
  isLoading: boolean;
  setUser: React.Dispatch<React.SetStateAction<userT | null | undefined>>;
}

interface RegisterUserData {
  username: string;
  email: string;
  password: string;
  confirm_password: string;
}

export type userT = {
  preferences: string;
  first_name: string;
  last_name: string;
  phone_number: null;
};

export interface Product {
  title: string;
  img: string;
  category: string;
}

export interface SearchInputBoxProps {
  categoryItems: Product[];
  setCategoryItems: React.Dispatch<React.SetStateAction<Product[]>>;
  category: string | null;
  search: string | null;
}

export interface categoriesT {
  id: number;
  image: string;
  name: string;
}

export interface DiscountItemT {
  title: string;
  img: string;
  category: string;
}

export type Message = {
  id: string;
  content: string;
  sender: "user" | "dishpal";
  timestamp: Date;
};