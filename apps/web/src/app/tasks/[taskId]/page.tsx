import { TaskDetails } from "@/components/task-details";

export default async function TaskPage({
  params,
}: {
  params: Promise<{ taskId: string }>;
}) {
  const { taskId } = await params;
  return <TaskDetails taskId={taskId} />;
}
