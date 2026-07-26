import { RunConsole } from "@/components/run-console";

export default async function RunPage({
  params,
}: {
  params: Promise<{ runId: string }>;
}) {
  const { runId } = await params;
  return <RunConsole runId={runId} />;
}
