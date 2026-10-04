# 外部模型开发性核查

2026-10-05。测试边界沿用已批准计划的公开Model密度/梯度/约束接口，以及完整采样与R整批接口；不测试内部协作对象。当前三个手算单元检查先失败后通过，覆盖平坦先验/距离单位、torch梯度/HVP和可积性证书。红灯分别为缺少模型文件、尚未实现torch提供方式、尚未实现证书；不表示原有采样器回归。日志保留。

新Mac环境`.venv-completion`使用torch 2.13.0、NumPy 2.2.6、SciPy 1.15.3；pip check通过。旧`.venv`和Windows冻结环境未修改。依赖锁见environment/locks/mac-completion-torch-pip.txt。torch自身JIT弃用警告保留，不改用未经核验的compile路线。

本提交准备了真实目标的Stan/NumPy/torch与R核验入口；当前尚未运行真实目标采样。下一步从干净源码提交冻结external-wells-validation-v1，保存同一实际数组并执行有限核验。它不是正式推断或性能协议。
