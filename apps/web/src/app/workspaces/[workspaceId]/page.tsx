import { WorkspaceDetailConsole } from "@/components/workspace-detail-console";

export default async function WorkspaceDetailPage({
  params,
}: {
  params: Promise<{ workspaceId: string }>;
}) {
  const { workspaceId } = await params;
  return <WorkspaceDetailConsole workspaceId={workspaceId} />;
}
