project <- normalizePath(getwd())
lib <- file.path(project, "environment", "R-library")
dir.create(lib, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(lib, .libPaths()))
Sys.setenv(RENV_PATHS_ROOT = file.path(project, "environment", "renv"), RENV_CONFIG_CONSENT = "TRUE")
if (!requireNamespace("renv", quietly = TRUE)) install.packages("renv", repos = "https://cloud.r-project.org", lib = lib)
lock <- file.path(project, "environment", "locks", "renv.lock")
if (file.exists(lock)) {
  renv::restore(lockfile = lock, library = lib, prompt = FALSE)
} else {
  required <- c("reticulate", "posterior", "jsonlite", "testthat")
  missing <- required[!vapply(required, requireNamespace, logical(1), quietly = TRUE)]
  if (length(missing)) install.packages(missing, repos = "https://cloud.r-project.org", lib = lib)
}
args <- c("CMD", "INSTALL", paste0("--library=",shQuote(lib)), "r-package")
status <- system2(file.path(R.home("bin"), "R"), args)
quit(status = status)
