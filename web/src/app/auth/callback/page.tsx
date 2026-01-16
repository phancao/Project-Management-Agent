'use client';

// OAuth Callback Page
// Handles Azure AD OAuth callback and exchanges code for tokens via backend

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2 } from 'lucide-react';

export default function AuthCallbackPage() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const [error, setError] = useState<string | null>(null);
    const [status, setStatus] = useState('Processing authentication...');

    useEffect(() => {
        const handleCallback = async () => {
            // Check for errors from Azure AD
            const errorParam = searchParams.get('error');
            const errorDescription = searchParams.get('error_description');

            if (errorParam) {
                setError(errorDescription || errorParam);
                return;
            }

            // Get auth code and state from URL
            const code = searchParams.get('code');
            const state = searchParams.get('state');

            if (!code || !state) {
                setError('Missing authorization code or state');
                return;
            }

            setStatus('Completing sign-in...');

            // Forward to backend to complete the OAuth flow
            // The backend will exchange the code for tokens and redirect back with JWT
            const backendCallbackUrl = `/api/auth/azure/callback?code=${encodeURIComponent(code)}&state=${encodeURIComponent(state)}`;

            try {
                // Redirect to backend callback endpoint
                window.location.href = backendCallbackUrl;
            } catch (err) {
                setError('Failed to complete authentication');
                console.error('Auth callback error:', err);
            }
        };

        handleCallback();
    }, [searchParams, router]);

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1E398D] via-[#14B795] to-[#1C9AD6]">
                <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-8 max-w-md text-center">
                    <h1 className="text-2xl font-bold text-white mb-4">Authentication Failed</h1>
                    <p className="text-red-300 mb-6">{error}</p>
                    <a
                        href="/login"
                        className="inline-block px-6 py-3 bg-gradient-to-r from-[#1E398D] to-[#14B795] text-white rounded-xl font-medium hover:opacity-90 transition"
                    >
                        Back to Login
                    </a>
                </div>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-[#1E398D] via-[#14B795] to-[#1C9AD6]">
            <div className="bg-white/10 backdrop-blur-xl border border-white/20 rounded-2xl p-8 max-w-md text-center">
                <Loader2 className="w-12 h-12 text-white animate-spin mx-auto mb-4" />
                <h1 className="text-xl font-semibold text-white mb-2">Signing you in...</h1>
                <p className="text-gray-300">{status}</p>
            </div>
        </div>
    );
}
