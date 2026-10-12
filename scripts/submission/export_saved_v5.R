# Read saved R objects only. Never call pb_sample(), pb_benchmark() or a backend.
library(posterior)
library(jsonlite)
args <- commandArgs(TRUE)
if (length(args) != 2L || file.exists(args[2])) stop("Supply evidence directory and new output directory")
dir.create(args[2], recursive=TRUE)
rows <- list()
for (run in c("r-example-v5-run2", "r-example-v5-final")) {
  fits <- readRDS(file.path(args[1], run, "fits.rds"))
  for (i in seq_along(fits)) {
    fit <- fits[[i]]; record <- fit$record
    label <- paste0(run, "-", i)
    row <- list(id=label, status=record$status, config=record$config,
                spec=fromJSON(fit$model$json), target_id=record$target_id,
                tape_sha256=record$tape_sha256, stopping_reason=record$stopping_reason,
                original_audit=record$audit)
    if (record$status != "completed") {
      stopifnot(is.null(fit$draws))
      row$ordinary_samples <- FALSE
      row$iterations <- record$diagnostics$iterations
      row$confirmed <- record$diagnostics$confirmed
    } else {
      row$ordinary_samples <- TRUE
      q <- record$unconstrained; accept <- record$accept
      stopifnot(identical(dim(q), c(4L,8192L,2L)), identical(dim(accept),c(4L,8192L)))
      stopifnot(max(abs(q-aperm(as.array(fit$draws),c(2L,1L,3L)))) == 0)
      writeBin(as.double(q),file.path(args[2],paste0(label,".f64")),size=8,endian="little")
      writeBin(as.raw(as.vector(accept)),file.path(args[2],paste0(label,".u8")))
      row$shape <- dim(q)
      row$diagnostics <- summarise_draws(fit$draws,mean,sd,rhat,ess_bulk,ess_tail)
    }
    rows[[length(rows)+1L]] <- row
  }
}
stopifnot(length(rows)==4L, sum(vapply(rows,function(x)x$status=="completed",FALSE))==3L)
write_json(list(scope="Saved-object diagnostic and binary export, no new sampler calls",
                R=R.version.string,posterior=as.character(packageVersion("posterior")),
                new_sampler_calls=0,records=rows),file.path(args[2],"EXPORT.json"),
           auto_unbox=TRUE,pretty=TRUE,digits=NA,na="null",null="null")
cat("Three historical completed fits exported; one failed fit remains excluded. New sampling calls 0.\n")
