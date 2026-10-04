# Post hoc illustration on the retained R draws object; no new acceptance gate.
args <- commandArgs(trailingOnly=TRUE)
if (length(args)!=2L) stop('Usage: Rscript diagnose_wells_example.R DRAWS_RDS NEW_OUTPUT_JSON')
if (file.exists(args[[2]])) stop('Preserve previous diagnostics; choose a new output')
draws <- readRDS(args[[1]])
if (!inherits(draws,'draws_array')) stop('Expected the saved posterior draws_array')
summary <- posterior::summarise_draws(draws,mean=base::mean,sd=stats::sd,
  rhat=posterior::rhat,ess_bulk=posterior::ess_bulk,ess_tail=posterior::ess_tail,
  mcse_mean=posterior::mcse_mean)
result <- list(scope='Post hoc diagnostics of the R Picard extension example; 96 iterations, no discarded warmup; no convergence or accuracy claim',
  posterior_version=as.character(packageVersion('posterior')),dimensions=dim(draws),summary=as.data.frame(summary))
jsonlite::write_json(result,args[[2]],auto_unbox=TRUE,pretty=TRUE,digits=NA,na='null')
print(summary)
