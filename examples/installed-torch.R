# Uses an installed R package and an explicitly selected Python environment.
# Rscript --vanilla examples/installed-torch.R path/to/new-output-directory
if (!nzchar(Sys.getenv("RETICULATE_PYTHON"))) {
  stop("Set RETICULATE_PYTHON to the Python executable in your torch environment before starting R")
}
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 1L) stop("Supply one new output directory")
if (file.exists(args[1])) stop("Output already exists; choose a new directory")
dir.create(args[1], recursive = TRUE)
library(parallelbayes)
model <- pb_model("gaussian", dimension = 2L, backend = "torch")
stopifnot(pb_validate(model)$passed)
configurations <- list(
  list(kernel="mala", executor="sequential", draws=64L, chains=4L, seed=2026L),
  list(kernel="mala", executor="quasi_deer", draws=64L, chains=4L, seed=2026L, window=8L),
  list(kernel="rwm", executor="sequential", draws=64L, chains=4L, seed=2026L),
  list(kernel="rwm", executor="online_picard", draws=64L, chains=4L, seed=2026L, window=8L)
)
fits <- pb_benchmark(model, configurations, output = file.path(args[1], "fits.rds"))
stopifnot(all(vapply(fits, function(fit) identical(fit$record$status,"completed"), logical(1))))
for (pair in list(c(1L,2L), c(3L,4L))) {
  sequential <- fits[[pair[1]]]; parallel <- fits[[pair[2]]]
  stopifnot(identical(sequential$record$tape_sha256, parallel$record$tape_sha256),
            identical(sequential$record$accept, parallel$record$accept),
            isTRUE(all.equal(as.array(sequential$draws),as.array(parallel$draws),tolerance=1e-8)))
}
records <- lapply(fits, function(fit) list(
  status=fit$record$status, config=fit$record$config,
  audit=fit$record$audit, tape_sha256=fit$record$tape_sha256,
  shape=dim(fit$draws), timing=fit$record$timing,
  diagnostics=posterior::summarise_draws(fit$draws)))
jsonlite::write_json(list(environment=pb_environment("torch"),
  r_package_version=as.character(packageVersion("parallelbayes")),
  capabilities=pb_capabilities(model), workflows=records,
  scope="Installation example; 64 transitions do not establish convergence or performance"),
  file.path(args[1],"summary.json"), auto_unbox=TRUE, pretty=TRUE, digits=NA, na="null")
print(lapply(records, function(record) record$diagnostics))
cat("Four installed-package workflows passed numerical checks; diagnostics and records saved.\n")
