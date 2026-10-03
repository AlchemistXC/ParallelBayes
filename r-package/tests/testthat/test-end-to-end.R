test_that("installed R interface runs Python and preserves posterior array order", {
  skip_if(Sys.getenv("PB_RUN_INTEGRATION") != "1", "Set PB_RUN_INTEGRATION=1 with pinned Python")
  model <- pb_model("gaussian", dimension = 2L)
  expect_true(pb_validate(model)$passed)
  sequential <- pb_sample(model, draws = 32L, chains = 2L, seed = 88L, audit = TRUE)
  parallel <- pb_sample(model, executor = "quasi_deer", draws = 32L, chains = 2L,
                        window = 8L, seed = 88L, audit = TRUE)
  expect_s3_class(parallel$draws, "draws_array")
  expect_equal(dim(parallel$draws), c(32L,2L,2L))
  expect_equal(unname(as.array(parallel$draws)), unname(as.array(sequential$draws)), tolerance = 1e-7)
  expect_identical(parallel$record$tape_sha256, sequential$record$tape_sha256)
  expect_error(pb_sample(model, kernel = "mala", executor = "online_picard"), "only RWM")
  failed <- pb_sample(model, executor = "quasi_deer", draws = 32L, max_iter = 1L)
  expect_identical(failed$record$status, "failed")
  expect_null(failed$draws)
  expect_true(length(failed$record$failed_trajectory)>0L)
})

test_that("nonrepresentable constrained output never becomes a posterior object", {
  skip_if(Sys.getenv("PB_RUN_INTEGRATION") != "1", "Set PB_RUN_INTEGRATION=1 with pinned Python")
  model <- pb_model("lognormal", mu = 1000, sigma = 1)
  failed <- pb_sample(model, draws = 2L, initial = c(1000), audit = TRUE)
  expect_identical(failed$record$status, "failed")
  expect_null(failed$draws)
  expect_true(length(failed$record$failed_trajectory) > 0L)
  expect_match(failed$record$transform_error, "overflow")
})


test_that("single-element native vectors retain array shape", {
  skip_if(Sys.getenv("PB_RUN_INTEGRATION") != "1", "Set PB_RUN_INTEGRATION=1 with pinned Python")
  model <- pb_model("normal_mean", y = c(1))
  fit <- pb_sample(model, draws = 8L, initial = c(0))
  expect_identical(dim(fit$draws), c(8L, 1L, 1L))
  expect_identical(fit$record$status, "completed")
})
