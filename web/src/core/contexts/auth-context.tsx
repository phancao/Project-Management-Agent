'use client';

// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Auth Context Provider for managing user authentication state.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import {
    type User,
    getStoredToken,
    getStoredUser,
    login as apiLogin,
    logout as apiLogout,
    register as apiRegister,
    type LoginCredentials,
    type RegisterData,
    getCurrentUser,
} from '~/core/api/auth';

interface AuthContextType {
    user: User | null;
    token: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    login: (credentials: LoginCredentials) => Promise<void>;
    register: (data: RegisterData) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Routes that don't require authentication
const PUBLIC_ROUTES = ['/login', '/register', '/landing'];

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();
    const pathname = usePathname();

    // Check auth on mount
    useEffect(() => {
        const initAuth = async () => {
            const storedToken = getStoredToken();
            const storedUser = getStoredUser();

            if (storedToken && storedUser) {
                // Immediately set user from storage to prevent redirect flash
                setToken(storedToken);
                setUser(storedUser);
                setIsLoading(false);

                // Then validate token in background
                const validUser = await getCurrentUser();
                if (validUser) {
                    // Update with fresh user data
                    setUser(validUser);
                } else {
                    // Token invalid, clear storage and state
                    apiLogout();
                    setToken(null);
                    setUser(null);
                }
            } else {
                setIsLoading(false);
            }
        };

        initAuth();
    }, []);

    // Redirect to login if not authenticated (except for public routes)
    useEffect(() => {
        if (!isLoading && !user && !PUBLIC_ROUTES.some(route => pathname?.startsWith(route))) {
            // Redirect to login for protected routes
            router.push('/login');
        }
    }, [isLoading, user, pathname, router]);

    const login = useCallback(async (credentials: LoginCredentials) => {
        const response = await apiLogin(credentials);
        setToken(response.access_token);
        setUser(response.user);
        router.push('/pm/chat');
    }, [router]);

    const register = useCallback(async (data: RegisterData) => {
        const response = await apiRegister(data);
        setToken(response.access_token);
        setUser(response.user);
        router.push('/pm/chat');
    }, [router]);

    const logout = useCallback(() => {
        apiLogout();
        setToken(null);
        setUser(null);
        router.push('/login');
    }, [router]);

    return (
        <AuthContext.Provider
            value={{
                user,
                token,
                isLoading,
                isAuthenticated: !!user,
                login,
                register,
                logout,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
