# Windows交接材料本机验收（2026-10-04）

本轮只准备原生Windows交接、技能迁移和公开研究仓库，不在Mac模拟GPU成功。

- `tests/handoff`：18通过，见`tests.log`和`tests.xml`。覆盖归档拼接与损坏拒绝、禁止Windows探针在Mac通过、技能校验/安全路径/冲突不覆盖/幂等安装。测试不证明PowerShell、Windows插件或CUDA在目标机兼容。
- 真实30技能ZIP在临时目录安装：30成功；第二次30项一致跳过；777文件逐一校验。未执行任何技能脚本或改本Mac技能目录，见`skills-transfer-validation.json`。
- 数值内核0.1.1 SHA256仍为`d8cb2fc2bf950fbe6b47841f3feb449d553e5f2a7c78d140811c6b2f2ba51ec7`，无需因交接文档改动重跑已通过的58项数值测试。
- CPU证据分块保持原三个归档的字节与哈希，见`release-chunks-validation.json`。独立CPU重建验证仍见`output/reproduction/validation.json`。
- `.gitignore`采用项目内容白名单，Git包含原创源码、测试、协议、分析摘要、TeX、PDF、图表和历史源码。第三方论文全文、私下技能ZIP、插件源码、虚拟环境、原始大数组不入Git；大数组通过Release分块发布。
- 在Windows上尚待实际运行：PowerShell bootstrap、Python CUDA/FP64/grad/JVP/vmap探针、R入口、移植后的采样器、技能发现及其平台兼容性。

使用的技能指导：codebase-design、OpenAI Docs、skill-installer。自定义离线迁移使用项目的校验复制工具；公开GitHub技能安装由目标机使用内置skill-installer及其脚本。插件通过目标机插件目录核对，不复制Mac缓存。

公开交付已完成：`cpu-review-v1`为已发布研究候选Release，18个附件、4,971,229,616字节；每项服务器SHA256和大小均与本地一致，见`published-release-verification.json`。上传前的合成输入来源与归档排查见`evidence-content-audit.json`。历史CPU归档内的“no public publication”是创建当时的状态，原始归档未修改；本次发布依据2026-10-04用户创建仓库并要求上传项目的新授权。私下30技能ZIP不在公开附件中。
