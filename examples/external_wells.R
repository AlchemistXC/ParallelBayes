# Native R batch example. Uses the existing public Python Model extension route.
# Arguments: REPO SOURCE NEW_OUTPUT PYTHON ACTUAL_TAPE
args <- commandArgs(trailingOnly=TRUE)
if (length(args) != 5L) stop('Usage: Rscript external_wells.R REPO SOURCE NEW_OUTPUT PYTHON ACTUAL_TAPE')
repo <- normalizePath(args[[1]], mustWork=TRUE)
source <- normalizePath(args[[2]], mustWork=TRUE)
output <- args[[3]]
if (file.exists(output)) stop('Use a new R integration output directory')
Sys.setenv(RETICULATE_PYTHON=normalizePath(args[[4]], mustWork=TRUE))
actual_tape <- normalizePath(args[[5]], mustWork=TRUE)
stopifnot(as.character(packageVersion('posterior')) == '1.7.0')
dir.create(output,recursive=TRUE)
helper <- reticulate::import_from_path('validate_wells',path=file.path(repo,'scripts/completion'),convert=TRUE)
r <- helper$run_validation(source,file.path(output,'python'),stage='torch',tape_from=actual_tape)
if (!identical(r$record$status,'passed') || is.null(r$draws)) stop('Validation failed; raw failure retained')
draws <- posterior::as_draws_array(r$draws)
dimnames(draws) <- list(iteration=seq_len(dim(draws)[1L]),chain=seq_len(dim(draws)[2L]),variable=c('alpha','beta[1]'))
stopifnot(identical(dim(draws),c(96L,4L,2L)))
writeBin(as.double(draws),file.path(output,'draws-f64le.bin'),size=8L,endian='little')
saveRDS(draws,file.path(output,'draws.rds'))
receipt <- list(status='passed',dimensions=dim(draws),class=class(draws),variables=posterior::variables(draws),
  tape_sha256=r$record$tape_sha256,versions=list(R=R.version.string,posterior=as.character(packageVersion('posterior')),
  reticulate=as.character(packageVersion('reticulate'))),session_info=capture.output(sessionInfo()),
  scope='R batch target and four-workflow integration; same frozen tape, no extra statistical replication')
jsonlite::write_json(receipt,file.path(output,'receipt.json'),auto_unbox=TRUE,pretty=TRUE,digits=NA)
cat('R batch integration passed; dimensions:',dim(draws),'\n')
