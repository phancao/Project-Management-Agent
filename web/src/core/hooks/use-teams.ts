"use client"

import { useState, useEffect } from "react"

export interface Team {
    id: string;
    name: string;
    description: string;
    memberIds: string[]; // List of User IDs
}

const STORAGE_KEY = "gravity_teams_v1";

const DEFAULT_TEAMS: Team[] = [
    { id: '1', name: 'Engineering', description: 'Core development team', memberIds: [] },
    { id: '2', name: 'Design', description: 'Product design and UX', memberIds: [] },
    { id: '3', name: 'Marketing', description: 'Growth and campaigns', memberIds: [] },
];

export function useTeams() {
    const [teams, setTeams] = useState<Team[]>([]);
    const [isLoading, setIsLoading] = useState(true);

    // Load from LocalStorage
    const loadTeams = () => {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored) {
            try {
                setTeams(JSON.parse(stored));
            } catch (e) {
                console.error("Failed to parse teams from local storage", e);
                setTeams(DEFAULT_TEAMS);
            }
        } else {
            setTeams(DEFAULT_TEAMS);
        }
    };

    // Load on mount
    useEffect(() => {
        loadTeams();
        setIsLoading(false);
    }, []);

    // Listen for storage changes from OTHER tabs (browser tabs)
    useEffect(() => {
        const handleStorageChange = (e: StorageEvent) => {
            if (e.key === STORAGE_KEY) {
                loadTeams();
            }
        };
        window.addEventListener('storage', handleStorageChange);
        return () => window.removeEventListener('storage', handleStorageChange);
    }, []);

    // Listen for custom event from SAME tab (for component sync)
    useEffect(() => {
        const handleTeamsUpdate = () => {
            loadTeams();
        };
        window.addEventListener('teams-updated', handleTeamsUpdate);
        return () => window.removeEventListener('teams-updated', handleTeamsUpdate);
    }, []);

    // Save to LocalStorage and dispatch sync event
    const saveTeams = (newTeams: Team[]) => {
        setTeams(newTeams);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newTeams));
        // Dispatch custom event to sync other components in same tab
        window.dispatchEvent(new CustomEvent('teams-updated'));
    };

    const addTeam = (name: string, description: string = "") => {
        const newTeam: Team = {
            id: crypto.randomUUID(),
            name,
            description,
            memberIds: []
        };
        saveTeams([...teams, newTeam]);
        return newTeam;
    };

    const updateTeam = (id: string, updates: Partial<Team>) => {
        saveTeams(teams.map(t => t.id === id ? { ...t, ...updates } : t));
    };

    const deleteTeam = (id: string) => {
        saveTeams(teams.filter(t => t.id !== id));
    };

    const addMemberToTeam = (teamId: string, userId: string) => {
        console.log(`[useTeams] Added member ${userId} to team ${teamId}`);
        const team = teams.find(t => t.id === teamId);
        if (team) {
            if (!team.memberIds.includes(userId)) {
                updateTeam(teamId, { memberIds: [...team.memberIds, userId] });
            } else {
                console.log(`[useTeams] Member ${userId} already in team`);
            }
        } else {
            console.error(`[useTeams] Team ${teamId} not found`);
        }
    };

    const removeMemberFromTeam = (teamId: string, userId: string) => {
        const team = teams.find(t => t.id === teamId);
        if (team) {
            updateTeam(teamId, { memberIds: team.memberIds.filter(id => id !== userId) });
        }
    };

    return {
        teams,
        isLoading,
        addTeam,
        updateTeam,
        deleteTeam,
        addMemberToTeam,
        removeMemberFromTeam
    };
}
