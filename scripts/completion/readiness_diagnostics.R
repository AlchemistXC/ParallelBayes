# Binary-only companion diagnostics; no convergence acceptance gate.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=1L) stop('Usage: Rscript readiness_diagnostics.R NEW_ANALYSIS_DIRECTORY')
root <- normalizePath(args[[1]],mustWork=TRUE)
manifest <- jsonlite::read_json(file.path(root,'transport.json'),simplifyVector=FALSE)
rows <- list()
for (fit in manifest$fits) {
  shape <- as.integer(unlist(fit$shape))
  if(length(shape)!=3L || prod(shape)>1e7) stop('Invalid binary dimensions')
  input <- file.path(root,fit$input)
  if(file.info(input)$size!=8*prod(shape)) stop('Binary length mismatch')
  values <- readBin(input,what='double',n=prod(shape),size=8,endian='little')
  if(any(!is.finite(values))) stop('Nonfinite transport input')
  output <- paste0(input,'.roundtrip')
  if(file.exists(output)) stop('Do not overwrite roundtrip evidence')
  writeBin(values,output,size=8,endian='little')
  x <- array(values,dim=shape,dimnames=list(NULL,NULL,unlist(fit$names)))
  draws <- posterior::as_draws_array(x)
  stat <- posterior::summarise_draws(draws,mean=base::mean,sd=stats::sd,
    rhat=posterior::rhat,ess_bulk=posterior::ess_bulk,ess_tail=posterior::ess_tail,
    mcse_mean=posterior::mcse_mean)
  rows[[fit$id]] <- as.data.frame(stat)
}
dest <- file.path(root,'posterior.json')
if(file.exists(dest)) stop('Do not overwrite diagnostics')
jsonlite::write_json(list(R=R.version.string,posterior=as.character(packageVersion('posterior')),
  results=rows,scope='Companion diagnostics only; one development fit per target/workflow, not independent accuracy experiments'),
  dest,pretty=TRUE,auto_unbox=TRUE,digits=NA,na='null')
print(c(fits=length(rows)))
