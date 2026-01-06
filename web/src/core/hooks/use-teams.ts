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

    // Load from LocalStorage on mount
    useEffect(() => {
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
        setIsLoading(false);
    }, []);

    // Save to LocalStorage whenever teams change
    const saveTeams = (newTeams: Team[]) => {
        setTeams(newTeams);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newTeams));
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
