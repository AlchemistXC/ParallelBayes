# Short CUDA installed-R validation, separate from all frozen research batches.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=1L || file.exists(args[1])) stop('One new output directory required')
dir.create(args[1],recursive=TRUE);library(parallelbayes)
model <- pb_model('gaussian',dimension=2L,backend='torch')
configs <- list(
  list(kernel='mala',executor='sequential',draws=64L,chains=4L,seed=2026L,device='cuda'),
  list(kernel='mala',executor='quasi_deer',draws=64L,chains=4L,seed=2026L,device='cuda',window=8L),
  list(kernel='rwm',executor='sequential',draws=64L,chains=4L,seed=2026L,device='cuda'),
  list(kernel='rwm',executor='online_picard',draws=64L,chains=4L,seed=2026L,device='cuda',window=8L))
fits <- pb_benchmark(model,configs,output=file.path(args[1],'fits.rds'))
for(fit in fits) {
  stopifnot(identical(fit$record$status,'completed'),identical(dim(fit$draws),c(64L,4L,2L)),
    isTRUE(fit$record$audit$passed),all(unlist(fit$record$audit$acceptance_mismatches)==0),
    startsWith(fit$record$diagnostics$tensor_device,'cuda'),identical(fit$record$diagnostics$tensor_dtype,'torch.float64'))
}
for(pair in list(c(1L,2L),c(3L,4L))) {
  s <- fits[[pair[1]]];p <- fits[[pair[2]]]
  stopifnot(identical(s$record$tape_sha256,p$record$tape_sha256),identical(s$record$accept,p$record$accept),
    isTRUE(all.equal(as.array(s$draws),as.array(p$draws),tolerance=1e-8)))
}
bad <- pb_sample(pb_model('gaussian',dimension=3L,backend='torch'),device='cuda',
  executor='quasi_deer',draws=31L,window=8L,max_iter=1L,step_size=.7)
stopifnot(identical(bad$record$status,'failed'),is.null(bad$draws),length(bad$record$failed_trajectory)>0L)
saveRDS(bad,file.path(args[1],'failed-fit.rds'))
module <- getFromNamespace('.pb_module','parallelbayes')()
path <- normalizePath(module$'__file__',winslash='/',mustWork=TRUE)
stopifnot(startsWith(path,paste0(normalizePath(system.file('python',package='parallelbayes'),winslash='/'),'/')))
records <- lapply(fits,function(f) list(config=f$record$config,status=f$record$status,audit=f$record$audit,
  shape=dim(f$draws),tape_sha256=f$record$tape_sha256,device=f$record$diagnostics$tensor_device,
  dtype=f$record$diagnostics$tensor_dtype,timing=f$record$timing,diagnostics=posterior::summarise_draws(f$draws)))
jsonlite::write_json(list(Python_module=path,R_package=find.package('parallelbayes'),environment=pb_environment('torch'),
  workflows=records,failure_isolated=TRUE,scope='Installed R CUDA interface, not convergence/performance evidence'),
  file.path(args[1],'summary.json'),auto_unbox=TRUE,pretty=TRUE,digits=NA,na='null')
