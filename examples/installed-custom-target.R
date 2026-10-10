# External Model via the installed R package's embedded Python module.
# Set R_LIBS_USER and RETICULATE_PYTHON before starting R.
# Rscript --vanilla installed-custom-target.R torch INPUTS NEW_OUTPUT [cpu|cuda]
args <- commandArgs(trailingOnly = TRUE)
if (length(args) < 3L || length(args) > 4L) stop("Supply BACKEND INPUTS NEW_OUTPUT [DEVICE]")
backend <- match.arg(args[1], c("torch", "jax"))
device <- if (length(args) == 4L) args[4] else "cpu"
if (!nzchar(Sys.getenv("RETICULATE_PYTHON"))) stop("Set RETICULATE_PYTHON before starting R")
if (file.exists(args[3])) stop("Output already exists; use a new directory")
script <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
if (length(script) != 1L) stop("Run this file with Rscript")
example_dir <- dirname(normalizePath(sub("^--file=", "", script), mustWork = TRUE))
library(parallelbayes)
environment_record <- pb_environment(backend) # Loads the installed R module first.
pb <- reticulate::import("parallelbayes", convert = TRUE)
expected <- normalizePath(file.path(system.file("python", package="parallelbayes"),
                                    "parallelbayes", "__init__.py"), mustWork = TRUE)
actual <- normalizePath(pb$"__file__", mustWork = TRUE)
if (!identical(actual, expected)) stop("Python is not loaded from the selected installed R package")
helper <- reticulate::import_from_path("installed_custom_target", path=example_dir, convert=TRUE)
result <- helper$run_example(normalizePath(args[2], mustWork=TRUE), args[3], backend, device)
print(vapply(result$workflows, function(w) w$status, ""))
diagnostics <- list()
for (workflow in result$workflows) {
  label <- paste0("workflow-", workflow$index)
  if (!identical(workflow$status, "completed")) {
    diagnostics[[label]] <- list(status=workflow$status, posterior_eligible=FALSE)
    next
  }
  a <- workflow$draws
  dimnames(a) <- list(iteration=seq_len(dim(a)[1]), chain=seq_len(dim(a)[2]),
                     variable=unlist(workflow$names))
  draws <- posterior::as_draws_array(a)
  saveRDS(draws, file.path(args[3], paste0(label, "-draws.rds")))
  con <- file(file.path(args[3], paste0(label, "-R.bin")), "wb")
  writeBin(as.double(a), con, size=8L, endian="little")
  close(con)
  diagnostics[[label]] <- list(status="completed", posterior_eligible=TRUE,
    shape=dim(a), variable=unlist(workflow$names),
    diagnostics=posterior::summarise_draws(draws))
}
jsonlite::write_json(list(scope=result$summary$scope, all_passed=result$summary$all_passed,
  r=R.version.string, posterior=as.character(packageVersion("posterior")),
  parallelbayes=as.character(packageVersion("parallelbayes")),
  installed_r_path=find.package("parallelbayes"), embedded_python_file=actual,
  environment=environment_record, workflows=diagnostics), file.path(args[3], "R-summary.json"),
  auto_unbox=TRUE, pretty=TRUE, digits=NA, na="null")
print(diagnostics)
if (!isTRUE(result$summary$all_passed)) stop("Numerical check failed; records kept, invalid paths excluded")
cat("Custom model: four numerical workflows checked; finite short runs do not establish convergence.\n")
