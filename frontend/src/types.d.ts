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
  date_joined: string;
  email: string;
  id: number;
  is_active: boolean;
  is_staff: boolean;
  last_login: null;
  role: string;
  username: string;
};

