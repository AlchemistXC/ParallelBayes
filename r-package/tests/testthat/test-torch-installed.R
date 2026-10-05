test_that("installed torch provider supports four MH workflows without JAX", {
  skip_if(Sys.getenv("PB_RUN_TORCH_INTEGRATION") != "1", "Set PB_RUN_TORCH_INTEGRATION=1 with torch Python")
  model <- pb_model("gaussian", dimension = 2L, backend = "torch")
  expect_identical(pb_environment("torch")$provider, "native_torch")
  expect_false(pb_capabilities(model)$nuts)
  expect_true(pb_validate(model)$passed)
  fits <- list()
  for (pair in list(c("mala", "sequential"), c("mala", "quasi_deer"),
                    c("rwm", "sequential"), c("rwm", "online_picard"))) {
    fit <- pb_sample(model, kernel = pair[1], executor = pair[2], device = "cpu",
                     draws = 19L, chains = 2L, window = 8L, seed = 88L, audit = TRUE)
    expect_identical(fit$record$status, "completed")
    expect_s3_class(fit$draws, "draws_array")
    expect_identical(dim(fit$draws), c(19L, 2L, 2L))
    expect_identical(names(dimnames(fit$draws)), c("iteration", "chain", "variable"))
    expect_true(fit$record$audit$passed)
    expect_true(all(unlist(fit$record$audit$acceptance_mismatches) == 0L))
    expect_equal(unname(as.array(fit$draws)), unname(aperm(fit$record$unconstrained, c(2L,1L,3L))), tolerance = 0)
    fits[[paste(pair, collapse = "/")]] <- fit
  }
  for (pair in list(c("mala/sequential", "mala/quasi_deer"), c("rwm/sequential", "rwm/online_picard"))) {
    sequential <- fits[[pair[1]]]
    parallel <- fits[[pair[2]]]
    expect_identical(parallel$record$tape_sha256, sequential$record$tape_sha256)
    expect_identical(parallel$record$accept, sequential$record$accept)
    expect_equal(parallel$draws, sequential$draws, tolerance = 1e-8)
  }
  expect_error(pb_sample(model, kernel = "nuts"), "unsupported torch kernel/executor")
  expect_error(pb_model(stan_file = "missing.stan", backend = "torch"), "does not translate Stan")
})

test_that("torch failed trajectories remain inspectable and outside posterior samples", {
  skip_if(Sys.getenv("PB_RUN_TORCH_INTEGRATION") != "1", "Set PB_RUN_TORCH_INTEGRATION=1 with torch Python")
  model <- pb_model("gaussian", dimension = 3L, backend = "torch")
  failed <- pb_sample(model, executor = "quasi_deer", draws = 31L, window = 8L,
                      max_iter = 1L, step_size = .7)
  expect_identical(failed$record$status, "failed")
  expect_null(failed$draws)
  expect_true(length(failed$record$failed_trajectory) > 0L)
  expect_error(pb_sample(model, executor = "quasi_deer", draws = 31L, window = 8L,
                         max_iter = 1L, step_size = .7, failure = "error"), "Output verification failed")
  overflow <- pb_model("lognormal", mu = 1000, sigma = 1, backend = "torch")
  fit <- pb_sample(overflow, draws = 2L, initial = c(1000), audit = TRUE)
  expect_identical(fit$record$status, "failed")
  expect_null(fit$draws)
  expect_match(fit$record$audit$error, "overflow")
  unchecked <- pb_sample(overflow, draws = 2L, initial = c(1000), audit = FALSE)
  expect_identical(unchecked$record$status, "failed")
  expect_null(unchecked$draws)
  expect_match(unchecked$record$transform_error, "overflow")
})

test_that("torch singleton vectors and undefined constant diagnostics are preserved", {
  skip_if(Sys.getenv("PB_RUN_TORCH_INTEGRATION") != "1", "Set PB_RUN_TORCH_INTEGRATION=1 with torch Python")
  model <- pb_model("normal_mean", y = c(1), backend = "torch")
  fit <- pb_sample(model, draws = 8L, initial = c(0))
  expect_identical(dim(fit$draws), c(8L, 1L, 1L))
  expect_identical(fit$record$status, "completed")
  constant <- posterior::summarise_draws(posterior::as_draws_array(array(0, c(32,4,1))))
  expect_true(is.na(constant$rhat))
  expect_true(is.na(constant$ess_bulk))
  expect_true(is.na(constant$ess_tail))
})
