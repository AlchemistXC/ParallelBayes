# Run from the project root after Rscript --vanilla scripts/install-r.R.
Sys.setenv(RETICULATE_PYTHON = file.path(normalizePath(getwd()), '.venv', 'bin', 'python'))
.libPaths(c(normalizePath('environment/R-library'), .libPaths()))
library(parallelbayes)
model <- pb_model('gaussian', dimension = 2L)
stopifnot(pb_validate(model)$passed)
print(pb_capabilities(model))
fit <- pb_sample(model, executor = 'quasi_deer', draws = 128L, chains = 2L,
                 window = 16L, seed = 2026L, audit = TRUE)
stopifnot(identical(fit$record$status, 'completed'))
print(fit$record$audit)
print(posterior::summarise_draws(fit$draws))
# This is an interface example. 128 transitions do not establish convergence.
saveRDS(fit, 'execution/quickstart-fit.rds')
