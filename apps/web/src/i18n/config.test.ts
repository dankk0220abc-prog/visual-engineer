import { readFileSync, readdirSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { createTranslator } from "next-intl";
import ts from "typescript";
import { describe, expect, it } from "vitest";

import enUS from "../../messages/en-US.json";
import zhCN from "../../messages/zh-CN.json";
import {
  localizedActionKeys,
  localizedErrorKeys,
  localizedEvalKeys,
  localizedStatusKeys,
} from "../lib/localization";

import { detectLocale, resolveLocale } from "./config";

type Messages = Record<string, unknown>;
type TranslationCall = { file: string; key: string; line: number };

const webRoot = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  "../..",
);
const repositoryRoot = path.resolve(webRoot, "../..");

function messageLeaves(
  value: unknown,
  prefix = "",
): Array<[key: string, message: string]> {
  if (typeof value === "string") return [[prefix, value]];
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`Message leaf ${prefix || "<root>"} is not a string`);
  }

  return Object.entries(value).flatMap(([key, child]) =>
    messageLeaves(child, prefix ? `${prefix}.${key}` : key),
  );
}

function valueAt(messages: Messages, key: string): unknown {
  return key.split(".").reduce<unknown>((current, segment) => {
    if (typeof current !== "object" || current === null) return undefined;
    return (current as Messages)[segment];
  }, messages);
}

function interpolationVariables(message: string): string[] {
  return [...message.matchAll(/\{([A-Za-z][A-Za-z0-9_]*)\s*(?:[,}])/g)]
    .map((match) => match[1])
    .filter((value): value is string => Boolean(value))
    .filter((value, index, values) => values.indexOf(value) === index)
    .sort();
}

function compileEveryMessage(locale: "zh-CN" | "en-US", messages: Messages) {
  const translator = createTranslator({
    locale,
    messages,
    onError: (error) => {
      throw error;
    },
  });

  for (const [key, message] of messageLeaves(messages)) {
    const values = Object.fromEntries(
      interpolationVariables(message).map((name) => [name, 1]),
    );
    translator(key as never, values as never);
  }
}

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) {
      return entry.name === "test" ? [] : sourceFiles(absolute);
    }
    return /\.(?:ts|tsx)$/.test(entry.name) && !entry.name.includes(".test.")
      ? [absolute]
      : [];
  });
}

function unwrapTranslationFactory(
  expression: ts.Expression,
): ts.CallExpression | null {
  let current = expression;
  while (
    ts.isAwaitExpression(current) ||
    ts.isParenthesizedExpression(current)
  ) {
    current = current.expression;
  }
  if (!ts.isCallExpression(current)) return null;
  if (
    !ts.isIdentifier(current.expression) ||
    !["useTranslations", "getTranslations"].includes(current.expression.text)
  ) {
    return null;
  }
  return current;
}

function scanTranslationCalls(file: string, source: string) {
  const parsed = ts.createSourceFile(
    file,
    source,
    ts.ScriptTarget.Latest,
    true,
    file.endsWith("x") ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const namespaces = new Map<string, Set<string>>();

  function collectFactories(node: ts.Node) {
    if (
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      node.initializer
    ) {
      const factory = unwrapTranslationFactory(node.initializer);
      if (factory) {
        const argument = factory.arguments[0];
        const namespace =
          argument && ts.isStringLiteralLike(argument) ? argument.text : "";
        const values = namespaces.get(node.name.text) ?? new Set<string>();
        values.add(namespace);
        namespaces.set(node.name.text, values);
      }
    }
    ts.forEachChild(node, collectFactories);
  }
  collectFactories(parsed);

  const calls: TranslationCall[] = [];
  const dynamic: Array<{ file: string; line: number }> = [];
  function collectCalls(node: ts.Node) {
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      namespaces.has(node.expression.text)
    ) {
      const possibleNamespaces = namespaces.get(node.expression.text)!;
      if (possibleNamespaces.size !== 1) {
        throw new Error(
          `${file}: translator ${node.expression.text} has ambiguous namespaces`,
        );
      }
      const [namespace] = [...possibleNamespaces];
      const argument = node.arguments[0];
      const location = parsed.getLineAndCharacterOfPosition(node.getStart());
      if (argument && ts.isStringLiteralLike(argument)) {
        calls.push({
          file,
          key: namespace ? `${namespace}.${argument.text}` : argument.text,
          line: location.line + 1,
        });
      } else {
        dynamic.push({ file, line: location.line + 1 });
      }
    }
    ts.forEachChild(node, collectCalls);
  }
  collectCalls(parsed);
  return { calls, dynamic };
}

