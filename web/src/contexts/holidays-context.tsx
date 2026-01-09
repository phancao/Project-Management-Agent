'use client';

import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { DateRange } from 'react-day-picker';

// Types
export interface Holiday {
    date: Date;
    name: string;
}

export interface MemberVacation {
    memberId: string;
    vacations: DateRange[];
}

interface HolidaysContextType {
    // Global holidays
    holidays: Holiday[];
    addHoliday: (holiday: Holiday) => void;
    removeHoliday: (index: number) => void;

    // Per-member vacations
    getMemberVacations: (memberId: string) => DateRange[];
    addMemberVacation: (memberId: string, vacation: DateRange) => void;
    removeMemberVacation: (memberId: string, vacationIndex: number) => void;

    // Loading state
    isLoading: boolean;
}

const HolidaysContext = createContext<HolidaysContextType | null>(null);

// localStorage keys
const HOLIDAYS_KEY = 'ee-holidays-global';
const VACATIONS_PREFIX = 'ee-vacations-member-';

export function HolidaysProvider({ children }: { children: ReactNode }) {
    const [holidays, setHolidays] = useState<Holiday[]>([]);
    const [vacationsMap, setVacationsMap] = useState<Record<string, DateRange[]>>({});
    const [isLoading, setIsLoading] = useState(true);

    // Load holidays from localStorage on mount
    useEffect(() => {
        try {
            const saved = localStorage.getItem(HOLIDAYS_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                setHolidays(parsed.map((h: any) => ({
                    ...h,
                    date: new Date(h.date)
                })));
            }
        } catch (e) {
            console.error("Failed to load holidays", e);
        }
        setIsLoading(false);
    }, []);

    // Save holidays to localStorage
    const saveHolidays = (newHolidays: Holiday[]) => {
        setHolidays(newHolidays);
        localStorage.setItem(HOLIDAYS_KEY, JSON.stringify(newHolidays));
    };

    const addHoliday = (holiday: Holiday) => {
        saveHolidays([...holidays, holiday]);
    };

    const removeHoliday = (index: number) => {
        saveHolidays(holidays.filter((_, i) => i !== index));
    };

    // Load vacations for a member (lazy loading)
    const loadMemberVacations = (memberId: string): DateRange[] => {
        if (vacationsMap[memberId]) {
            return vacationsMap[memberId];
        }

        try {
            const saved = localStorage.getItem(`${VACATIONS_PREFIX}${memberId}`);
            if (saved) {
                const parsed = JSON.parse(saved);
                const hydrated = parsed.map((v: any) => ({
                    from: v.from ? new Date(v.from) : undefined,
                    to: v.to ? new Date(v.to) : undefined
                }));
                setVacationsMap(prev => ({ ...prev, [memberId]: hydrated }));
                return hydrated;
            }
        } catch (e) {
            console.error(`Failed to load vacations for ${memberId}`, e);
        }
        return [];
    };

    const getMemberVacations = (memberId: string): DateRange[] => {
        return vacationsMap[memberId] || loadMemberVacations(memberId);
    };

    const saveMemberVacations = (memberId: string, vacations: DateRange[]) => {
        setVacationsMap(prev => ({ ...prev, [memberId]: vacations }));
        localStorage.setItem(`${VACATIONS_PREFIX}${memberId}`, JSON.stringify(vacations));
    };

    const addMemberVacation = (memberId: string, vacation: DateRange) => {
        const current = getMemberVacations(memberId);
        saveMemberVacations(memberId, [...current, vacation]);
    };

    const removeMemberVacation = (memberId: string, vacationIndex: number) => {
        const current = getMemberVacations(memberId);
        saveMemberVacations(memberId, current.filter((_, i) => i !== vacationIndex));
    };

    return (
        <HolidaysContext.Provider value={{
            holidays,
            addHoliday,
            removeHoliday,
            getMemberVacations,
            addMemberVacation,
            removeMemberVacation,
            isLoading
        }}>
            {children}
        </HolidaysContext.Provider>
    );
}

export function useHolidays() {
    const context = useContext(HolidaysContext);
    if (!context) {
        throw new Error('useHolidays must be used within a HolidaysProvider');
    }
    return context;
}

// Helper: Check if a specific date is a holiday
export function isHoliday(date: Date, holidays: Holiday[]): boolean {
    return holidays.some(h =>
        h.date.getFullYear() === date.getFullYear() &&
        h.date.getMonth() === date.getMonth() &&
        h.date.getDate() === date.getDate()
    );
}

// Helper: Check if a specific date is a vacation for a member
export function isVacation(date: Date, vacations: DateRange[]): boolean {
    for (const vacation of vacations) {
        if (vacation.from) {
            const start = new Date(vacation.from);
            start.setHours(0, 0, 0, 0);
            const end = vacation.to ? new Date(vacation.to) : new Date(vacation.from);
            end.setHours(23, 59, 59, 999);

            const checkDate = new Date(date);
            checkDate.setHours(12, 0, 0, 0);

            if (checkDate >= start && checkDate <= end) {
                return true;
            }
        }
    }
    return false;
}
