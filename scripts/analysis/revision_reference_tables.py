#!/usr/bin/env python3
"""Project archived reference evidence into manuscript-review-v2 tables.

Read-only with respect to frozen protocols, fit results and reference draws.
No sampling, reference replacement, bootstrap regeneration or eligibility change.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(x, digits=3):
    if x is None:
        return r'未定'
    if x == 0:
        return '$0$'
    if abs(x) >= .001 and abs(x) < 10:
        return f'${x:.{digits+2}f}$'
    a, b = f'{x:.{digits-1}e}'.split('e')
    return f'${a}\\times10^{{{int(b)}}}$'


LABELS = {
 'alpha':r'$\alpha$', 'beta':r'$\beta$',
 'alpha_squared':r'$\alpha^2$', 'beta_squared':r'$\beta^2$',
 'p_switch_0m':r'$p(0)$', 'p_switch_100m':r'$p(100)$',
 'beta_positive':r'$\ind(\beta>0)$',
 'q1':r'$\theta_1$', 'q2':r'$\theta_2$',
 'sigmoid_q1':r'$\sigma(\theta_1)$', 'q1_positive':r'$\ind(\theta_1>0)$'}


def table(headers, rows, caption, label, alignment):
    out=[r'\begin{table}[htbp]\centering\small',
         '\\begin{tabular}{'+alignment+'}\\toprule',
         ' & '.join(headers)+r'\\\midrule']
    out += [' & '.join(row)+r'\\' for row in rows]
    out += [r'\bottomrule\end{tabular}', '\\caption{'+caption+'}',
            '\\label{'+label+'}',r'\end{table}']
    return '\n'.join(out)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--statistics',type=Path,required=True)
    parser.add_argument('--wells-reference-binary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--tex',type=Path,required=True)
    args=parser.parse_args()
    root=args.project.resolve(); stats=args.statistics.resolve(); sources={}
    def read(path, identity=None):
        path=Path(path); sources[identity or str(path.relative_to(root))]=digest(path)
        return json.loads(path.read_text())
    manifest=read(stats/'SHA256.json','formal-statistics/SHA256.json')
    # Pin the independently rebuilt statistics, not a similarly named directory.
    if digest(stats/'SHA256.json')!='d928a497889e11f6aaf5829bf1ffd807a647a880a5d4ae7cef4acf3046c34bfb':
        raise ValueError('Unexpected complete statistics manifest')
    def statread(name):
        path=stats/name
        if digest(path)!=manifest[name]: raise ValueError('Statistics hash mismatch: '+name)
        return read(path,'formal-statistics/'+name)
    refs=statread('reference-contract.json')
    quad=read(root/'benchmark/analysis/outputs/wells-quadrature-v1/result.json')
    comparison=read(root/'benchmark/analysis/outputs/wells-quadrature-v1/comparison.json')
    mc=read(root/'benchmark/analysis/outputs/wells-reference-v1/diagnostics.json')
    receipt=read(root/'benchmark/analysis/outputs/wells-reference-v1/receipt.json')
    qprotocol=read(root/'benchmark/protocols/wells-quadrature-v1.json')
    lr=read(root/'benchmark/analysis/outputs/reference-summary.json')
    provenance=read(root/'benchmark/analysis/outputs/reference-summary.provenance.json')
    reuse=read(root/'benchmark/analysis/outputs/completion-f3/reference-reuse.json')
    refprotocol=read(root/'benchmark/protocols/reference-v1.json')
    if digest(root/'benchmark/analysis/outputs/reference-summary.json')!=provenance['summary_sha256']:
        raise ValueError('L1/L2 reference provenance mismatch')
    if refs['W1']['base_target_id']!=quad['target_id'] or quad['target_id']!=receipt['target_id']:
        raise ValueError('W1 target identity differs')
    grid={(r['radius'],r['order']):r for r in quad['rows']}
    if set(grid)!={(r,n) for r in qprotocol['radii'] for n in qprotocol['orders']}:
        raise ValueError('Incomplete quadrature grid')
    if refs['W1']['means']!=grid[(12,96)]['means']:
        raise ValueError('Formal W1 reference is not preselected quadrature')
    wells=[]
    for j,name in enumerate(quad['functions']):
        m=mc['summary'][j]; c=comparison['comparisons'][j]
        assert m['variable']==name and c['function']==name
        wells.append(dict(function=name,reference=refs['W1']['means'][j],
          change_order_64_to_96_at_R12=abs(grid[(12,96)]['means'][j]-grid[(12,64)]['means'][j]),
          change_radius_10_to_12_at_n96=abs(grid[(12,96)]['means'][j]-grid[(10,96)]['means'][j]),
          change_radius_6_to_12_at_n96=abs(grid[(12,96)]['means'][j]-grid[(6,96)]['means'][j]),
          maximum_change_from_selected_over_12_grids=max(abs(r['means'][j]-refs['W1']['means'][j]) for r in quad['rows']),
          finite_mcmc_mean=m['mean'], finite_mcmc_mcse=m['mcse_max_available'],
          mcmc_minus_quadrature=m['mean']-refs['W1']['means'][j],
          uncertainty_status='uncertified_numerical_reference',
          tail_only_float_estimate=grid[(12,96)]['tail_only_mean_error_estimate'][j]))
    logistic=[]; existing=[]
    for model in ['L1','L2']:
        assert refs[model]['means']==lr[model]['mean']
        assert refs[model]['mcse']==lr[model]['mcse_conservative']
        assert refs[model]['base_target_id']==provenance['model_sha256'][model]
        for j,name in enumerate(refs[model]['names']):
            logistic.append(dict(model=model,function=name,reference=lr[model]['mean'][j],
              batch_mcse=lr[model]['batch_mcse'][j],between_fit_mcse=lr[model]['between_fit_mcse'][j],
              retained_mcse=lr[model]['mcse_conservative'][j],
              reference_fit_mean_min=min(x[j] for x in lr[model]['reference_means']),
              reference_fit_mean_max=max(x[j] for x in lr[model]['reference_means']),
              kind=refs[model]['kinds'][j],positive_count=lr[model]['event_positive_counts'][j]))
            f=statread(f'{model}/function-{j}.json')
            pairs=[r for r in f['error']['pairs'] if r['workflow_a']=='cpu-mala-sequential@4096'
                   and r['workflow_b']=='cpu-nuts-spawn_chains@4096']
            if len(pairs)!=1: raise ValueError('Missing unique logistic comparison')
            r=pairs[0]
            existing.append(dict(model=model,function=name,comparison='CPU MALA sequential minus CPU Pyro NUTS; N=4096',
              common_valid=r['validity_table']['n11'],planned=r['planned'],
              point_difference=r['conditional_mean_loss_difference'],
              shift_min=r['reference_shift_min'],shift_max=r['reference_shift_max'],
              interval_status=r['interval_status'],shift_rule='reference +/- 2 estimated MCSE; not a confidence interval'))
    # Pair original repetitions, never list-order entries or individual chains.
    frame_path=stats/'W1.frame.ndjson'
    if digest(frame_path)!=manifest['W1.frame.ndjson']: raise ValueError('W1 frame hash differs')
    sources['formal-statistics/W1.frame.ndjson']=digest(frame_path)
    rows=[json.loads(line) for line in frame_path.read_text().splitlines()]
    sensitivity=[]
    for budget in [1024,4096]:
        for j,name in enumerate(quad['functions']):
            groups=[]
            for workflow in ['cpu-mala-sequential','cpu-nuts-spawn_chains']:
                selected=[r for r in rows if r['phase']=='main' and r['task']['budget']==budget
                          and r['task']['workflow']==workflow]
                if len(selected)!=24: raise ValueError('Unexpected W1 planned denominator')
                eligible={r['task']['replicate']:r['means'][j] for r in selected
                          if r['outcome']=='valid' and math.isfinite(r['means'][j])}
                groups.append(eligible)
            common=sorted(set(groups[0])&set(groups[1]))
            if len(common)!=24: raise ValueError('W1 comparison no longer has all 24 pairs')
            a,b=[np.array([g[k] for k in common]) for g in groups]
            mu=refs['W1']['means'][j]; s=wells[j]['finite_mcmc_mcse']; alt=wells[j]['finite_mcmc_mean']
            def loss(c): return float(np.mean((a-c)**2-(b-c)**2))
            D=loss(mu); delta=float(np.mean(a-b))
            saved=statread(f'W1/function-{j}.json')
            saved_pair=next(r for r in saved['error']['pairs']
              if r['workflow_a']==f'cpu-mala-sequential@{budget}' and r['workflow_b']==f'cpu-nuts-spawn_chains@{budget}')
            if not math.isclose(D,saved_pair['conditional_mean_loss_difference'],abs_tol=1e-18,rel_tol=1e-12):
                raise ValueError('Paired loss disagrees with frozen analysis')
            # This algebra check is separate from the saved aggregate check.
            for c in [g['means'][j] for g in quad['rows']]+[alt]:
                if not math.isclose(loss(c),D-2*(c-mu)*delta,abs_tol=1e-18,rel_tol=1e-10):
                    raise ValueError('Common-reference shift identity failed')
            row=dict(function=name,budget=budget,common_replicates=common,n=24,
              difference_A_minus_B=D,mean_A=float(np.mean(a)),mean_B=float(np.mean(b)),
              mean_A_minus_B=delta,reference_shift_to_equal_loss=None if delta==0 else D/(2*delta),
              fixed_reference_pointwise_BCa=saved_pair['confidence_interval'],
              difference_using_mcmc_reference_point=loss(alt),
              all_grid_differences=[dict(radius=g['radius'],order=g['order'],difference=loss(g['means'][j])) for g in quad['rows']],
              stress_scope='uses the independent finite-MCMC MCSE as a hypothetical reference-shift scale; not an estimate or bound of quadrature error')
            if s is not None:
                for width in [1.96,2.0]:
                    lo,hi=sorted([loss(mu-width*s),loss(mu+width*s)])
                    row[f'stress_plus_minus_{width:g}_MCSE']=dict(minimum=lo,maximum=hi,sign_can_change=lo<0<hi)
            sensitivity.append(row)
    binary=args.wells_reference_binary.resolve()
    if digest(binary)!=receipt['binary_sha256']: raise ValueError('W1 reference binary identity differs')
    sources['independent-wells-reference/values-f64le.bin']=digest(binary)
    values=np.fromfile(binary,dtype='<f8').reshape(tuple(mc['dimensions']),order='F')
    posterior=[]
    for j in [0,1,4,5]:
        x=values[:,:,j].ravel(); m=float(x.mean())
        if not math.isclose(m,mc['summary'][j]['mean'],abs_tol=1e-13): raise ValueError('Wrong reference array ordering')
        q=np.quantile(x,[.025,.975],method='linear')
        posterior.append(dict(function=quad['functions'][j],mean=m,posterior_equal_tail_95=[float(v) for v in q],
          reference_mean_mcse=mc['summary'][j]['mcse_max_available'],
          quantile_estimation_uncertainty='not quantified',
          source='pre-existing independent posteriorDB Stan reference; 10 chains x 1000 thinned draws; no formal-fit selection',
          quantile_rule='NumPy linear, equivalent to R type 7'))
    summary=dict(identity='manuscript-review-v2-reference-companion',scope='post hoc presentation and reference-shift analysis only; no sampling or protocol change',
      W1=wells,W1_quadrature=dict(center=quad['center'],scale_cholesky=quad['scale_cholesky'],radii=qprotocol['radii'],orders=qprotocol['orders'],
      selected=[12,96],root_gradient_max=quad['root']['gradient_max'],root_evaluations=quad['root']['evaluations'],
      all_grids=quad['rows'],integration=qprotocol['integration'],tail_control=qprotocol['tail_control'],error_interpretation=qprotocol['error_interpretation']),
      W1_mcmc_generation=receipt['upstream_generation'],W1_mcmc_replication=receipt['replication'],
      logistic=logistic,logistic_generation=dict(protocol='reference-v1',defaults=refprotocol['defaults'],
      independent_fits_per_model=4,total_correlated_draws_per_model=262144,
      summary_provenance=provenance,raw_reuse_audit=summary_of_reuse(reuse)),
      existing_logistic_reference_sensitivity=existing,W1_pair_sensitivity=sensitivity,W1_posterior_summary=posterior,
      interpretation=dict(formula='D(c+e)=D(c)-2*e*(mean_A-mean_B), same common set and same s_f=1',
      W1_long_budget='All six continuous function point differences favour the specified NUTS workflow for every saved quadrature and the independent MCMC reference point; all six can reverse within the hypothetical +/-2 MCMC-MCSE shift. No certified quadrature-error radius is available.',
      rare_event='All W1 fitted event estimates are zero. The nonzero squared discrepancy is the square of the common numerical reference, not evidence of resolved event estimation.'),sources=sources)
    args.output.mkdir(parents=True,exist_ok=True)
    write_json(args.output/'reference-summary.json',summary)
    args.tex.parent.mkdir(parents=True,exist_ok=True)
    args.tex.write_text(make_tex(summary),encoding='utf-8')
    report=make_report(summary,args)
    (args.output/'reference-review.md').write_text(report,encoding='utf-8')
    proof=dict(source_script_sha256=digest(Path(__file__)),reference_summary_sha256=digest(args.output/'reference-summary.json'),
      tex_sha256=digest(args.tex),review_sha256=digest(args.output/'reference-review.md'),
      checks=['formal statistics manifest and all consumed member hashes','W1 target/reference identity','L1/L2 provenance and means/MCSE identity',
      '24 planned/common W1 repetitions per method/budget/function','saved paired loss reproduced','reference-shift identity independently checked',
      'reference binary SHA and 7-variable R-column-major layout checked','posterior means agree with archived R summary'],
      new_sampling_calls=0,scientific_status_or_reference_changes=0)
    write_json(args.output/'reference-validation.json',proof)
    print(json.dumps(proof,ensure_ascii=False,indent=2))


def summary_of_reuse(d):
    return {m:{k:d['models'][m][k] for k in ['specification_exactly_equal','target_id','independent_fits','chains_per_fit','draws_per_chain','total_correlated_draws','sign_event_positive_count','limitations']} for m in ['L1','L2']}


def write_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')


def make_tex(d):
    out=[r'''% Generated by scripts/analysis/revision_reference_tables.py; do not hand-edit numbers.
\section{参考值、数值稳定性与比较敏感性}
\label{sec:reference-precision}
本节直接整理冻结参考和主要实验的保存统计量；参考偏移分析与后验区间摘要是收到本轮意见后的伴随分析，不改变原参考、可用集合或实验协议。
\subsection{W1的逐函数参考}
在驻点附近采用固定坐标$\theta=m+Cz$，其中
\[
m=(0.6059593596,-0.6218819313)^\mathsf T,\qquad
C=\begin{pmatrix}0.0603102245&0\\-0.0768479318&0.0598848727\end{pmatrix}.
\]
驻点由解析NumPy梯度求得，最大梯度绝对值为$8.68\times10^{-14}$；$CC^\mathsf T$为该点观测信息的逆。
在$[-R,R]^2$内作张量Gauss--Legendre求积，$R\in\{6,8,10,12\}$，每轴阶数$n\in\{32,64,96\}$，保留全部12个结果。事件$\beta>0$另按边界分段积分。使用预先选定的$(R,n)=(12,96)$，没有按与MCMC的接近程度选择参考。
''']
    rows=[]
    for r in d['W1']:
        rows.append([LABELS[r['function']],number(r['reference'],7),number(r['change_order_64_to_96_at_R12']),
          number(r['change_radius_10_to_12_at_n96']),number(r['mcmc_minus_quadrature']),number(r['finite_mcmc_mcse'])])
    out.append(table(['函数','求积参考','加密变化','扩域变化','MCMC减求积','MCMC MCSE'],rows,
      'W1参考精度摘要。加密变化为$R=12$时64到96阶之差；扩域变化为96阶时$R=10$到12之差。后两列来自独立的既有Stan参考；MCSE取posterior、链间均值和批均值三种估计的可用最大值。上述变化是数值稳定性指标，不是认证误差界。','tab:reference-wells','lrrrrr'))
    out.append(r'''独立MCMC参考来自posteriorDB的一次Stan生成：10链，每链总迭代20000、预热10000、每10步保留一次，得到每链1000个相关样本；不是10000个独立实验。六个连续函数的MCSE为有限估计，不能约束共同偏差。事件样本全部为零，MCSE仍未定。

基于全局对数凹性支持平面的尾部积分不等式，256个角扇区给出的$R=12$尾质量/计算归一化常数为$7.47\times10^{-30}$。这是浮点计算的尾部上界估计，不包含区间算术认证、内部求积或舍入误差。六个连续均值从$R=6$到12的最大变化约$1.87\times10^{-9}$；事件由$4.34669\times10^{-11}$变为$4.76721\times10^{-11}$。完整12组值及各函数尾部估计保存在参考伴随数据中。
''')
    out.append(r'\subsection{L1/L2有限参考及已有偏移分析}')
    rows=[[r['model'],LABELS[r['function']],number(r['reference'],7),number(r['batch_mcse']) if r['kind']!='unresolved' else '未定',number(r['between_fit_mcse']) if r['kind']!='unresolved' else '未定',number(r['retained_mcse'])] for r in d['logistic']]
    out.append(table(['目标','函数','参考均值','批均值MCSE','拟合间MCSE','采用MCSE'],rows,
      'L1/L2逐函数有限参考。每模型四份独立四链拟合，每链保留16384步，共262144个相关样本；参考是归档reference-v1的既有BlackJAX NUTS结果。L2符号事件的原始机械方差计算为零，正式不确定性仍保留未定。','tab:reference-logistic','llrrrr'))
    out.append(r'''四份参考拟合的种子与主要实验分离，模型数据和目标哈希经复用审查一致；每链预热1024步，最大树深10。四份拟合未记录发散，但这些检查不能排除参考的共同偏差。MCSE取批均值与拟合间估计的较大者。L1符号事件出现28624次，L2为零；后者不能作为精确零概率参考。

原正式分析已对有限MCMC参考作共同偏移$\mu^\star\pm2\,\mathrm{MCSE}$敏感性计算。在4096预算CPU顺序MALA与CPU Pyro NUTS的比较中，L1四函数及L2前三函数的损失差在该范围内均保持正号；但每格仅六个共同有效重复，未达到20份的区间计算下限。L2符号事件保持未定。逐函数上下限保存在参考伴随JSON；这一偏移范围不是置信区间，且没有扣除参考方差。
''')
    out.append(r'''\subsection{W1比较对参考偏移的敏感性}
在相同可用重复集合和同一尺度$s_f=1$下，记两方法平均平方损失差为$D_f(c)$，参考从$c$移至$c+e$时有
\[
D_f(c+e)=D_f(c)-2e\left(\overline{\widehat\mu}_{A,f}-\overline{\widehat\mu}_{B,f}\right).
\]
这里$A$是CPU顺序MALA、$B$是CPU Pyro NUTS四进程工作流。本表固定共同集合以对应配对比较；改用各自集合会改变所比较的估计对象。若尺度不同，共同平方项一般不再抵消。下表固定4096预算和全部24份共同有效重复。$e_0$为使点损失差变为零的带符号参考偏移；若两方法平均估计相同，该阈值不存在。
''')
    rows=[]
    for r in d['W1_pair_sensitivity']:
        if r['budget']!=4096 or r['function']=='beta_positive': continue
        st=r['stress_plus_minus_2_MCSE']
        rows.append([LABELS[r['function']],number(r['difference_A_minus_B']),number(r['reference_shift_to_equal_loss']),
          number(r['difference_using_mcmc_reference_point']),number(st['minimum'])+' 至 '+number(st['maximum'])])
    out.append(table(['函数','$D_f(c)$','$e_0$','改用MCMC参考',r'$\pm2$ MCSE偏移范围'],rows,
      'W1的参考敏感性。正号表示本格NUTS工作流的平均平方损失较小。末列只是以独立MCMC的MCSE作为假设偏移尺度，不是求积误差估计，也不是置信区间。','tab:reference-sensitivity','lrrrr'))
    out.append(r'''六个连续函数在全部12个保存求积值以及独立MCMC参考点下保持相同点排序；在假设$\pm2$ MCSE偏移内，六者均可改变符号。因此数据支持对已检查参考点的稳定性，尚不提供对未知真值的认证排序。W1的$p(100)$即使在固定参考下，其原逐点BCa损失差区间也包含零。其余五个连续函数的固定参考区间不包含零；这些区间不传播求积参考的不确定性，也未校正多重比较。

所有W1拟合的$\ind(\beta>0)$均值都是零；图中的非零平方差完全由共同数值参考决定。改变共同参考仍使两方法该函数的点损失差为零，这既不确认极小尾概率的估计精度，也不解决常量函数诊断的未定状态。
''')
    out.append(r'\subsection{W1模型给出的后验解释}')
    rows=[[LABELS[r['function']],f"{r['mean']:.6f}",f"[{r['posterior_equal_tail_95'][0]:.6f}, {r['posterior_equal_tail_95'][1]:.6f}]",number(r['reference_mean_mcse'])] for r in d['W1_posterior_summary']]
    out.append(table(['参数或概率','后验均值',r'95\%等尾后验区间','均值MCSE'],rows,
      r'独立既有参考样本的应用摘要。距离以100米为单位，$p(0)=\sigma(\alpha)$，$p(100)=\sigma(\alpha+\beta)$。区间为10000个保存相关样本的经验2.5\%与97.5\%分位数（R type 7等价规则）；它描述后验不确定性，均值MCSE描述有限计算误差。分位数本身的估计误差没有另行量化。','tab:wells-posterior-application','lrrr'))
    out.append(r'''该二维模型中，较远距离与较低的换井概率相联系。以上为已指定模型及其参考样本的后验描述，不把距离系数解释为因果效应；也没有从正式实验中挑选表现较好的拟合。

\noindent\textbf{来源与重建。}表格由随附的参考精度脚本从W1求积与参考档案、L1/L2参考摘要，以及Mac独立重建的正式统计生成。脚本校验目标、参考二进制和读取的统计文件哈希；参考伴随JSON同时保存完整逐函数数值、所有12个求积配置、两预算配对结果和来源SHA。没有新增MCMC或更换原正式参考。
''')
    return '\n'.join(out)+'\n'


def make_report(d,args):
    p=d['W1_posterior_summary']
    return '''# 本轮参考精度意见专项审查

结论：意见合理，应补充已存在的逐函数资料和参考敏感性；不需要重采样或改变正式参考。

- **证据**：W1采用预选R=12、每轴96阶Gauss–Legendre值；12个保存组合均保留。加密/扩域变化极小，但不是认证总误差界。
- **证据**：独立posteriorDB Stan样本的MCSE比求积变化大很多。它衡量这份有限MCMC均值的估计误差，不能替代求积误差。
- **衍生分析**：同一24份四链重复、4096预算CPU顺序MALA减CPU Pyro NUTS的六个连续函数点损失差，对12个保存求积点和独立MCMC参考点均保持正号。但在假设±2 MCMC-MCSE偏移范围内六者均可翻转；±1.96范围结论相同。此为事后敏感性，不是假设已知参考置信区间。
- **限制**：固定参考BCa区间没有传播参考不确定性；p(100)的原固定参考BCa已包含零。其余五函数不跨零也不是未校正的全局结论。
- **意见公式**：在相同有效集合、同一尺度下D(c+e)=D(c)−2e(平均估计A−平均估计B)/s²正确。符号e是新增参考减原参考；未知真值误差的符号要按此定义。使用各自归一化集合时共同平方项仍能抵消，但会改变所比较的估计对象，不再是本表指定共同集合上的配对比较。
- **已有分析**：L1/L2主分析原已执行±2MCSE，七个已定函数在4096预算MALA/NUTS点差保持正号；共同有效仅6份，不能给出正式BCa区间。L2事件仍未定。
- **应用解释**：采用预先存在的独立参考全部10链，未选择正式拟合。补充alpha、beta、p(0)、p(100)的后验均值和95%经验等尾区间；后验区间与参考MCSE分列，分位数的计算误差未量化。
- **未改变**：冻结协议、任务状态、MCMC输出、正式误差参考和区间规则。

## 推荐正文一句

W1的MALA与Pyro NUTS损失差在全部已保存求积参考及独立MCMC参考点下保持相同点排序，但对借用MCMC误差尺度的假设参考偏移并不稳健；因此该比较仍限于所用数值参考，不能视为已认证的真值排序。

## 可重复命令

```sh
python scripts/analysis/revision_reference_tables.py \\
  --statistics /path/to/formal-statistics \\
  --wells-reference-binary /path/to/wells-reference-01/values-f64le.bin \\
  --output benchmark/analysis/outputs/manuscript-review-v2 \\
  --tex manuscript/software/revision-reference.generated.tex
```

具体来源及所有读取SHA见reference-summary.json；reference-validation.json记录核查项及本脚本SHA。没有新采样调用。
'''


if __name__=='__main__':
    main()
