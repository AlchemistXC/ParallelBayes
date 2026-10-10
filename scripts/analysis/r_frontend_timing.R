# One fresh R process, one fixed workflow/mode, two technical calls.
# Run through r_frontend_timing.py; no sampling at source/parse time.
entry <- proc.time()[["elapsed"]]
clock <- function() proc.time()[["elapsed"]]
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 6L) stop("INPUTS EXAMPLE WORKFLOW AUDIT OUTPUT EXPECTED_R_PACKAGE")
inputs <- args[1L]
example <- args[2L]
workflow <- as.integer(args[3L])
audit <- identical(args[4L], "true")
output <- args[5L]
if (!dir.exists(output)) stop("Parent must create a fresh attempt directory")
script <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
helper_dir <- dirname(normalizePath(sub("^--file=", "", script)))

start <- clock()
library(parallelbayes)
if (!identical(normalizePath(find.package("parallelbayes")), normalizePath(args[6L]))) {
  stop("Selected installed R package differs from frozen package")
}
environment_record <- pb_environment("torch")
pb <- reticulate::import("parallelbayes", convert = FALSE)
module_file <- reticulate::py_to_r(pb$"__file__")
expected_module <- file.path(system.file("python", package = "parallelbayes"), "parallelbayes", "__init__.py")
if (!identical(normalizePath(module_file), normalizePath(expected_module))) stop("Wrong Python module")
torch <- reticulate::import("torch", convert = FALSE)
torch$set_num_threads(1L)
torch$set_num_interop_threads(1L)
environment_record <- pb_environment("torch")
helper <- reticulate::import_from_path("r_frontend_helper", path = helper_dir, convert = FALSE)
load_seconds <- clock() - start
start <- clock()
context <- helper$load_context(inputs, example)
target_seconds <- clock() - start
calls <- list()

for (label in c("first", "subsequent")) {
  call_start <- clock()
  start <- clock()
  result <- helper$invoke(context, workflow, audit)
  invoke_seconds <- clock() - start
  start <- clock()
  value <- reticulate::py_to_r(helper$payload(result))
  transfer_seconds <- clock() - start
  start <- clock()
  draws <- NULL
  diagnostics <- NULL
  if (identical(value$status, "completed")) {
    a <- value$draws
    dimnames(a) <- list(iteration = seq_len(dim(a)[1L]), chain = seq_len(dim(a)[2L]),
                       variable = unlist(value$names))
    draws <- posterior::as_draws_array(a)
  }
  conversion_seconds <- clock() - start
  start <- clock()
  if (!is.null(draws)) diagnostics <- posterior::summarise_draws(draws)
  diagnostic_seconds <- clock() - start
  ready_elapsed <- clock() - entry
  call_elapsed <- clock() - call_start
  # Parent clocks this notification before raw archival. It is the actual cold
  # R launch-to-results-ready latency, including the small stdout notification.
  cat("PB_R_READY ", label, " ", value$status, "\n", sep = "")
  flush(stdout())
  start <- clock()
  helper$persist(context, result, file.path(output, label))
  if (!is.null(draws)) {
    saveRDS(draws, file.path(output, paste0(label, "-draws.rds")))
    con <- file(file.path(output, paste0(label, "-R.bin")), "wb")
    writeBin(as.double(value$draws), con, size = 8L, endian = "little")
    close(con)
  }
  archive_seconds <- clock() - start
  calls[[label]] <- list(status = value$status, ready_elapsed = ready_elapsed,
    call_elapsed = call_elapsed, invoke = invoke_seconds, transfer_to_R = transfer_seconds,
    posterior_conversion = conversion_seconds, diagnostics_seconds = diagnostic_seconds,
    archive_seconds = archive_seconds, diagnostics = diagnostics)
  if (!identical(value$status, "completed")) break
}
record <- list(schema = "r-frontend-timing-v1", workflow = workflow, audit = audit,
  R = R.version.string, R_package = as.character(packageVersion("parallelbayes")),
  R_package_path = find.package("parallelbayes"), python_module = module_file,
  posterior = as.character(packageVersion("posterior")),
  reticulate = as.character(packageVersion("reticulate")), environment = environment_record,
  load_seconds = load_seconds, target_seconds = target_seconds, calls = calls,
  formal_repetitions_added = 0L)
jsonlite::write_json(record, file.path(output, "R-record.json"), auto_unbox = TRUE,
  pretty = TRUE, digits = NA, na = "null", null = "null")
