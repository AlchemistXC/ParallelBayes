# Reproducible user example; run from the project root in the locked environment.
Sys.setenv(RETICULATE_PYTHON = file.path(normalizePath(getwd()), '.venv', 'bin', 'python'))
.libPaths(c(normalizePath('environment/R-library'), .libPaths()))
library(parallelbayes)
set.seed(29017)
X <- cbind(1, rnorm(64))
y <- rbinom(nrow(X), 1, plogis(X %*% c(-0.3, 0.7)))
dat <- list(N = nrow(X), D = ncol(X), X = X, y = y, prior_scale = 2.5)
stan <- pb_model(stan_file = 'models/stan/logistic.stan', data = dat)
jax <- pb_model('logistic', X = X, y = y, prior_scale = 2.5)
validation <- pb_validate(stan, rbind(c(0, 0), c(-2, 1), c(3, -4)), reference = jax)
stopifnot(validation$passed)
configs <- list(
  list(kernel = 'mala', executor = 'sequential', draws = 256L,
       chains = 2L, step_size = 0.01, seed = 8102L, audit = TRUE),
  list(kernel = 'mala', executor = 'quasi_deer', draws = 256L,
       chains = 2L, step_size = 0.01, seed = 8102L, window = 32L, audit = TRUE)
)
fits <- pb_benchmark(jax, configs)
stopifnot(all(vapply(fits, function(fit) identical(fit$record$status, 'completed'), logical(1))))
path_difference <- max(abs(as.array(fits[[1]]$draws) - as.array(fits[[2]]$draws)))
stopifnot(path_difference < 1e-7)
print(validation)
print(data.frame(executor = c('sequential', 'quasi_deer'),
                 sampler_api_seconds = vapply(fits, function(fit) fit$record$timing$total, numeric(1))))
print(path_difference)
saveRDS(list(validation = validation, fits = fits, path_difference = path_difference),
        'execution/logistic-paired-example.rds')
# This short example verifies the interface and common-input execution.
# Formal accuracy and performance comparisons use the frozen protocol CLI.
