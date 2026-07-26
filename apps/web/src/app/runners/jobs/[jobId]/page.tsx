import { RunnerJobConsole } from "@/components/runner-job-console";

export default async function RunnerJobPage({
  params,
}: {
  params: Promise<{ jobId: string }>;
}) {
  const { jobId } = await params;
  return <RunnerJobConsole jobId={jobId} />;
}
