import { WorkspaceLoading } from "~/components/ui/workspace-loading";
import { FolderKanban } from "lucide-react";

export default function Loading() {
    return (
        <div className="flex h-screen w-screen items-center justify-center bg-background">
            <WorkspaceLoading
                title="Loading Project Management"
                subtitle="Preparing workspace..."
                items={[
                    { label: "Loading page", isLoading: true },
                ]}
                icon={<FolderKanban className="w-6 h-6 text-white" />}
            />
        </div>
    );
}