function productionTranslationCalls() {
  const results = sourceFiles(path.join(webRoot, "src")).map((file) =>
    scanTranslationCalls(file, readFileSync(file, "utf8")),
  );
  return {
    calls: results.flatMap((result) => result.calls),
    dynamic: results.flatMap((result) => result.dynamic),
  };
}

function missingTranslationCalls(
  calls: TranslationCall[],
  messages: Messages,
): TranslationCall[] {
  return calls.filter((call) => valueAt(messages, call.key) === undefined);
}

function openApiDocument(): {
  components: { schemas: Record<string, unknown> };
} {
  return JSON.parse(
    readFileSync(
      path.join(repositoryRoot, "packages/api-contract/openapi.json"),
      "utf8",
    ),
  ) as { components: { schemas: Record<string, unknown> } };
}

function enumStrings(value: unknown): string[] {
  if (Array.isArray(value)) return value.flatMap(enumStrings);
  if (typeof value !== "object" || value === null) return [];
  const object = value as Record<string, unknown>;
  const direct = Array.isArray(object.enum)
    ? object.enum.filter((item): item is string => typeof item === "string")
    : [];
  const constant = typeof object.const === "string" ? [object.const] : [];
  return [
    ...direct,
    ...constant,
    ...Object.values(object).flatMap(enumStrings),
  ];
}

describe("locale resources", () => {
  it("keeps the zh-CN and en-US semantic key sets identical", () => {
    expect(
      messageLeaves(zhCN)
        .map(([key]) => key)
        .sort(),
    ).toEqual(
      messageLeaves(enUS)
        .map(([key]) => key)
        .sort(),
    );
  });

  it("compiles every leaf message as ICU in both locales", () => {
    expect(() => compileEveryMessage("en-US", enUS)).not.toThrow();
    expect(() => compileEveryMessage("zh-CN", zhCN)).not.toThrow();
  });

  it("keeps interpolation variable sets aligned for every bilingual leaf", () => {
    for (const [key, english] of messageLeaves(enUS)) {
      const chinese = valueAt(zhCN, key);
      expect(typeof chinese, key).toBe("string");
      expect(interpolationVariables(chinese as string), key).toEqual(
        interpolationVariables(english),
      );
    }
  });

  it("rejects invalid ICU even when a message is otherwise unused", () => {
    expect(() =>
      compileEveryMessage("en-US", {
        unused: "{count, plural, one {valid} other {broken}",
      }),
    ).toThrow();
  });
});

describe("translation call contract", () => {
  it("requires every static production translation call in both locales", () => {
    const { calls, dynamic } = productionTranslationCalls();
    expect(dynamic).toEqual([]);
    expect(calls.length).toBeGreaterThan(600);
    expect(missingTranslationCalls(calls, enUS)).toEqual([]);
    expect(missingTranslationCalls(calls, zhCN)).toEqual([]);
  });

  it("fails the same-locale removal and typo cases independently of parity", () => {
    const calls = [
      { file: "fixture.tsx", line: 1, key: "navigation.tasks" },
      { file: "fixture.tsx", line: 2, key: "navigation.typo" },
    ];
    const englishWithoutTasks = { ...enUS, navigation: { ...enUS.navigation } };
    const chineseWithoutTasks = { ...zhCN, navigation: { ...zhCN.navigation } };
    delete (englishWithoutTasks.navigation as Partial<typeof enUS.navigation>)
      .tasks;
    delete (chineseWithoutTasks.navigation as Partial<typeof zhCN.navigation>)
      .tasks;
    expect(
      missingTranslationCalls(calls, englishWithoutTasks).map(({ key }) => key),
    ).toEqual(["navigation.tasks", "navigation.typo"]);
    expect(
      missingTranslationCalls(calls, chineseWithoutTasks).map(({ key }) => key),
    ).toEqual(["navigation.tasks", "navigation.typo"]);
  });
});

