# Binary companion diagnostics. Scope and independent unit come from the caller.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=1L) stop('Usage: Rscript posterior_diagnostics.R NEW_ANALYSIS_DIRECTORY')
root <- normalizePath(args[[1]],mustWork=TRUE)
manifest <- jsonlite::read_json(file.path(root,'transport.json'),simplifyVector=FALSE)
if(is.null(manifest$scope) || is.null(manifest$independent_unit)) stop('Analysis scope is required')
rows <- list(); times <- list()
for (fit in manifest$fits) {
  if(!identical(basename(fit$input),fit$input)) stop('Transport input must be a local basename')
  if(!is.null(rows[[fit$id]])) stop('Duplicate fit identity')
  shape <- as.integer(unlist(fit$shape))
  if(length(shape)!=3L || any(shape<1L) || prod(shape)>1e7) stop('Invalid binary dimensions')
  if(length(fit$names)!=shape[[3]]) stop('Variable names differ from shape')
  input <- file.path(root,fit$input)
  if(file.info(input)$size!=8*prod(shape)) stop('Binary length mismatch')
  values <- readBin(input,what='double',n=prod(shape),size=8,endian='little')
  if(any(!is.finite(values))) stop('Nonfinite transport input')
  output <- paste0(input,'.roundtrip')
  if(file.exists(output)) stop('Do not overwrite roundtrip evidence')
  writeBin(values,output,size=8,endian='little')
  start <- proc.time()[['elapsed']]
  x <- array(values,dim=shape,dimnames=list(NULL,NULL,unlist(fit$names)))
  draws <- posterior::as_draws_array(x)
  stat <- posterior::summarise_draws(draws,mean=base::mean,sd=stats::sd,
    rhat=posterior::rhat,ess_bulk=posterior::ess_bulk,ess_tail=posterior::ess_tail,
    mcse_mean=posterior::mcse_mean)
  times[[fit$id]] <- unname(proc.time()[['elapsed']]-start)
  rows[[fit$id]] <- as.data.frame(stat)
}
dest <- file.path(root,'posterior.json')
if(file.exists(dest)) stop('Do not overwrite diagnostics')
jsonlite::write_json(list(R=R.version.string,posterior=as.character(packageVersion('posterior')),
  results=rows,diagnostic_seconds=times,scope=manifest$scope,independent_unit=manifest$independent_unit),
  dest,pretty=TRUE,auto_unbox=TRUE,digits=NA,na='null')
print(c(fits=length(rows)))
