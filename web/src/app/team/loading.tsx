import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import { Users } from "lucide-react";

export default function Loading() {
    return (
        <div className="flex h-screen w-screen items-center justify-center bg-background">
            <WorkspaceLoading
                title="Loading Team Management"
                subtitle="Preparing team data..."
                items={[
                    { label: "Loading page", isLoading: true },
                ]}
                icon={<Users className="w-6 h-6 text-white" />}
            />
        </div>
    );
}
