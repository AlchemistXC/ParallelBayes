# 当前稿件的结果段重建

当前入口为 `scripts/release/rebuild_current_results.py`。它将五个生成结果段、其已保存
分析输入和当前论文依赖收集成独立目录，再从新目录执行生成器并逐字节比较。
这是**已保存摘要到论文的重建**：不重跑采样、原始数组统计、R诊断或绘图，
不能单凭它关闭完整研究的F5验收。范围和实际核验见
[CURRENT-RESULT-REBUILD](CURRENT-RESULT-REBUILD.md)。

CPU输入从已核对整体SHA256的 `evidence-paper-cpu-review-v1.tar` 取出，逐项再与归档内manifest比对；
Windows输入从已独立接收的第一轮目录取出，生成器核对协议身份、摘要所绑定的逐任务记录与现代诊断哈希。
当前F1/F2伴随摘要和第二轮接收摘要分别保留，不把尚未收到的192项机制任务写成完成。

```sh
# Python需要NumPy；无需torch/CUDA，也不调用采样器。
python scripts/release/rebuild_current_results.py prepare \
  --cpu-archive /path/to/evidence-paper-cpu-review-v1.tar \
  --windows /path/to/extracted-windows-native-v1 \
  --output /path/to/new-result-inputs

# 可把整个输入目录移到其他位置，再用包内脚本重建；输出目录必须不存在。
python /path/to/new-result-inputs/scripts/release/rebuild_current_results.py rebuild \
  --capsule /path/to/new-result-inputs --output /path/to/new-rebuild

cd /path/to/new-rebuild/manuscript/software
tectonic 软件与基准研究.tex
```

当前Windows-v1生成器是固定历史协议的入口，不能用于未审查的新协议。其主要速度范围、
高Rhat/常量拟合计数、诊断极值及成本从已保存记录核算；环境、实现、SBC和接收叙述
使用该历史版本的已审查模板，未宣称每一句叙述都由原始轨迹自动推导。
版本、输入哈希和生成命令写入MANIFEST/REBUILD，丢失或损坏输入明确报错。
现有矢量图按原文件交付，不把成功编译当作图表数值复算。

下面保留**历史CPU归档**的原始数组重建方法。应在该归档独立解压目录及其锁定环境中执行，
不要在当前开发工作树覆盖数据，也不要用历史CPU范围说明判断当前Windows能力。

# 历史CPU：从原始证据重建结果

这些步骤读取完整原始任务，不按速度、收敛情况或结果方向挑选任务。结果目录含运行manifest、逐任务state、尝试目录、配置、result、raw.npz和校验和。重建要求所有预定任务已结束；缺失、额外、来源错误或文件损坏都会被拒绝。

## 重建CPU主结果

在本项目根目录及锁定环境中执行。计算不重新抽样，第一次测得的摘要/诊断耗时会保存，后续重建复用该记录。

```sh
.venv/bin/python benchmark/analysis/analyze.py reference --protocol benchmark/protocols/reference-v1.json --runs benchmark/runs/cpu-reference-v1 --output benchmark/analysis/outputs/reference-summary.json
.venv/bin/python benchmark/analysis/analyze.py formal --protocol benchmark/protocols/protocol-v1.json --runs benchmark/runs/cpu-formal-v1 --reference benchmark/analysis/outputs/reference-summary.json --output benchmark/analysis/outputs/cpu-formal
.venv/bin/python scripts/write-results-tex.py
.venv/bin/python benchmark/analysis/figures.py
.venv/bin/python benchmark/analysis/sbc-functions.py --runs execution/statistical-v4 --output execution/statistical-v4/likelihood-ranks.json
```

`analysis-provenance.json`将分析代码、协议、运行manifest、每个任务状态及参考摘要关联起来。参考摘要另有来源文件。`run-metrics.json`保存逐重复数值，`formal-summary.json`保留全部组、失败分母、成本及精度未判定状态，`paired-speedups.csv`保留同核配对。

`sbc-functions-v1`在正式64个数据集拟合之前冻结，对保存的样本计算依赖数据的对数似然秩、并列数和解析期望误差。它是独立分析协议，不改变`statistical-v4`的采样配置。这个历史CPU协议不包含GPU结果；当前Windows阶段使用另外的版本、协议和原始证据。

## 重新执行历史CPU协议

当前0.1.1不能冒充0.1.0继续旧协议。若确需完整重跑，先解压归档源码到独立目录，将原核心锁复制进去，再在该目录中通过PYTHONPATH选中归档内核。原始protocol-v1含完整合成数据，不需要另找外部数据。

```sh
mkdir -p execution/reproduce-v1/environment/locks
tar -xzf execution/source-snapshots/formal-v1-source.tar.gz -C execution/reproduce-v1
cp environment/locks/python-core.txt execution/reproduce-v1/environment/locks/
```

然后从`execution/reproduce-v1`目录运行以下命令。路径变量只用于定位本项目，不改变系统HOME。

```sh
PB_ORIGINAL_PROJECT="$(cd ../.. && pwd)"
PYTHONPATH="$PWD/r-package/inst/python" "$PB_ORIGINAL_PROJECT/.venv/bin/python" -m parallelbayes.cli run "$PB_ORIGINAL_PROJECT/benchmark/protocols/protocol-v1.json" --output "$PB_ORIGINAL_PROJECT/benchmark/runs/reproduced-cpu-formal-v1"
```

这会重新执行全部1920任务，耗时较长；没有默认短时截止。使用新结果目录，不覆盖原始研究。源码/依赖哈希必须通过，不能仅把协议中的哈希改成当前代码。

## 失败重放

MH原始NPZ中包含`tape__noise`、`tape__log_uniform`和`tape__directions`，结合任务模型、初值、配置及对应源码，调用`sample(model, config, tape=...)`即可重新执行实际输入。NUTS使用记录的JAX版本、种子和适配配置。数值失败与硬件/资源失败需要分别解释，硬件条件改变后不能预设相同失败事件。

0.1.1记录`primary_failed_trajectory`和最终`failed_trajectory`，Stan部分链还记录`completed_steps`。编译或设备异常在程序尚未返回轨迹时只能保留配置、环境和异常，不能补造不可取得的数组。

## 版本边界

CPU主结果是0.1.0／protocol-v1；历史GPU交接归档为0.1.1／protocol-v3（当前不执行）；正式64数据集SBC使用0.1.1／statistical-v4。未执行的中间审查协议与源码快照保留，仅用于追踪修订。跨机器各自的同核比较可以分析，但不同源码版本不能直接归因为纯硬件差异。