describe("typed dynamic translation registries", () => {
  it("covers every API status/state/verdict rendered by the Web", () => {
    const schemas = openApiDocument().components.schemas;
    const statusKeys = new Set<string>(localizedStatusKeys);
    const apiStatuses = Object.entries(schemas).flatMap(([name, schema]) =>
      /(Status|State|Verdict)(Response)?$/.test(name)
        ? enumStrings(schema)
        : [],
    );
    expect(
      [...new Set(apiStatuses)].filter((status) => !statusKeys.has(status)),
    ).toEqual([]);
    for (const status of localizedStatusKeys) {
      expect(valueAt(enUS, `common.status.${status}`)).toBeDefined();
      expect(valueAt(zhCN, `common.status.${status}`)).toBeDefined();
    }
  });

  it("covers protocol failures and current Delivery lifecycle regressions", () => {
    const failureCodes = enumStrings(
      openApiDocument().components.schemas.FailureCode,
    );
    const errorKeys = new Set<string>(localizedErrorKeys);
    expect(failureCodes.filter((code) => !errorKeys.has(code))).toEqual([]);
    expect(localizedErrorKeys).toEqual(
      expect.arrayContaining([
        "delivery_authorization_expired",
        "delivery_authorization_stale",
        "delivery_baseline_mismatch",
        "delivery_confirmation_mismatch",
        "delivery_readiness_required",
        "local_delivery_result_binding_mismatch",
        "stale_review_package",
      ]),
    );
    for (const code of localizedErrorKeys) {
      expect(valueAt(enUS, `errors.${code}`)).toBeDefined();
      expect(valueAt(zhCN, `errors.${code}`)).toBeDefined();
    }
  });

  it("covers every supported AI action kind and mandatory Eval ID", () => {
    const schemas = openApiDocument().components.schemas;
    const actionKinds = Object.entries(schemas).flatMap(([name, schema]) =>
      /^(ValidationSuite|WorkspaceText).*Operation$/.test(name)
        ? enumStrings(schema)
        : [],
    );
    expect(Object.keys(localizedActionKeys).sort()).toEqual(actionKinds.sort());

    const evaluatorSource = readFileSync(
      path.join(
        repositoryRoot,
        "apps/api/src/visual_engineer_api/ai_planning/evaluator.py",
      ),
      "utf8",
    );
    const mandatoryBlock = evaluatorSource.match(
      /MANDATORY_EVAL_IDS\s*=\s*\(([\s\S]*?)\n\)/,
    )?.[1];
    expect(mandatoryBlock).toBeDefined();
    const mandatoryEvalIds = [
      ...(mandatoryBlock ?? "").matchAll(/"([a-z0-9_]+)"/g),
    ].map((match) => match[1]);
    expect(Object.keys(localizedEvalKeys).sort()).toEqual(
      mandatoryEvalIds.sort(),
    );

    for (const key of Object.values(localizedActionKeys)) {
      expect(valueAt(enUS, `aiPlan.${key}`)).toBeDefined();
      expect(valueAt(zhCN, `aiPlan.${key}`)).toBeDefined();
    }
    for (const key of Object.values(localizedEvalKeys)) {
      expect(valueAt(enUS, `aiPlan.eval.${key}`)).toBeDefined();
      expect(valueAt(zhCN, `aiPlan.eval.${key}`)).toBeDefined();
    }
  });
});

describe("locale resolution", () => {
  it.each([
    ["zh-CN,zh;q=0.9,en;q=0.8", "zh-CN"],
    ["zh-TW;q=0.8,en-US;q=0.7", "zh-CN"],
    ["fr-FR,en;q=0.8", "en-US"],
    ["en-US,zh;q=0.1", "en-US"],
    [null, "en-US"],
  ])("detects %s as %s", (header, expected) => {
    expect(detectLocale(header)).toBe(expected);
  });

  it("uses a supported Cookie before browser negotiation", () => {
    expect(resolveLocale("zh-CN", "en-US")).toBe("zh-CN");
    expect(resolveLocale("en-US", "zh-CN")).toBe("en-US");
  });

  it("ignores an invalid Cookie and safely negotiates the header", () => {
    expect(resolveLocale("de-DE", "zh-HK, en;q=0.5")).toBe("zh-CN");
  });
});
