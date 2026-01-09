'use client';

import { createContext, useContext } from 'react';

// Context for member profile dialog
interface MemberProfileContextType {
    openMemberProfile: (memberId: string) => void;
}

export const MemberProfileContext = createContext<MemberProfileContextType | null>(null);

export function useMemberProfile() {
    const context = useContext(MemberProfileContext);
    if (!context) {
        throw new Error('useMemberProfile must be used within MemberProfileProvider');
    }
    return context;
}
