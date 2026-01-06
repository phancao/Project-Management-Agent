import { useQuery } from "@tanstack/react-query";
import { listUsers, type PMUser } from "../api/pm/users";

/**
 * Prefetch users at page load.
 * This hook should be called at the page level (e.g., TeamPage)
 * to ensure users are cached before user interacts with search.
 */
export function usePrefetchUsers() {
    return useQuery({
        queryKey: ['pm', 'users'],
        queryFn: () => listUsers(),
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 10 * 60 * 1000,   // 10 minutes
    });
}
