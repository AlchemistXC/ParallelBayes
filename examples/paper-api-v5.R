# Run from any directory after installing parallelbayes and selecting the locked
# torch Python environment through RETICULATE_PYTHON before R starts.
# Rscript --vanilla examples/paper-api-v5.R NEW_OUTPUT_DIRECTORY
if (!nzchar(Sys.getenv("RETICULATE_PYTHON"))) stop("Set RETICULATE_PYTHON before starting R")
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L || file.exists(args[1])) stop("Supply one new output directory")
dir.create(args[1], recursive = TRUE)
library(parallelbayes)
model <- pb_model("gaussian", dimension = 2L, backend = "torch")
validation <- pb_validate(model)
stopifnot(isTRUE(validation$passed))
print(pb_capabilities(model))
configs <- lapply(c("sequential", "online_picard"), function(executor)
  list(kernel = "rwm", executor = executor, device = "cpu",
       draws = 8192L, chains = 4L, step_size = 0.8, window = 16L, max_iter = 8704L,
       seed = 2026L, audit = TRUE))
fits <- pb_benchmark(model, configs, output = file.path(args[1], "fits.rds"))
statuses <- vapply(fits, function(fit) fit$record$status, "")
jsonlite::write_json(list(statuses = statuses, validation = validation),
                    file.path(args[1], "status.json"), auto_unbox = TRUE, pretty = TRUE)
stopifnot(all(statuses == "completed")) # Failed records remain in fits.rds.
stopifnot(identical(fits[[1]]$record$tape_sha256, fits[[2]]$record$tape_sha256),
          identical(fits[[1]]$record$accept, fits[[2]]$record$accept),
          isTRUE(fits[[1]]$record$audit$passed), isTRUE(fits[[2]]$record$audit$passed))
path_difference <- max(abs(as.array(fits[[1]]$draws)-as.array(fits[[2]]$draws)))
stopifnot(path_difference < 1e-8)
timing <- data.frame(executor = c("sequential", "online_picard"),
  audited_sampler_seconds = vapply(fits, function(fit) fit$record$timing$total, numeric(1)),
  independent_audit_seconds = vapply(fits, function(fit) fit$record$timing$audit, numeric(1)))
print(timing)
diagnostics <- lapply(fits, function(fit) posterior::summarise_draws(fit$draws))
print(diagnostics)
jsonlite::write_json(list(
  scope = "v5 public-API technical example: two paired Gaussian CPU calls; excluded from the frozen formal study and all speed summaries",
  package_version = as.character(packageVersion("parallelbayes")),
  package_path = find.package("parallelbayes"), r_version = R.version.string,
  posterior_version = as.character(packageVersion("posterior")),
  environment = pb_environment("torch"), validation = validation,
  capabilities = pb_capabilities(model), statuses = statuses,
  shapes = lapply(fits, function(fit) dim(fit$draws)),
  tape_sha256 = fits[[1]]$record$tape_sha256,
  acceptance_mismatches = sum(fits[[1]]$record$accept != fits[[2]]$record$accept),
  maximum_path_difference = path_difference, timing = timing,
  diagnostics = diagnostics), file.path(args[1], "summary.json"),
  auto_unbox = TRUE, pretty = TRUE, digits = NA, na = "null")
cat("Two public-API CPU workflows completed; arrays, diagnostics and records saved.\n")
