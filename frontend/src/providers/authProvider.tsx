import React, { createContext, useContext, useState, useEffect } from 'react';
import Cookies from 'js-cookie';

interface User {
  id: string;
  name: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  register: (email: string, password: string, name: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing session
    const checkSession = async () => {
      try {
        const token = Cookies.get('auth_token');
        if (token) {
          // TODO: Validate token with backend
          // For now, just set a dummy user
          setUser({
            id: '1',
            name: 'Test User',
            email: 'test@example.com'
          });
        }
      } catch (error) {
        console.error('Error checking session:', error);
      } finally {
        setLoading(false);
      }
    };

    checkSession();
  }, []);

  const login = async (email: string, _password: string) => {
    try {
      // TODO: Implement actual login
      // For now, just set a dummy user
      setUser({
        id: '1',
        name: 'Test User',
        email
      });
      Cookies.set('auth_token', 'dummy_token');
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  };

  const logout = () => {
    setUser(null);
    Cookies.remove('auth_token');
  };

  const register = async (email: string, _password: string, name: string) => {
    try {
      // TODO: Implement actual registration
      // For now, just set a dummy user
      setUser({
        id: '1',
        name,
        email
      });
      Cookies.set('auth_token', 'dummy_token');
    } catch (error) {
      console.error('Registration error:', error);
      throw error;
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, register }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}; 