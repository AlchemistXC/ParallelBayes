test_that("environment metadata preserves large Python byte counts in R", {
  skip_if(Sys.getenv("PB_RUN_TORCH_INTEGRATION") != "1", "Set PB_RUN_TORCH_INTEGRATION=1 with torch Python")
  actual <- pb_environment("torch")
  # JSON is an independent serialization route; direct py_to_r(int) can truncate.
  py <- reticulate::import("parallelbayes.torch_backend.sampling", convert = FALSE)
  reference <- jsonlite::fromJSON(reticulate::py_to_r(reticulate::import("json",convert=FALSE)$dumps(py$environment())))
  expect_identical(actual$provider, reference$provider)
  expect_equal(actual$ram_bytes, reference$ram_bytes, tolerance = 0)
})
