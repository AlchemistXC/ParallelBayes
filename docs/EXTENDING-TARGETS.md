# 新增原生目标的完整示例

本例新增二维Poisson回归：log率为Xβ，β的先验为独立N(0,4)。观测由固定Philox随机流生成，无额外数据下载。正态先验在无约束坐标定义，映射为恒等，Jacobian为0。省略的log(y!)为参数无关常数。

1. `examples/custom-poisson-target.py::poisson_target()`返回公开`Model`对象。spec完整保存X、y、先验、坐标及名称顺序；JAX log_density、独立NumPy reference和解析gradient_reference分开实现。
2. `validate_model()`在零点、正负尺度和尾部点核对相对密度、梯度；结果写入日志。
3. 显式生成同一noise/log_uniform/directions，传给顺序MALA与quasi-DEER，以及顺序RWM与Picard。检查接受事件与路径，而不以相同seed跨框架替代实际随机数组。
4. 失败不进入普通后验对象。成功示例只证明此输入下的接口与数值核验，不证明收敛、一般正确性或性能收益。

从项目根目录执行：

```sh
.venv/bin/python examples/custom-poisson-target.py
Rscript --vanilla examples/custom-poisson-target.R
```

R例使用reticulate载入扩展示例并得到`posterior::draws_array`。0.1.1的`pb_model()`只注册内置kind及Stan路径；它不直接接受任意R闭包。若需要把新目标正式纳入包，应新增支持声明和测试；当前示例无需改动冻结内核源码。示例验证结果保存在execution/custom-target-example.json及execution/custom-target-R-example.json。
