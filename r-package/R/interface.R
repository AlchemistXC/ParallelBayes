.pb_module <- function() {
  path <- system.file("python", package = "parallelbayes")
  module <- reticulate::import_from_path("parallelbayes", path = path, convert = TRUE)
  if (!identical(module$"__version__", as.character(utils::packageVersion("parallelbayes")))) {
    stop("A different ParallelBayes Python version is already loaded; restart R with the pinned environment")
  }
  module
}
.pb_json <- function(x) jsonlite::toJSON(x, auto_unbox = TRUE, digits = NA, null = "null", matrix = "rowmajor")
.pb_spec <- function(model) {
  if (!inherits(model, "pb_model")) stop("model must be a pb_model")
  reticulate::import("json", convert = FALSE)$loads(model$json)
}
.pb_native <- function(model) .pb_module()$make_model(.pb_spec(model))

pb_model <- function(kind = "gaussian", ..., stan_file = NULL, data = list()) {
  spec <- c(list(kind = kind), list(...))
  for (field in intersect(names(spec), c("mean", "y"))) {
    if (is.atomic(spec[[field]]) && is.null(dim(spec[[field]]))) spec[[field]] <- I(spec[[field]])
  }
  if (!is.null(stan_file)) {
    spec$kind <- "stan"
    spec$stan_file <- normalizePath(stan_file, mustWork = TRUE)
    spec$data <- data
  }
  structure(list(json = .pb_json(spec), kind = spec$kind), class = "pb_model")
}

pb_capabilities <- function(model) .pb_module()$capabilities(.pb_spec(model))

pb_sample <- function(model, kernel = "mala", executor = "sequential", ..., failure = c("record", "error")) {
  failure <- match.arg(failure)
  settings <- c(list(kernel = kernel, executor = executor), list(...))
  if (!is.null(settings$initial) && is.atomic(settings$initial) && is.null(dim(settings$initial))) settings$initial <- I(settings$initial)
  config <- reticulate::import("json", convert = FALSE)$loads(.pb_json(settings))
  raw <- .pb_module()$sample(.pb_native(model), config)
  draws <- if (identical(raw$status, "completed")) {
    a <- aperm(raw$draws, c(2L, 1L, 3L))
    dimnames(a) <- list(iteration = seq_len(dim(a)[1L]), chain = seq_len(dim(a)[2L]), variable = unlist(raw$names))
    posterior::as_draws_array(a)
  } else NULL
  raw$draws <- NULL
  result <- structure(list(draws = draws, record = raw, model = model), class = "pb_fit")
  if (failure == "error" && is.null(draws)) stop("Output verification failed; use failure='record' to inspect/replay")
  result
}

pb_validate <- function(model, points = NULL, reference = NULL) {
  if (!is.null(reference)) {
    if (is.null(points)) stop("Explicit common-coordinate points are required for cross-provider validation")
    .pb_module()
    stan <- reticulate::import("parallelbayes.stan")
    return(stan$cross_validate(.pb_native(model), .pb_native(reference), points))
  }
  .pb_module()$validate_model(.pb_native(model), points)
}

pb_environment <- function() {
  .pb_module()
  reticulate::import("parallelbayes.sampling")$environment()
}

pb_benchmark <- function(model, configurations, output = NULL) {
  if (!is.list(configurations) || length(configurations) == 0L) stop("configurations must be a nonempty list")
  fits <- lapply(configurations, function(config) do.call(pb_sample, c(list(model = model), config)))
  if (!is.null(output)) saveRDS(fits, output)
  fits
}

print.pb_model <- function(x, ...) { cat("ParallelBayes target:", x$kind, "\n"); invisible(x) }
print.pb_fit <- function(x, ...) {
  cat("ParallelBayes:", x$record$status, "|", x$record$guarantee, "\n")
  if (!is.null(x$draws)) print(x$draws, ...)
  invisible(x)
}
