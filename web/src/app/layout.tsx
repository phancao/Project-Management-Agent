// Copyright (c) 2025 Bytedance Ltd. and/or its affiliates
// SPDX-License-Identifier: MIT

import "~/styles/globals.css";

import { type Metadata } from "next";
import { Geist } from "next/font/google";
import Script from "next/script";
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages } from 'next-intl/server';

import { PMMCPAutoConfig } from "~/components/deer-flow/pm-mcp-auto-config";
import { ThemeProviderWrapper } from "~/components/deer-flow/theme-provider-wrapper";
import { env } from "~/env";

import { Toaster } from "../components/deer-flow/toaster";
import { LoadingProvider } from "~/core/contexts/loading-context";
import { LoadingScreen } from "~/components/ui/loading-screen";
import { AuthProvider } from "~/core/contexts/auth-context";
import { HolidaysProvider } from "~/contexts/holidays-context";
import { BugBaseProvider } from "~/components/bugbase";

export const metadata: Metadata = {
  title: "🌌 Galaxy AI Project Manager",
  description:
    "An AI-powered project management assistant that helps you manage sprints, tasks, and team collaboration.",
  icons: [{ rel: "icon", url: "/favicon.ico" }],
};

const geist = Geist({
  subsets: ["latin"],
  variable: "--font-geist-sans",
});

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <html lang={locale} className={`${geist.variable}`} suppressHydrationWarning>
      <head>
        {/* Define isSpace function globally to fix markdown-it issues with Next.js + Turbopack
          https://github.com/markdown-it/markdown-it/issues/1082#issuecomment-2749656365 */}
        <Script id="markdown-it-fix" strategy="beforeInteractive">
          {`
            if (typeof window !== 'undefined' && typeof window.isSpace === 'undefined') {
              window.isSpace = function(code) {
                return code === 0x20 || code === 0x09 || code === 0x0A || code === 0x0B || code === 0x0C || code === 0x0D;
              };
            }
          `}
        </Script>
      </head>
      <body className="bg-app" suppressHydrationWarning>
        <NextIntlClientProvider messages={messages}>
          <PMMCPAutoConfig />
          <LoadingProvider>
            <LoadingScreen />
            <ThemeProviderWrapper>
              <HolidaysProvider>
                <AuthProvider>
                  <BugBaseProvider>{children}</BugBaseProvider>
                </AuthProvider>
              </HolidaysProvider>
            </ThemeProviderWrapper>
          </LoadingProvider>
          <Toaster />
        </NextIntlClientProvider>
        {
          // NO USER BEHAVIOR TRACKING OR PRIVATE DATA COLLECTION BY DEFAULT
          //
          // When `NEXT_PUBLIC_STATIC_WEBSITE_ONLY` is `true`, the script will be injected
          // into the page only when `AMPLITUDE_API_KEY` is provided in `.env`
        }
        {env.NEXT_PUBLIC_STATIC_WEBSITE_ONLY && env.AMPLITUDE_API_KEY && (
          <>
            <Script src="https://cdn.amplitude.com/script/d2197dd1df3f2959f26295bb0e7e849f.js"></Script>
            <Script id="amplitude-init" strategy="lazyOnload">
              {`window.amplitude.init('${env.AMPLITUDE_API_KEY}', {"fetchRemoteConfig":true,"autocapture":true});`}
            </Script>
          </>
        )}
      </body>
    </html>
  );
}
