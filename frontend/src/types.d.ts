import { AxiosResponse } from "axios";

interface loginCredentials {
  email: string;
  password: string;
  username: string;
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
  created_at: string;
  id: number;
  location: string;
  phone_number: string;
  preferences: string;
  updated_at: string;
  user: {
    email: string;
    first_name: string;
    id: number;
    last_name: string;
    phone_number: null;
    username: string;
  };
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