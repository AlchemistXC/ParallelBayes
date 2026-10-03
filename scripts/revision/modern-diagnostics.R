# Post-review diagnostics from unchanged raw posterior arrays; one result per task.
args <- commandArgs(trailingOnly=TRUE)
limit <- if(length(args)) as.integer(args[[1]]) else Inf
root <- normalizePath(getwd())
.libPaths(c(file.path(root,'environment/R-library'),.libPaths()))
if (!nzchar(Sys.getenv('RETICULATE_PYTHON'))) Sys.setenv(RETICULATE_PYTHON=file.path(root,'.venv/bin/python'))
library(posterior); library(reticulate); library(jsonlite)
py_run_string("import importlib.util, json, numpy as np\nspec=importlib.util.spec_from_file_location('pa','benchmark/analysis/analyze.py')\npa=importlib.util.module_from_spec(spec);spec.loader.exec_module(pa)\ndef diagnostic_array(path,protocol,model,discard):\n    with np.load(path) as z: q=z['draws'][:,int(discard):].copy()\n    s=json.load(open(protocol))['models'][model]\n    f=pa.functions(s,q)\n    return np.transpose(np.concatenate((q,f),axis=-1),(1,0,2))\n")
queue <- read.csv('output/cpu-revision/modern-inputs.csv',stringsAsFactors=FALSE)
out <- Sys.getenv('PB_DIAGNOSTIC_OUTPUT','output/cpu-revision/modern');dir.create(out,recursive=TRUE,showWarnings=FALSE)
manifest <- list(posterior=as.character(packageVersion('posterior')),R=as.character(getRversion()),
 scope='post-review; all constrained parameters and declared functions; unchanged retained samples',
 rhat='posterior::rhat = max rank-normalized split and folded split; undefined retained as null',
 ess='posterior::ess_bulk and ess_tail; not substituted for empirical error')
write_json(manifest,file.path(out,'manifest.json'),auto_unbox=TRUE,pretty=TRUE)
count <- 0L
for(i in seq_len(nrow(queue))) {
 row<-queue[i,];dest<-file.path(out,paste0(row$id,'.json'))
 if(file.exists(dest))next
 if(count>=limit)break
 started<-proc.time()[['elapsed']]
 x<-py$diagnostic_array(row$path,row$protocol,row$model,as.integer(row$discard))
 nf<-if(row$model %in% c('G1','G2','A1'))3L else 4L
 np<-dim(x)[3]-nf
 values<-lapply(seq_len(dim(x)[3]),function(j){
  a<-x[,,j];rh<-posterior::rhat(a);eb<-posterior::ess_bulk(a);et<-posterior::ess_tail(a)
  list(name=if(j<=np)paste0('parameter_',j) else paste0('function_',j-np),
       kind=if(j<=np)'parameter' else 'function',rhat=rh,ess_bulk=eb,ess_tail=et,
       constant_any_chain=any(apply(a,2,function(v)length(unique(v))==1L)),
       rhat_state=if(is.finite(rh))'finite' else 'undefined_or_nonfinite')
 })
 record<-list(identity=as.list(row),variables=values,diagnostic_seconds=proc.time()[['elapsed']]-started)
 tmp<-paste0(dest,'.tmp');write_json(record,tmp,auto_unbox=TRUE,pretty=FALSE,na='null',digits=NA);file.rename(tmp,dest)
 count<-count+1L
 if(i%%40L==0L||count==1L)cat(i,'/',nrow(queue),'diagnosed\n')
}
