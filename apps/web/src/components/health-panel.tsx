import { StatusPill } from "./status-pill";

export type HealthState = "checking" | "healthy" | "unavailable";

function HealthRow({
  label,
  description,
  state,
}: {
  label: string;
  description: string;
  state: HealthState;
}) {
  const display = {
    checking: { label: "检查中", tone: "pending" as const },
    healthy: { label: "正常", tone: "positive" as const },
    unavailable: { label: "不可用", tone: "negative" as const },
  }[state];

  return (
    <li className="flex items-center justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <div>
        <p className="text-sm font-semibold text-slate-900">{label}</p>
        <p className="mt-0.5 text-xs text-slate-500">{description}</p>
      </div>
      <StatusPill tone={display.tone}>{display.label}</StatusPill>
    </li>
  );
}

export function HealthPanel({
  live,
  ready,
  onRetry,
}: {
  live: HealthState;
  ready: HealthState;
  onRetry: () => void;
}) {
  const hasFailure = live === "unavailable" || ready === "unavailable";

  return (
    <section
      className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"
      aria-labelledby="health-heading"
    >
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs font-semibold tracking-widest text-slate-500 uppercase">
            Runtime
          </p>
          <h2
            id="health-heading"
            className="mt-1 text-lg font-semibold text-slate-950"
          >
            服务健康
          </h2>
        </div>
        {hasFailure ? (
          <button
            type="button"
            className="rounded-lg px-3 py-2 text-sm font-semibold text-blue-700 outline-none hover:bg-blue-50 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2"
            onClick={onRetry}
          >
            重新检查
          </button>
        ) : null}
      </div>
      <ul className="mt-5 divide-y divide-slate-100">
        <HealthRow
          label="Liveness"
          description="API 进程能够响应"
          state={live}
        />
        <HealthRow
          label="Readiness"
          description="API 已连接数据库"
          state={ready}
        />
      </ul>
    </section>
  );
}
