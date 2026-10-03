Sys.setenv(RETICULATE_PYTHON=normalizePath(".venv-win-torch/Scripts/python.exe"))
.libPaths(c("D:/Tools/R-library-4.6",.libPaths()))
library(parallelbayes)
model <- pb_model("gaussian",dimension=2L,backend="torch")
stopifnot(identical(pb_environment("torch")$provider,"native_torch"))
stopifnot(length(pb_capabilities(model)$combinations)==4L)
records <- list()
for (device in c("cpu","cuda")) {
 for (pair in list(c("mala","sequential"),c("mala","quasi_deer"),c("rwm","sequential"),c("rwm","online_picard"))) {
  fit <- pb_sample(model,kernel=pair[[1]],executor=pair[[2]],device=device,draws=37L,
                   chains=2L,window=8L,step_size=.1,audit=TRUE)
  stopifnot(inherits(fit$draws,"draws_array"),identical(dim(fit$draws),c(37L,2L,2L)))
  stopifnot(identical(names(dimnames(fit$draws)),c("iteration","chain","variable")))
  expected <- aperm(fit$record$unconstrained,c(2L,1L,3L))
  stopifnot(all(as.array(fit$draws)==expected))
  records[[paste(device,pair[[1]],pair[[2]],sep="/")]] <- list(status=fit$record$status,
    shape=dim(fit$draws),audit=fit$record$audit,summary=posterior::summarise_draws(fit$draws))
 }
}
constant <- posterior::as_draws_array(array(0,c(32,4,1)))
diag <- posterior::summarise_draws(constant)
stopifnot(is.na(diag$rhat),is.na(diag$ess_bulk),is.na(diag$ess_tail))
records$constant <- list(rhat=NA,ess_bulk=NA,ess_tail=NA,state="undefined_no_variation")
jsonlite::write_json(records,"execution/windows-native/r-validation.json",auto_unbox=TRUE,pretty=TRUE,na="null",digits=NA)
cat("8 native R batches passed; iteration x chain x variable verified; constant diagnostics undefined\n")
