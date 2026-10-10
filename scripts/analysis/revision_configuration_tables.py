#!/usr/bin/env python3
"""Export final compact configurations; read frozen evidence, never sample or tune.

The generated tables refer to the compact protocol rather than historical CPU
configurations. Exact affine matrices and input checks are retained in JSON.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import zipfile

import numpy as np
from scipy.special import expit

EXPECTED = '91bbff0ec47f9f47b64ac4acfd328e2df8834a67b1d24a1c9e35c4fa0a980aeb'
ORDER = ['G1','G2','A1','L1','L2','H1','H2','M1','W1']
SOURCE_NAMES = ['benchmark/protocols/windows-native-v1.json',
    'benchmark/protocols/inference-budget-pilot-mac-v1.json',
    'r-package/inst/python/parallelbayes/reference.py',
    'scripts/completion/inference_setup.py','scripts/completion/inference_targets.py',
    'scripts/completion/formal_inputs.py','scripts/completion/inference_nuts.py',
    'scripts/completion/inference_parallel_nuts.py','scripts/completion/batch_contract.py',
    'scripts/windows/formal_batch_worker.py','scripts/windows/prepare_formal_study.py',
    'examples/affine_target.py','examples/external_wells.py']


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(data):
    return digest(json.dumps(data,sort_keys=True,separators=(',',':'),allow_nan=False).encode())


def file_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')


def export(formal, output, tex):
    formal,output,tex=map(Path,(formal,output,tex))
    p=json.loads((formal/'protocol.json').read_text());unsigned=dict(p);reported=unsigned.pop('protocol_sha256')
    if reported!=EXPECTED or fingerprint(unsigned)!=EXPECTED:raise ValueError('Unexpected compact protocol')
    bound=json.loads((formal/'freeze-manifest.json').read_text())
    if file_hash(formal/'protocol.json')!=bound['protocol.json']:raise ValueError('Protocol file changed')
    sources={}
    for n in SOURCE_NAMES:
        value=file_hash(formal/'source'/n)
        if value!=p['source_files'][n] or value!=bound['source/'+n]:raise ValueError('Frozen source differs: '+n)
        sources[n]=value
    specs=json.loads((formal/'source'/SOURCE_NAMES[0]).read_text())['models']
    catalog=json.loads((formal/'catalog.json').read_text())
    if catalog['targets']!=p['targets']:raise ValueError('Final target catalog differs from compact protocol')
    # Regenerate mathematical definitions solely to check the saved model data.
    # Numerical checks do not change any saved arrays or inference result.
    rng=lambda role:np.random.default_rng(np.random.SeedSequence(role))
    rr=rng([20261003,11]);rotation,_=np.linalg.qr(rr.normal(size=(64,64)))
    spectrum=np.geomspace(1.,100.,64)
    cov=np.einsum('ik,jk,k->ij',rotation,rotation,spectrum)
    checks={'G2_covariance_reconstruction_max_abs':float(np.max(np.abs(cov-specs['G2']['covariance'])))}
    rr=rng([20261003,11]);phi=.9;prior=phi**np.abs(np.arange(64)[:,None]-np.arange(64)[None,:])
    innovation=rr.normal(size=64);latent=np.empty(64);latent[0]=innovation[0]
    for i in range(1,64):latent[i]=phi*latent[i-1]+np.sqrt(1-phi**2)*innovation[i]
    y=latent+rr.normal(size=64);postcov=np.linalg.inv(np.linalg.inv(prior)+np.eye(64))
    postmean=np.einsum('ij,j->i',postcov,y)
    for name,new in [('y',y),('covariance',postcov),('mean',postmean)]:
        checks['A1_'+name+'_reconstruction_max_abs']=float(np.max(np.abs(new-specs['A1'][name])))
    for name,n in [('L1',256),('L2',4096)]:
        beta=rng([20261003,11]).normal(0,2.5,8);rr=rng([20261003,12,n]);x=rr.normal(size=(n,8));x[:,0]=1
        x[:,1:]=(x[:,1:]-x[:,1:].mean(0))/x[:,1:].std(0)
        y=rr.binomial(1,expit(np.einsum('ij,j->i',x,beta)))
        for field,new in [('X',x),('y',y),('generator_beta',beta)]:
            checks[name+'_'+field+'_reconstruction_max_abs']=float(np.max(np.abs(new-specs[name][field])))
    if max(checks.values())>1e-11:raise ValueError('Target reconstruction differs')
    data_name='posterior_database/data/data/wells_data.json.zip'
    if file_hash(formal/'external'/data_name)!=p['external_files'][data_name]:raise ValueError('Wells source changed')
    with zipfile.ZipFile(formal/'external'/data_name) as z:wells=json.loads(z.read('wells_data.json'))
    targets=[]
    for name in ORDER:
        t=next(t for t in p['targets'] if t['name']==name);g=t['geometry'];factor=np.asarray(g['factor']);center=np.asarray(g['center'])
        spec=specs.get(name)
        if spec is not None and fingerprint(spec)!=t['base_target_id']:raise ValueError('Target identity differs: '+name)
        record=dict(name=name,dimension=t['dimension'],base_target_id=t['base_target_id'],
            h_MALA=t['step_mala'],s_RWM=t['step_rwm'],geometry=g,
            same_fixed_geometry_for_RWM_MALA_NUTS_and_CPU_CUDA=True,
            base_spec_in_frozen_source=SOURCE_NAMES[0]+'#/models/'+name,
            development_setup_file_sha256=t['development_setup_file_sha256'])
        if name in ('G1','G2','A1'):
            L=factor;C=np.asarray(spec['covariance']);whitened=np.linalg.solve(L,np.linalg.solve(L,C).T).T
            record['sampling_covariance_identity_max_abs']=float(np.max(np.abs(whitened-np.eye(t['dimension']))))
            record['sampling_mean_max_abs']=float(np.max(np.abs(np.linalg.solve(L,np.asarray(spec['mean'])-center))))
        if name in ('L1','L2'):
            X=np.asarray(spec['X']);prob=expit(np.einsum('ij,j->i',X,center,optimize=False));H=np.einsum('ni,nj,n->ij',X,X,prob*(1-prob))+np.eye(t['dimension'])/spec['prior_scale']**2
            record['mode_information_whitening_max_abs']=float(np.max(np.abs(np.einsum('ia,ij,jb->ab',factor,H,factor,optimize=False)-np.eye(t['dimension']))))
            record['observations']=len(spec['y']);record['prior_sd']=spec['prior_scale'];record['generator_beta']=spec['generator_beta']
        if name=='M1':record['mode_displacement']=spec['separation'];record['sampling_equals_original']=np.array_equal(center,np.zeros(8)) and np.array_equal(factor,np.eye(8))
        if name=='W1':
            record['observations']=wells['N'];record['flat_prior']=True
            X=np.column_stack((np.ones(wells['N']),np.asarray(wells['dist'])/100.))
            prob=expit(np.einsum('ij,j->i',X,center,optimize=False))
            H=np.einsum('ni,nj,n->ij',X,X,prob*(1-prob),optimize=False)
            record['mode_information_whitening_max_abs']=float(np.max(np.abs(np.einsum('ia,ij,jb->ab',factor,H,factor,optimize=False)-np.eye(2))))
        targets.append(record)
    # Check every original initialization against its frozen stream, not just a seed label.
    init_checks=[]
    for name,r in sorted(p['inputs'].items()):
        path=formal/'inputs'/name
        if file_hash(path)!=r['sha256']:raise ValueError('Actual input changed: '+name)
        with zipfile.ZipFile(path) as z:actual=np.load(io.BytesIO(z.read('initial.npy')),allow_pickle=False)
        initial=[];model_code=ORDER.index(r['model'])+1
        words=np.frombuffer(hashlib.sha256(p['identity'].encode()).digest(),dtype='<u4')
        for chain in range(4):
            address=(20261005,1,*map(int,words),model_code,r['replicate'],1,chain)
            arr=2*np.random.Generator(np.random.Philox(np.random.SeedSequence(address))).standard_normal(r['dimension'])
            if r['model']=='M1':arr[0]=-5. if chain%2==0 else 5.
            initial.append(arr)
        if not np.array_equal(actual,initial):raise ValueError('Initial values differ: '+name)
        init_checks.append(dict(input=name,sha256=r['sha256'],initial_array_sha256=digest(actual.astype('<f8').tobytes()),exact_match=True))
    # Observe actual task environments; no task is rerun and missing files remain visible.
    observed=[]
    for f in sorted((formal/'formal-runs').glob('batch-*/main/tasks/*/attempt-0001/environment.json')):
        e=json.loads(f.read_text());observed.append({k:e.get(k) for k in ['device','dtype','torch_threads','interop_threads','thread_environment']})
    variants=[]
    for e in observed:
        if e not in variants:variants.append(e)
    result=dict(schema='manuscript-configuration-review-v1',protocol_sha256=EXPECTED,
        protocol_file_sha256=file_hash(formal/'protocol.json'),source_commit=p['source_commit'],generator_sha256=file_hash(Path(__file__)),
        source_files=sources,target_definition_checks=checks,targets=targets,
        input_initial_checks=init_checks,actual_input_count=len(init_checks),
        controls=p['controls'],windows_limits=p['windows_limits'],minimum_available_ram_bytes=p['minimum_available_ram_bytes'],
        observed_main_environments=len(observed),observed_environment_variants=variants,
        initial_rule='q0 ~ N(0,4I); M1 first coordinate fixed [-5,5,-5,5]; all kernels share saved starts; NUTS has distinct streams and adaptive warmup',
        coordinate_rule='base coordinate r = c + L q; original theta = base.constrain(r); H2 additionally x = z exp(v/2)',
        interpretation='G2 and A1 are exactly whitened Gaussian targets in real arithmetic. Their raw correlation is not retained in the sampled geometry. Finite precision and dense evaluation cost remain.',
        new_sampler_calls=0,new_tuning_calls=0,protocol_changed=False)
    output.mkdir(parents=True,exist_ok=True);write(output/'configuration-evidence.json',result)
    text=r'''% Generated by scripts/analysis/revision_configuration_tables.py; no sampling.
\section{紧凑研究的最终目标与配置}
\label{sec:compact-final-config}
本节直接读取正式紧凑协议及其冻结目标目录，未使用历史CPU配置替代本轮定义。全部核和两设备共用每目标的固定仿射坐标。记基础模型坐标为$r=c+Lq$，其中$q$是实际采样坐标；原参数为$\theta=T_0(r)$。除H2外$T_0$为恒等映射，H2再将非中心化变量转换为漏斗原尺度。变换后的密度含$\log|\det L|$。

\begin{table}[htbp]\centering\small
\begin{tabular}{lrrrl}\toprule
目标 & 维数 & MALA $h$ & RWM $s$ & 固定仿射坐标\\\midrule
'''
    labels={'G1':'$c=0,L=I$','G2':r'$c=0,L=\operatorname{chol}(\Sigma)$','A1':r'$c=m,L=\operatorname{chol}(\Sigma)$',
            'L1':'众数及观测信息','L2':'众数及观测信息','H1':'$c=0,L=I$','H2':'$c=0,L=I$','M1':'$c=0,L=I$','W1':'众数及观测信息'}
    for t in targets:text+=f"{t['name']} & {t['dimension']} & {t['h_MALA']:.9g} & {t['s_RWM']:.9g} & {labels[t['name']]}\\\\\n"
    text+=r'''\bottomrule\end{tabular}
\caption{正式紧凑研究采用的最终配置。$h$遵循正文噪声$\sqrt{2h}$的MALA约定；$s$是RWM提议标准差。表内数字为显示精度，完整浮点数、中心和矩阵保存在随附配置JSON及原协议中。}
\label{tab:compact-final-steps}\end{table}

\paragraph{高斯与AR(1)目标。}
G1为$N_8(0,I)$。G2为$N_{64}(0,U\Lambda U^\top)$，$\Lambda_{jj}=100^{(j-1)/63}$；$U$由固定$64\times64$标准正态矩阵的QR分解取得。原始协方差条件数100，但完整Cholesky变换使采样坐标为$N_{64}(0,I)$。A1的生成模型为$x_1\sim N(0,1)$、$x_t=0.9x_{t-1}+\sqrt{1-0.9^2}\epsilon_t$、$y_t=x_t+\eta_t$，$t=1,\ldots,64$，噪声相互独立且为标准正态。记$K_{ij}=0.9^{|i-j|}$，固定数据后的后验为$N(m,\Sigma)$，$\Sigma=(K^{-1}+I)^{-1}$、$m=\Sigma y$。A1也使用完整Cholesky变换，因而采样坐标同为标准正态。G2/A1的原尺度相关结构不能直接作为本轮核差异的原因；维数、各核移动效率、稠密目标计算及有限精度仍影响被测工作流。

\paragraph{回归目标。}
L1/L2均为8参数logistic回归，样本数分别为256/4096，先验$\beta_j\overset{\mathrm{iid}}\sim N(0,2.5^2)$。设计矩阵第一列为1，其余七列从标准正态生成后按每列样本均值和总体式标准差（分母$n$）标准化。生成系数来自$N_8(0,2.5^2I)$且两模型共用，观测独立来自$\operatorname{Bernoulli}(\sigma(X_i\beta))$。W1采用3020条真实水井记录，$\Pr(y_i=1)=\sigma(\alpha+\beta d_i/100)$，先验在$(\alpha,\beta)$上平坦。L1/L2/W1以零点开始的trust-exact优化求众数$c$，接受条件为目标有限及解析梯度最大绝对值不超过$10^{-7}$；$L=\operatorname{chol}(H(c)^{-1})$。L1/L2的$H=X^\top\operatorname{diag}\{p_i(1-p_i)\}X+I/2.5^2$，W1不加先验项。优化最多300步，未做特征值修复，未使用参考后验样本；这只是固定坐标选择，不将Laplace近似当作参考真值。

\paragraph{漏斗与双峰目标。}
H1为$v\sim N(0,3^2)$，$x_i\mid v\sim N(0,e^v)$，$i=1,\ldots,8$。H2采样$v\sim N(0,3^2),z_i\sim N(0,1)$并输出$x_i=z_i e^{v/2}$。二者基础坐标不同，原参数后验对应。M1为$\tfrac12N_8(-5e_1,I)+\tfrac12N_8(5e_1,I)$，即$\delta=5$，未额外平移或旋转，因此本例$q=\theta$数值相同，正文仍统一用$\theta$表示原参数。

\paragraph{固定数据的生成与定位。}
合成目标使用NumPy默认生成器和\texttt{SeedSequence}。G2、A1和logistic生成系数分别从地址$[20261003,11]$开始；G2先生成旋转矩阵，A1先生成潜状态创新再生成观测噪声。L1/L2的设计及二元观测分别使用地址$[20261003,12,n]$。相同地址在不同模型内重新开始，并不表示G2与A1共用同一目标数组。归档的模型数据和协方差是执行依据，完整再生成核对最大绝对差小于$10^{-11}$。无需依赖本机目录即可在正式证据包的\texttt{source/benchmark/protocols/windows-native-v1.json}及\texttt{catalog.json}定位完整定义；配置JSON还给出来源SHA及完整$c,L$。

\paragraph{开发选择、初值与核控制。}
坐标构造规则预先固定，随后在独立开发输入上分别选择MH步长，而非从正式结果重新调参。RWM候选为$\{0.5,1,1.5,2.4,3.5,5\}/\sqrt d$，MALA候选为$\{0.1,0.3,0.6,1,1.6,2.4\}/d^{1/3}$；每候选两份四链输入，丢弃512步后保留1024步，以两次均有效时的平均ESJD/d最大者入选，平局取较小步长。正式四链共用原件中的$q_0\sim N(0,4I)$，M1首坐标替换为$(-5,5,-5,5)$。MH和NUTS读取同一初值，原尺度初值为$T_0(c+Lq_0)$；NUTS另用独立随机流和适应预热，并非与MH共享路径。216份实际初值逐数组核对通过。

正式保留预算为1024/4096步；MH先丢弃512步，窗口32，quasi-DEER每窗口最多2048轮，Picard最多$N+512$轮。CPU Pyro NUTS采用四个spawn子进程，每进程一链、一条torch计算线程和一条interop线程；每链预热1024步、目标接受率0.8、最大树深8，适应步长及对角质量矩阵（\texttt{full\_mass=False}），未使用JIT。各链适应后的参数保存在输出中，而非用表内MH步长替代。

\paragraph{资源与失败规则。}
主MH工作进程设置torch计算线程4、interop线程1，CUDA任务也保留这部分主机执行。3888份主进程环境记录均为上述设置，浮点数为float64；OMP/MKL/OpenBLAS/VECLIB线程环境变量未设置，因此不将torch设置解释为所有库的统一线程硬上限。线程数也不等于独占物理核心预算。每任务存储/工作区估计上限2048 MiB，进程树RSS监督上限8 GiB，原生Windows Job提交内存上限12 GiB；它们是不同计量规则，2048 MiB不是通用分配器硬上限。任务启动保留可用主存至少12 GiB及磁盘至少4 GiB，CUDA工作进程另检查GPU空闲至少3 GiB，运行磁盘底线1 GiB。边界资源不足则暂停启动，不把未运行任务标为数值失败；进程异常、非有限值、迭代耗尽和路径标准失配均保留。没有总实验时限、数值失败重试或顺序回退来改变样本资格。12 GiB限制本身不证明所见进程失败均由内存耗尽导致。

\paragraph{版本依据。}
以上读取的是\texttt{windows-compact-inference-v1}，冻结执行源\texttt{3a37a89}，协议摘要前缀\texttt{91bbff0ec47f}。冻结文件和依赖版本保持不变；本次仅导出配置、核对既有输入，新增采样和调参均为零。
'''
    tex.parent.mkdir(parents=True,exist_ok=True);tex.write_text(text)
    write(output/'configuration-summary.json',dict(protocol_sha256=EXPECTED,targets=len(targets),actual_initial_arrays_verified=len(init_checks),
        generated_tex_sha256=file_hash(tex),evidence_sha256=file_hash(output/'configuration-evidence.json'),
        max_target_reconstruction_error=max(checks.values()),gaussian_whitening_errors={t['name']:t['sampling_covariance_identity_max_abs'] for t in targets if 'sampling_covariance_identity_max_abs' in t},
        review_findings=['Final configuration table requested by reviewer is needed.',
            'G2 and A1 are fully whitened: do not describe their final sampling coordinates as correlated.',
            'M1 plot reads original draws, but its identity affine map means q1 and theta1 are numerically identical.',
            'Both MH and NUTS share actual dispersed starts; their random mechanisms and warmup differ.'],new_sampler_calls=0))
    print(json.dumps({'targets':len(targets),'verified_initial_arrays':len(init_checks),'max_definition_difference':max(checks.values()),'new_sampler_calls':0}))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('formal','output','tex'):parser.add_argument('--'+key,type=Path,required=True)
    export(**vars(parser.parse_args()))
