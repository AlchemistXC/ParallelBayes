# Run from the project root after installation. Uses the public Python Model
# extension route; pb_model currently registers only built-in kinds/Stan files.
.libPaths(c(file.path(getwd(),'environment/R-library'),.libPaths()))
Sys.setenv(RETICULATE_PYTHON=file.path(normalizePath(getwd()),'.venv','bin','python'))
helper <- reticulate::import_from_path('custom-poisson-target',path='examples',convert=TRUE)
r <- helper$run_example('execution/custom-target-R-example.json')
draws <- posterior::as_draws_array(r$draws)
stopifnot(identical(dim(draws),c(128L,2L,2L)))
print(r$record)
