# Web Console Localization Glossary

| English term           | zh-CN        | Usage boundary                                                     |
| ---------------------- | ------------ | ------------------------------------------------------------------ |
| Workspace              | 工作区       | Runner-owned detached worktree; never a source repository path     |
| Checkpoint             | 检查点       | Immutable Workspace tree/diff state                                |
| Validation             | 验证         | Governed validation execution and Evidence aggregation             |
| Review                 | 审查         | Human Review Decision over an immutable Review Package             |
| Release Readiness      | 发布就绪度   | System-derived readiness verdict; not production approval          |
| Plan Approval          | 计划批准     | Human decision over one exact Plan version; no execution authority |
| Execution Grant        | 执行授权     | Separate immutable authority for fixed Workspace operations        |
| Review Approval        | 审查批准     | Review Decision only; no delivery authority                        |
| Delivery Authorization | 交付授权     | Separate local-delivery authority over one exact fresh baseline    |
| Side-effect Permit     | 副作用许可   | Short-lived, attempt/lease/digest-bound filesystem authority       |
| AI Plan                | AI 计划      | Strict Provider-produced plan contract                             |
| Prompt                 | 提示词       | Versioned system-owned Provider instruction and binding            |
| Trace                  | 追踪         | Provider attempt/lifecycle evidence; raw payload remains unchanged |
| Eval                   | 评估         | System-owned deterministic policy evaluation                       |
| Evidence               | 证据         | Immutable raw evidence; labels may be localized, content is not    |
| stale                  | 已失效       | No longer fresh against the bound revision or lineage              |
| replay                 | 重放         | Exact deterministic or idempotent repetition                       |
| fixture                | 固定测试夹具 | Synthetic, bounded test input; never production/customer evidence  |

The UI may retain an established English technical term beside the Chinese
translation where that prevents ambiguity. Distinct authorities must never be
collapsed into the generic translation “批准”.
