# R -> bundled Python -> BridgeStan C++ -> posterior, with an independent target.
project <- normalizePath(Sys.getenv('PB_PROJECT_ROOT', unset = getwd()))
Sys.setenv(RETICULATE_PYTHON = file.path(project, '.venv/bin/python'),
           BRIDGESTAN = file.path(project, 'environment/bridgestan-2.7.0'))
.libPaths(c(Sys.getenv('PB_TEST_R_LIBRARY', unset = file.path(project, 'environment/R-library')),
            file.path(project, 'environment/R-library'), .libPaths()))
library(parallelbayes)
stan <- pb_model(stan_file = file.path(project, 'models/stan/lognormal.stan'),
                 data = list(mu = 0.4, sigma = 1.3))
native <- pb_model('lognormal', mu = 0.4, sigma = 1.3)
check <- pb_validate(stan, reference = native, points = matrix(c(-12, -2, 0, 2, 5), ncol = 1))
stopifnot(isTRUE(check$passed))
a <- pb_sample(stan, kernel = 'mala', draws = 32L, initial = c(0), step_size = 0.005, seed = 128L)
b <- pb_sample(native, kernel = 'mala', draws = 32L, initial = c(0), step_size = 0.005, seed = 128L)
stopifnot(identical(a$record$status, 'completed'), identical(b$record$status, 'completed'))
difference <- max(abs(as.array(a$draws) - as.array(b$draws)))
stopifnot(difference < 1e-8)
result <- list(target_validation = check, max_sample_difference = difference,
                package_version = as.character(packageVersion('parallelbayes')), status = 'passed')
jsonlite::write_json(result, file.path(project, 'execution/logs/r-stan-end-to-end.json'), auto_unbox = TRUE, pretty = TRUE)
print(result)
