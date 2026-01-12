
import { startOfDay, endOfDay, eachDayOfInterval, isWeekend, isWithinInterval, parseISO } from 'date-fns';

// Mock Interfaces
interface MemberPeriod {
    range: { from: Date; to?: Date };
    allocation: number;
    vacations?: { from: Date; to?: Date }[];
}

interface PMTimeEntry {
    user_id: string;
    date: string;
    hours: number;
}

// Logic extracted from EfficiencyDashboard (Post-Fix)
function calculateEfficiency(
    dateRange: { from: Date; to: Date },
    activePeriods: Record<string, MemberPeriod[]> = {},
    timeEntries: PMTimeEntry[] = [],
    memberIds: string[]
) {
    const startDate = startOfDay(dateRange.from);
    const endDate = endOfDay(dateRange.to);

    // Helper: Check if a day counts as "Active Capacity" for a member
    const isMemberActiveOnDay = (memberId: string, day: Date, periods: MemberPeriod[]) => {
        // 1. Weekend Check
        if (isWeekend(day)) return false;

        // 2. Default Mode (No periods defined) -> Active
        if (!periods || periods.length === 0) return true;

        // 3. Check if ONLY vacation periods exist (Heuristic)
        const hasOnlyVacations = periods.every(p => p.allocation === 0);

        // 4. Check specific active periods
        let isActive = false;
        periods.forEach(period => {
            if (period.range.from && isWithinInterval(day, {
                start: startOfDay(period.range.from),
                end: endOfDay(period.range.to || period.range.from)
            })) {
                if (period.allocation > 0) isActive = true;
            }
        });

        if (isActive) return true;
        if (hasOnlyVacations) return true;

        return false;
    };

    const getMemberCapacityHours = (memberId: string) => {
        const periods = activePeriods[memberId];
        const days = eachDayOfInterval({ start: startDate, end: endDate });
        let memberTotalCapacity = 0;

        days.forEach(day => {
            if (!isMemberActiveOnDay(memberId, day, periods || [])) return;

            let allocationPercent = 100;
            if (periods && periods.length > 0) {
                const activePeriod = periods.find(p => p.range.from && isWithinInterval(day, {
                    start: startOfDay(p.range.from),
                    end: endOfDay(p.range.to || p.range.from)
                }));
                if (activePeriod) {
                    allocationPercent = activePeriod.allocation;
                }
            }
            memberTotalCapacity += 8 * (allocationPercent / 100);
        });

        return memberTotalCapacity;
    };

    // Calculate Total Capacity
    let totalCapacityHours = 0;
    memberIds.forEach(id => {
        totalCapacityHours += getMemberCapacityHours(id);
    });

    // Calculate Actual Hours (Filtered)
    let totalAllocatedHours = 0;
    timeEntries.forEach(entry => {
        const entryDate = parseISO(entry.date);
        if (entryDate < startDate || entryDate > endDate) return;

        const periods = activePeriods[entry.user_id];
        // Only count if member is active
        if (isMemberActiveOnDay(entry.user_id, entryDate, periods || [])) {
            totalAllocatedHours += entry.hours;
        }
    });

    const eePercent = totalCapacityHours > 0 ? (totalAllocatedHours / totalCapacityHours) * 100 : 0;

    return {
        totalCapacityHours,
        totalAllocatedHours,
        eePercent
    };
}

// Verification Case: "Chen" Scenario (Phase 2 - 82% Investigation)
// Date Range: Sep 1 - Sep 30
// Active: Sep 5 - Sep 30 (Joined mid-month)
// Capacity: 
//   Sep 5 (Fri) = 8h
//   Sep 8-12 (5 days) = 40h
//   Sep 15-19 (5 days) = 40h
//   Sep 22-26 (5 days) = 40h
//   Sep 29-30 (2 days) = 16h
//   Total Capacity = 144 hours.

// Scenario: User logged time for most days, but missed a few.
// Target Efficiency: ~82%
// Target Allocated: 144 * 0.82 = ~118 hours.
// Missing Hours: 144 - 118 = 26 hours (approx 3 days missed).

const memberId = "Chen";
const dateRange = { from: new Date('2025-09-01'), to: new Date('2025-09-30') };

const activePeriods = {
    [memberId]: [
        {
            range: { from: new Date('2025-09-05'), to: new Date('2025-12-30') },
            allocation: 100
        }
    ]
};

// Generate Time Entries (Simulate logging 8h/day but missing 3 days)
const timeEntries: PMTimeEntry[] = [];
const days = eachDayOfInterval({ start: new Date('2025-09-05'), end: new Date('2025-09-30') });
let daysLogged = 0;

days.forEach((day, index) => {
    if (isWeekend(day)) return;

    // Simulate missing 3 days (e.g. Sep 15, 16, 17)
    // 15th, 16th, 17th of the month
    if (day.getDate() >= 15 && day.getDate() <= 17) {
        console.log(`Simulating MISSED LOG on ${day.toISOString()}`);
        return;
    }

    timeEntries.push({
        user_id: memberId,
        date: day.toISOString(),
        hours: 8
    });
    daysLogged++;
});

const result = calculateEfficiency(dateRange, activePeriods, timeEntries, [memberId]);

console.log("\nVerification Results (Phase 2):");
console.log(`Active Period: Sep 5 - Sep 30`);
console.log(`Total Capacity: ${result.totalCapacityHours}h`);
console.log(`Total Allocated: ${result.totalAllocatedHours}h (${daysLogged} days logged)`);
console.log(`Efficiency: ${result.eePercent.toFixed(1)}%`);

if (result.eePercent > 80 && result.eePercent < 85) {
    console.log("SUCCESS: Simulated ~82% efficiency by missing 3 days of logs.");
} else {
    console.log("FAILURE: Did not reproduce target efficiency.");
}
