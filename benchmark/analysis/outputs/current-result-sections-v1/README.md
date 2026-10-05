# 当前结果段与PDF重建：紧凑证据

源码b7ad1d167e889efad764bf092257fee0c24925f7；五份结果段通过40项来源绑定资产重建。
完整本地归档为output/research-completion/current-result-sections-v1.tar，
12,646,400字节，SHA256 c233a8acfc3bdef4c620e999914d139e582fcb56b14d5ad99358c5d5270c1a6b。
62项资产加manifest共63文件，解压后全部校验，公共入口在搬移目录再次重建五段。

只核验已保存摘要/逐任务记录到结果文本和PDF；不新增采样、R诊断、图形重算或正式重复。
23页PDF只有第12页文字/像素发生预期变化，其余22页与文献修订版一致。
compile日志含多遍编译：初始遍出现暂未解析引用，最终遍无警告。
三项保护检查使用初版内容包，入口源码与最终版本相同；最终内容仅改中文范围说明。
检查不能计入采样器测试数量。历史路径保留在日志，搬移重建入口不依赖这些路径。

详细边界与重建命令见docs/CURRENT-RESULT-REBUILD.md、docs/REBUILD-RESULTS.md。
原始协议与历史结果未修改；F2/F3/F5/F6尚未关闭。未自动发布Release。
