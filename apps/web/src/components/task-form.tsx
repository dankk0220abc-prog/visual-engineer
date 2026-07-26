"use client";

import { useState } from "react";

import type { CreateTaskInput, RepositoryKind } from "@/lib/api";

type FieldName =
  | "title"
  | "objective"
  | "repository_kind"
  | "repository_display_name"
  | "repository_locator";

type FieldErrors = Partial<Record<FieldName, string>>;

const inputClasses =
  "mt-2 w-full rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-950 outline-none placeholder:text-slate-400 hover:border-slate-400 focus:border-blue-600 focus:ring-2 focus:ring-blue-600/20";

function ErrorMessage({
  field,
  error,
}: {
  field: FieldName;
  error: string | undefined;
}) {
  return error ? (
    <p id={`${field}-error`} className="mt-1.5 text-sm text-red-700">
      {error}
    </p>
  ) : null;
}

function value(formData: FormData, name: FieldName): string {
  return String(formData.get(name) ?? "").trim();
}

function validate(formData: FormData): {
  errors: FieldErrors;
  input?: CreateTaskInput;
} {
  const title = value(formData, "title");
  const objective = value(formData, "objective");
  const repositoryKind = value(formData, "repository_kind");
  const repositoryDisplayName = value(formData, "repository_display_name");
  const repositoryLocator = value(formData, "repository_locator");
  const errors: FieldErrors = {};

  if (!title) errors.title = "请输入任务标题。";
  else if (title.length > 120) errors.title = "标题不能超过 120 个字符。";

  if (!objective) errors.objective = "请输入任务目标。";
  else if (objective.length > 4000)
    errors.objective = "任务目标不能超过 4000 个字符。";

  if (!["local_path", "github"].includes(repositoryKind)) {
    errors.repository_kind = "请选择支持的仓库类型。";
  }

  if (!repositoryDisplayName)
    errors.repository_display_name = "请输入仓库显示名称。";
  else if (repositoryDisplayName.length > 120)
    errors.repository_display_name = "仓库显示名称不能超过 120 个字符。";

  if (!repositoryLocator) errors.repository_locator = "请输入仓库位置。";
  else if (repositoryLocator.length > 1024)
    errors.repository_locator = "仓库位置不能超过 1024 个字符。";

  for (const [name, fieldValue] of Object.entries({
    title,
    objective,
    repository_display_name: repositoryDisplayName,
    repository_locator: repositoryLocator,
  })) {
    if (fieldValue.includes("\0")) {
      errors[name as FieldName] = "字段不能包含 NUL 字符。";
    }
  }

  if (Object.keys(errors).length > 0) return { errors };

  return {
    errors,
    input: {
      title,
      objective,
      repository_kind: repositoryKind as RepositoryKind,
      repository_display_name: repositoryDisplayName,
      repository_locator: repositoryLocator,
    } as CreateTaskInput,
  };
}

export function TaskForm({
  isSubmitting,
  onSubmit,
}: {
  isSubmitting: boolean;
  onSubmit: (input: CreateTaskInput) => Promise<boolean>;
}) {
  const [errors, setErrors] = useState<FieldErrors>({});

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const result = validate(new FormData(form));
    setErrors(result.errors);

    if (!result.input) return;

    const created = await onSubmit(result.input);
    if (created) form.reset();
  }

  function errorProps(field: FieldName) {
    const error = errors[field];
    return {
      "aria-invalid": Boolean(error),
      "aria-describedby": error ? `${field}-error` : undefined,
    };
  }

  return (
    <form className="mt-6 space-y-5" noValidate onSubmit={handleSubmit}>
      <div>
        <label className="text-sm font-semibold text-slate-800" htmlFor="title">
          任务标题
        </label>
        <input
          className={inputClasses}
          id="title"
          name="title"
          maxLength={120}
          placeholder="例如：重构项目导航"
          {...errorProps("title")}
        />
        <ErrorMessage error={errors.title} field="title" />
      </div>

      <div>
        <label
          className="text-sm font-semibold text-slate-800"
          htmlFor="objective"
        >
          任务目标
        </label>
        <textarea
          className={`${inputClasses} min-h-28 resize-y`}
          id="objective"
          name="objective"
          maxLength={4000}
          placeholder="说明期望结果和验证标准。Foundation 阶段只保存元数据，不会访问仓库。"
          {...errorProps("objective")}
        />
        <ErrorMessage error={errors.objective} field="objective" />
      </div>

      <fieldset>
        <legend className="text-sm font-semibold text-slate-800">
          仓库信息
        </legend>
        <div className="mt-2 grid gap-4 sm:grid-cols-2">
          <div>
            <label className="text-sm text-slate-700" htmlFor="repository_kind">
              仓库类型
            </label>
            <select
              className={inputClasses}
              defaultValue="local_path"
              id="repository_kind"
              name="repository_kind"
              {...errorProps("repository_kind")}
            >
              <option value="local_path">本地路径</option>
              <option value="github">GitHub</option>
            </select>
            <ErrorMessage
              error={errors.repository_kind}
              field="repository_kind"
            />
          </div>
          <div>
            <label
              className="text-sm text-slate-700"
              htmlFor="repository_display_name"
            >
              显示名称
            </label>
            <input
              className={inputClasses}
              id="repository_display_name"
              name="repository_display_name"
              maxLength={120}
              placeholder="design-system"
              {...errorProps("repository_display_name")}
            />
            <ErrorMessage
              error={errors.repository_display_name}
              field="repository_display_name"
            />
          </div>
        </div>
        <div className="mt-4">
          <label
            className="text-sm text-slate-700"
            htmlFor="repository_locator"
          >
            仓库位置
          </label>
          <input
            className={inputClasses}
            id="repository_locator"
            name="repository_locator"
            maxLength={1024}
            placeholder="/workspace/design-system 或 owner/repository"
            {...errorProps("repository_locator")}
          />
          <p className="mt-1.5 text-xs leading-5 text-slate-500">
            仅作为任务元数据保存；当前系统不会读取此位置。
          </p>
          <ErrorMessage
            error={errors.repository_locator}
            field="repository_locator"
          />
        </div>
      </fieldset>

      <button
        type="submit"
        disabled={isSubmitting}
        className="inline-flex min-h-11 w-full items-center justify-center rounded-xl bg-slate-950 px-4 py-2.5 text-sm font-semibold text-white outline-none hover:bg-slate-800 focus-visible:ring-2 focus-visible:ring-blue-600 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60"
      >
        {isSubmitting ? "正在创建…" : "创建任务"}
      </button>
    </form>
  );
}
