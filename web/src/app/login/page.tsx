'use client';

// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import { useState, useEffect } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Rocket, Loader2 } from 'lucide-react';

// Microsoft Icon Component
function MicrosoftIcon({ className }: { className?: string }) {
    return (
        <svg className={className} viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="1" y="1" width="9" height="9" fill="#F25022" />
            <rect x="11" y="1" width="9" height="9" fill="#7FBA00" />
            <rect x="1" y="11" width="9" height="9" fill="#00A4EF" />
            <rect x="11" y="11" width="9" height="9" fill="#FFB900" />
        </svg>
    );
}

// Use relative URL so requests go through the gateway
const API_URL = '';

export default function LoginPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [isSSOLoading, setIsSSOLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [isCheckingSSO, setIsCheckingSSO] = useState(true);

    // Handle OAuth callback (token in URL from Azure AD redirect)
    useEffect(() => {
        const token = searchParams.get('token');
        const userEmail = searchParams.get('user_email');
        const userName = searchParams.get('user_name');
        const userId = searchParams.get('user_id');
        const errorParam = searchParams.get('error');
        const errorDescription = searchParams.get('error_description');

        if (errorParam) {
            setError(errorDescription || errorParam);
            setIsCheckingSSO(false);
            return;
        }

        if (token && userEmail && userName && userId) {
            // Store auth data from OAuth callback
            localStorage.setItem('auth_token', token);
            localStorage.setItem('auth_user', JSON.stringify({
                id: userId,
                email: decodeURIComponent(userEmail),
                name: decodeURIComponent(userName),
                role: 'user',
            }));
            // Redirect to app
            router.push('/pm/chat');
            return;
        }

        setIsCheckingSSO(false);
    }, [searchParams, router]);

    const handleMicrosoftLogin = () => {
        setIsSSOLoading(true);
        setError(null);
        // Redirect to Azure AD OAuth flow
        window.location.href = `${API_URL}/api/auth/azure/login`;
    };

    // Show loading while checking OAuth callback
    if (isCheckingSSO) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1E398D] via-[#14B795] to-[#1C9AD6]">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-white animate-spin mx-auto mb-4" />
                    <p className="text-white">Loading...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1E398D] via-[#14B795] to-[#1C9AD6]">
            {/* Background effects */}
            <div className="absolute inset-0 bg-[url('/grid.svg')] bg-center opacity-10"></div>
            <div className="absolute inset-0">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-[#14B795] rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse"></div>
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-[#1E398D] rounded-full mix-blend-multiply filter blur-3xl opacity-20 animate-pulse delay-1000"></div>
            </div>

            {/* Login Card */}
            <div className="relative z-10 w-full max-w-md mx-4">
                <div className="backdrop-blur-xl bg-white/10 dark:bg-slate-900/40 border border-white/20 dark:border-slate-700/50 rounded-2xl shadow-2xl p-8">
                    {/* Logo & Title */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-[#1E398D] to-[#14B795] shadow-lg shadow-[#1E398D]/30 mb-4">
                            <Rocket className="w-8 h-8 text-white" />
                        </div>
                        <h1 className="text-2xl font-bold text-white mb-2">
                            🌌 Galaxy AI Project Manager
                        </h1>
                        <p className="text-gray-200 text-sm">
                            Sign in with your company account
                        </p>
                    </div>

                    {/* Error Message */}
                    {error && (
                        <div className="mb-6 p-3 rounded-lg bg-[#ED1C29]/20 border border-[#ED1C29]/30 text-red-200 text-sm">
                            {error}
                        </div>
                    )}

                    {/* Microsoft SSO Button */}
                    <button
                        onClick={handleMicrosoftLogin}
                        disabled={isSSOLoading}
                        className="w-full py-4 px-4 rounded-xl bg-white hover:bg-gray-100 text-gray-800 font-semibold transition-all shadow-lg flex items-center justify-center gap-3 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSSOLoading ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Redirecting to Microsoft...
                            </>
                        ) : (
                            <>
                                <MicrosoftIcon className="w-6 h-6" />
                                Sign in with Microsoft
                            </>
                        )}
                    </button>

                    {/* Info text */}
                    <p className="mt-6 text-center text-gray-300 text-xs">
                        Use your Galaxy Technology company account to sign in.
                    </p>
                </div>
            </div>
        </div>
    );
}
