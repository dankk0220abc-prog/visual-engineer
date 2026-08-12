# VisualEngineer

[English README](README.md) · [架构说明](docs/architecture/overview.md) · [公开 Evidence 资产](docs/portfolio/evidence-assets.md) · [安全策略](SECURITY.md)

VisualEngineer 是一个本地、单用户的受治理 AI 设计工程与交付系统：AI 可以生成类型化计划，但计划、批准、Execution Grant、Runner 执行、审查、交付和 Evidence 始终是彼此独立的事实与权限。

## 核心定位

它解决的不是“让模型直接调用工具”，而是如何将 AI 辅助交付变成可复核的流程：

- Provider 输出只是类型化 Plan，不能直接获得 Runner 或 Workspace 权限。
- Plan Approval 不等于 Execution Grant；每个风险更高的阶段都需要单独授权。
- Provider 调用具有 `prepared → dispatching → terminal` 的持久生命周期；post-dispatch 不确定性保留为 `outcome_unknown`，不自动重试。
- Fixture 是默认的确定性、无网络、无凭据演示路径；BYOK 只在当前浏览器会话的易失性服务端内存中保存，且不会回退使用维护者额度。
- Evidence 是安全投影，不公开 Key、原始 Provider 流量、完整 upstream request ID 或私有财务资料。

## 已封存的 live Evidence

最终 main 基线为 `9615bde962c7dfeb73f9644573066d74d2d837ec`（tree `8f4b95fd1257a830e0aec3792063110d2690e730`，Alembic `20260810_0017`）。

唯一完成的真实 Provider 验证是 Zhipu / GLM-5.2：correlation `3a9c354f7a58`，状态 `succeeded`，1,362 input + 654 output = 2,016 tokens，Provider latency 11,543 ms，client total 11,553 ms，billing 为 `live_billing_unknown`。此前 3 次真实尝试保留为 `outcome_unknown`，没有被改写为成功或失败。

该成功调用生成了 Plan 与 8 条通过的策略评估，但没有创建 Approval、Execution Grant、Runner authority、Review 或 Delivery。

最终 CI：Fast `31581978015` 与 Heavy `31581978289` 都在 attempt 1 成功。

## Demo 与限制

默认演示使用 Fixture。按仓库的真实命令运行：

```sh
make bootstrap
make platform-up
```

这会创建本地合成夹具并启动本地服务，不是只读操作。不要在普通演示中输入真实 Provider Key 或运行 `make zhipu-live-canary-run`。

当前范围是本地、单用户、fixture-first 的开发系统，而不是生产部署。未声称真实客户、用户量、QPS、收入、性能提升或多 Provider live validation；BYOK 不是商业多租户密钥库；远程 Git、PR、merge、release、部署、认证、多租户与生产 SRE 控制均不在当前范围内。

完整英文项目主页、架构、截图与可验证边界见 [README](README.md)。
