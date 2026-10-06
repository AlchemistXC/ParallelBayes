# Read saved objects only. No model construction or sampling.
args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=2L || file.exists(args[2])) stop('Saved example root and new JSON required')
library(posterior)
fits <- readRDS(file.path(args[1],'fits.rds'))
stopifnot(length(fits)==4L)
rows <- lapply(fits,function(f) {
  stopifnot(identical(f$record$status,'completed'),identical(dim(f$draws),c(64L,4L,2L)),
    isTRUE(f$record$audit$passed),all(unlist(f$record$audit$acceptance_mismatches)==0))
  list(status=f$record$status,shape=dim(f$draws),device=f$record$diagnostics$tensor_device,
    dtype=f$record$diagnostics$tensor_dtype,tape_sha256=f$record$tape_sha256,
    audit=f$record$audit,diagnostics=posterior::summarise_draws(f$draws))
})
for(pair in list(c(1L,2L),c(3L,4L))) {
  a <- fits[[pair[1]]];b <- fits[[pair[2]]]
  stopifnot(identical(a$record$tape_sha256,b$record$tape_sha256),
    identical(a$record$accept,b$record$accept),
    isTRUE(all.equal(as.array(a$draws),as.array(b$draws),tolerance=1e-8)))
}
if(file.exists(file.path(args[1],'failed-fit.rds'))) {
  bad <- readRDS(file.path(args[1],'failed-fit.rds'))
  stopifnot(identical(bad$record$status,'failed'),is.null(bad$draws),
    length(bad$record$failed_trajectory)>0L)
}
jsonlite::write_json(list(status='passed',workflows=rows,independent_repeats_added=0L,
  sampling_calls=0L,scope='Read-only installed example object reconstruction'),
  args[2],pretty=TRUE,auto_unbox=TRUE,digits=NA,na='null')
