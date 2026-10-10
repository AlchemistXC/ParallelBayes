"""Describe verified report contents without inventing scientific conclusions."""
import json
from pathlib import Path


def tex(value):
    replacements={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#',
                  '_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
    return ''.join(replacements.get(c,c) for c in str(value))


def number(value):return '—' if value is None else str(value) if isinstance(value,int) else f'{value:.5g}'


def write_report(output,receipt):
    from formal_report import DISPLAY
    output=Path(output);fixture=receipt['fixture'];formal=receipt['frame']['scope']=='formal_inference'
    if fixture:title='接口测试报告（人工数据）';notice='人工夹具，仅用于验证软件与版面；不得作为研究结果或纳入论文结论。'
    elif formal:title='正式实验分析附件';notice='固定预算下的已核验记录；失败、缺失与参考不确定性仍须参与解释。'
    else:title='有限技术验收分析附件';notice='技术验收，不是正式推断实验；不计算正式重复区间，不证明后验收敛。'
    lines=['# ParallelBayes：'+title,'',notice,'',
        '本报告从给定统计清单重建，没有重新采样、运行R诊断或估计新的区间。完整研究或后验收敛不由本报告自动判定。',
        '',f"统计清单 SHA256：`{receipt['statistics_manifest_sha256']}`。",'',
        '独立单位为一次完整四链重复。缓存使用预选原输入，每输入一次初始及三次准备后调用不增加独立重复数。',
        '正式统计模式的误差及成本区间沿用9,999次共享整体重复重采样的逐点95% BCa区间，至少20个合格重复；不可判定保留原因，不补零宽区间。技术验收模式不生成这些正式区间。没有同时覆盖或多重比较校正的声明。',
        '有限MCMC参考的MCSE与共享参考偏移敏感性另存；数值积分未认证，未定参考没有误差点。参考不确定性没有传播进BCa区间。',
        '普通工作流、研究审计执行、额外核验和总调用分开记录，不累加嵌套时间。缓存执行比大于1不表示可靠推断加速。',
        'CSV空单元表示不可用；完整状态与分母在同一行或对应JSON中。没有通过筛掉失败、常量函数、慢配置或未定参考来生成图件。','',
        '| 目标 | 计划主任务 | 计划缓存 | 主任务证据状态 | 缓存证据状态 |','|---|---:|---:|---|---|']
    compact=receipt['frame'].get('execution_contract')=='windows-compact-contract-v1'
    if compact and formal:
        lines[4:4]=['本研究是旧采样启动后的资源修订；旧结果单独保留，未合入新重复。新正式研究为24次完整四链重复、1024/4096两个固定预算；缓存每格4份输入仅作描述，区间留空，失败不以成功子调用替代。','']
    elif compact:
        lines[4:4]=['本附件是独立紧凑技术验收：18主任务、16缓存探测/64调用，正式重复数为0；技术输入不并入正式研究，不生成区间。','']
    body=[r'\documentclass[UTF8,fontset=fandol,a4paper]{ctexart}',r'\usepackage[margin=20mm,headheight=16pt]{geometry}',
          r'\usepackage{booktabs,longtable,graphicx,hyperref,fancyhdr,array}',r'\hypersetup{hidelinks}',
          r'\newcolumntype{P}[1]{>{\raggedright\arraybackslash}p{#1}}',
          r'\pagestyle{fancy}\fancyhf{}',r'\fancyhead[C]{\small '+tex(title)+r'}\fancyfoot[C]{\thepage}',
          r'\setlength{\parindent}{0pt}\setlength{\parskip}{5pt}',r'\begin{document}',
          r'\begin{center}{\Large\bfseries ParallelBayes：'+tex(title)+r'}\end{center}',tex(notice),
          '本报告不自动判定研究完成或后验收敛。缺失证据保持缺失；数值有效输出仍可能有探索问题。',
          r'正式模式的区间是逐点95\% BCa区间，以完整四链重复为单位，缓存调用不增加独立样本数。技术验收不生成正式区间；失败和未知时间不填零。',
          r'\section*{任务框架}',r'\begin{longtable}{lrrp{46mm}p{46mm}}',r'\toprule 目标 & 主任务 & 缓存 & 主任务状态 & 缓存状态 \\ \midrule\endhead']
    if compact and formal:
        body[body.index(r'\section*{任务框架}'):body.index(r'\section*{任务框架}')]=[
            r'本研究是旧采样启动后的资源修订，不是完全事前预注册。旧结果未混入新24次完整四链重复。仅比较1024/4096预算；缓存每格4输入只作描述，不生成区间，不用成功子调用替代不合格输入。']
    elif compact:
        body[body.index(r'\section*{任务框架}'):body.index(r'\section*{任务框架}')]=[
            '本附件仅为独立紧凑技术验收：18主任务、16缓存探测/64调用，正式重复数为0，不生成区间。']
    for model in receipt['source_models']:
        name=model['model'];s=model['summary']
        a=json.dumps(s['main_dispositions'],sort_keys=True);b=json.dumps(s['cache_dispositions'],sort_keys=True)
        lines.append(f"| {name} | {s['main_planned']} | {s['cache_planned']} | `{a}` | `{b}` |")
        body.append(' & '.join(map(tex,[name,s['main_planned'],s['cache_planned'],a,b]))+r' \\')
    body.extend([r'\bottomrule\end{longtable}',
        r'各目标的 task\_costs.csv 按任务保留原调用记录汇总的已知费用与未知项；diagnostics.csv 按函数、工作流和预算保留诊断分母。',
        '图中若采用对称对数坐标，其线性区阈值记录在对应 contract.json；零点保持原值，不以小正数替代。',
        '未显示误差--成本点的行仍保留于来源表。原因为参考未定、估计不可用或同一函数有效重复中费用不完整。'])
    for model in receipt['source_models']:
        name=model['model'];tables=json.loads((output/name/'tables.json').read_text(encoding='utf-8'))
        body.extend([r'\clearpage\section*{'+tex(name)+'：诊断与资格}',
            '下表每行的计划数以完整四链重复为单位。已收到的不可判定诊断与未收到诊断分开；Rhat阈值只用于描述，不是整体后验可信的充分条件。',
            r'\begingroup\footnotesize\begin{longtable}{P{28mm}P{40mm}rrrrr}',
            r'\toprule 函数 & 工作流/预算 & 计划 & 缺诊断 & 未定Rhat & Rhat$>1.01$ & 最小尾ESS \\ \midrule\endhead'])
        for r in tables['diagnostics']:
            values=[r['function'],DISPLAY[r['workflow']]+' / '+str(r['budget']),r['planned'],r['missing'],
                    r['rhat_undefined'],r['rhat_above_1_01'],number(r['ess_tail_minimum'])]
            cells=[tex(v) for v in values]
            cells[0]=cells[0].replace(r'\_',r'\_\allowbreak{}')
            body.append(' & '.join(cells)+r' \\')
        body.extend([r'\bottomrule\end{longtable}\endgroup'])
        if tables['nuts']:
            body.extend([r'\subsection*{NUTS诊断}',
                '发散总数只对收到的记录计数，未知不填零。树深度命中若未被上游提供，仍不可判定；两者不会把数值有效自动变成统计收敛。',
                r'\begin{longtable}{rrrrrr}',r'\toprule 预算 & 计划 & 有记录任务 & 已知发散 & 未知链数 & 完整树深命中 \\ \midrule\endhead'])
            for r in tables['nuts']:
                values=[r['budget'],r['planned_tasks'],r['received_tasks'],r['known_divergences'],r['unknown_divergence_chains'],number(r['complete_tree_depth_hits'])]
                body.append(' & '.join(map(tex,values))+r' \\')
            body.extend([r'\bottomrule\end{longtable}'])
    lines.extend(['','所有来源表、可用性状态、逐任务费用及完整诊断见各模型子目录。图件是逐模型/函数的完整附件；正文主图选择须依据实际论证，不以获得有利结果为条件。',''])
    for figure in receipt['figures']:
        function=figure.get('function');label=figure['model']+(' / '+function if function else ' / execution costs')
        caption=('三个口径分别回答已准备内核、普通工作流和含审计执行的成本问题。RWM比较Online Picard与顺序执行，MALA比较quasi-DEER与顺序执行。点为同核顺序/时间成本比的配对几何均值，线为比值尺度的逐点95% BCa区间；右侧标注共同有效重复数，星号表示点不可用。'
            if figure['kind']=='execution_costs' else
            '左图为各已测预算下的条件误差和同一函数可用重复上的普通成本。横纵区间分别为逐点95% BCa区间，不是联合置信区域。右图为共同有效重复上MH平方损失减CPU NUTS平方损失，零线不是显著性门槛。没有预算插值或精确达到精度时间的声明。')
        if figure['kind']=='execution_costs' and compact and formal:
            caption=('缓存每格4份预选输入，仅给描述性配对比，不生成区间；每输入初次及全部三次prepared调用均核验合格且计时齐全后才使用prepared中位数。'
                '普通工作流与含审计执行使用24次原始四链主任务的共同有效重复；至少20份时给逐点95% BCa区间，否则区间未定。'
                '点为共同合格输入上顺序/时间成本比的几何均值。RWM比较Online Picard，MALA比较quasi-DEER；缓存比不是普通后验推断加速。')
        elif figure['kind']=='execution_costs' and not formal:
            caption=('技术输入的同核顺序/时间成本比仅作描述，不生成区间，也不增加正式重复。'
                '初次及全部三次prepared调用完整核验和计时均合格才给缓存中位数；失败或缺失保持未定。'
                '普通工作流、缓存与含审计执行费用分开，缓存比不证明推断加速或后验收敛。')
        caption+=' 空心标记表示区间不可判定；缺失点不补零。完整分母、缺失原因、参考类别及配对四格表见来源数据。'
        if fixture:caption='人工数据，仅作接口和版面检查。'+caption
        lines.extend(['### '+label,'',f"![{label}]({figure['file'][:-4]}.png)",'',caption,'',f"来源：[{figure['source_table']}]({figure['source_table']})。",''])
        body.extend([r'\clearpage\section*{'+tex(label)+r'}',
            r'\begin{center}\includegraphics[width=\linewidth,height=.74\textheight,keepaspectratio]{'+figure['file']+r'}\end{center}',tex(caption)])
    lines.extend(['## 仍须核验','',
        '原始结果、冻结协议与执行环境的审计属于上游接收步骤。本报告不能代替实际Windows验收、正式实验、完整研究复现或作者审阅。',
        '每次改变绘图数据或布局后，须重做最终PDF字体、碰撞与逐面板检查。相关检查不是统计正确性的证明。'])
    body.extend([r'\clearpage\section*{来源与边界}',
        '来源统计清单SHA256：'+r'\texttt{'+receipt['statistics_manifest_sha256'][:32]+r'}\par\texttt{'+receipt['statistics_manifest_sha256'][32:]+r'}',
        '原坐标函数、参考类别及MCSE保留于参考契约和来源表。有限参考偏移范围不是参考误差已传播的区间；未认证积分不称为解析真值。',
        '本文件及图件是可重建分析附件，不代替完整研究终稿、原始证据审计或作者审阅。',r'\end{document}'])
    (output/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (output/'report.tex').write_text('\n'.join(body)+'\n',encoding='utf-8')
