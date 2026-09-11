import React, { createContext, useContext, useState, useEffect } from 'react';
import { supabase } from '../lib/supabaseClient';

export interface User {
  name: string;
  email: string;
}

export interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  signup: (name: string, email: string, password: string) => Promise<{ success: boolean; error?: string; needsConfirmation?: boolean }>;
  logout: () => Promise<void>;
}

// Demo bypass – works without Supabase
const DEMO = { email: 'demo@satquery.ai', password: 'SatQuery@123', name: 'Demo Explorer' };
const DEMO_USER_KEY = 'satquery_demo_user';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 1. Restore demo session if present
    const stored = localStorage.getItem(DEMO_USER_KEY);
    if (stored) {
      try { setUser(JSON.parse(stored)); } catch { /* ignore */ }
      setLoading(false);
      return;
    }

    // 2. Check real Supabase session
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user) {
        setUser({
          email: session.user.email || '',
          name: session.user.user_metadata?.full_name || 'User',
        });
      }
      setLoading(false);
    });

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      // Don't override demo session from Supabase events
      if (localStorage.getItem(DEMO_USER_KEY)) return;
      if (session?.user) {
        setUser({
          email: session.user.email || '',
          name: session.user.user_metadata?.full_name || 'User',
        });
      } else {
        setUser(null);
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const login = async (email: string, password: string): Promise<{ success: boolean; error?: string }> => {
    const trimmed = email.trim().toLowerCase();

    // Demo shortcut — no Supabase needed
    if (trimmed === DEMO.email.toLowerCase() && password === DEMO.password) {
      const demoUser: User = { name: DEMO.name, email: DEMO.email };
      localStorage.setItem(DEMO_USER_KEY, JSON.stringify(demoUser));
      setUser(demoUser);
      return { success: true };
    }

    // Real Supabase login
    const { error } = await supabase.auth.signInWithPassword({ email: trimmed, password });
    if (error) return { success: false, error: error.message };
    return { success: true };
  };

  const signup = async (
    name: string,
    email: string,
    password: string
  ): Promise<{ success: boolean; error?: string; needsConfirmation?: boolean }> => {
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password,
      options: { data: { full_name: name } },
    });

    if (error) return { success: false, error: error.message };

    // Supabase returns a session immediately if email confirmation is OFF.
    // If confirmation is ON, session will be null and we inform the UI.
    const needsConfirmation = !data.session;
    return { success: true, needsConfirmation };
  };

  const logout = async (): Promise<void> => {
    localStorage.removeItem(DEMO_USER_KEY);
    setUser(null);
    await supabase.auth.signOut();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#080c10] text-emerald-400 text-sm">
        Loading...
      </div>
    );
  }

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, login, signup, logout }}>
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

export default AuthContext;
