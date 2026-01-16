// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

/**
 * Auth API functions for login, register, and user session management.
 */

// Use relative URL so requests go through the gateway (nginx on port 8080)
const API_URL = '';

export interface User {
    id: string;
    email: string;
    name: string;
    role: string;
}

export interface AuthResponse {
    access_token: string;
    token_type: string;
    expires_in: number;
    user: User;
}

export interface LoginCredentials {
    email: string;
    password: string;
}

export interface RegisterData {
    email: string;
    password: string;
    name: string;
}

const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';

/**
 * Store auth data in localStorage
 */
export function storeAuthData(response: AuthResponse): void {
    if (typeof window !== 'undefined') {
        localStorage.setItem(TOKEN_KEY, response.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(response.user));
    }
}

/**
 * Clear auth data from localStorage
 */
export function clearAuthData(): void {
    if (typeof window !== 'undefined') {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
    }
}

/**
 * Get stored token
 */
export function getStoredToken(): string | null {
    if (typeof window !== 'undefined') {
        return localStorage.getItem(TOKEN_KEY);
    }
    return null;
}

/**
 * Get stored user
 */
export function getStoredUser(): User | null {
    if (typeof window !== 'undefined') {
        const userJson = localStorage.getItem(USER_KEY);
        if (userJson) {
            try {
                return JSON.parse(userJson) as User;
            } catch {
                return null;
            }
        }
    }
    return null;
}

/**
 * Login with email and password
 */
export async function login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(credentials),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Login failed');
    }

    const data = await response.json() as AuthResponse;
    storeAuthData(data);
    return data;
}

/**
 * Register a new user
 */
export async function register(data: RegisterData): Promise<AuthResponse> {
    const response = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });

    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Registration failed');
    }

    const authData = await response.json() as AuthResponse;
    storeAuthData(authData);
    return authData;
}

/**
 * Get current user from token
 */
export async function getCurrentUser(): Promise<User | null> {
    const token = getStoredToken();
    if (!token) {
        return null;
    }

    try {
        const response = await fetch(`${API_URL}/api/auth/me`, {
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });

        if (response.status === 401) {
            // Only clear auth data on explicit unauthorized response
            clearAuthData();
            return null;
        }

        if (!response.ok) {
            // Other errors (500, network issues) - don't clear auth, just fail silently
            console.warn('[Auth] Failed to validate token, keeping existing session');
            return null;
        }

        return await response.json() as User;
    } catch (error) {
        console.warn('[Auth] Error validating token:', error);
        return null;
    }
}

/**
 * Logout - clear stored auth data
 */
export function logout(): void {
    clearAuthData();
}

/**
 * Get auth header for API requests
 */
export function getAuthHeader(): Record<string, string> {
    const token = getStoredToken();
    if (token) {
        return { 'Authorization': `Bearer ${token}` };
    }
    return {};
}
