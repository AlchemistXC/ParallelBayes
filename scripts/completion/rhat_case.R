# Read-only companion diagnostic. Does not change posterior or the saved samples.
args <- commandArgs(trailingOnly = TRUE)
if (length(args) != 2L) stop("Usage: Rscript rhat_case.R CASE_DIRECTORY NEW_OUTPUT_DIRECTORY")
case_dir <- normalizePath(args[[1]], mustWork = TRUE)
output <- args[[2]]
if (file.exists(output)) stop("Output already exists; choose a new attempt directory")
library(posterior)
if (as.character(packageVersion("posterior")) != "1.7.0") stop("Use pinned posterior 1.7.0; preserve other environments")
meta <- jsonlite::read_json(file.path(case_dir, "case.json"), simplifyVector = TRUE)
n <- meta$chains * meta$iterations
raw <- readBin(file.path(case_dir, meta$fixture_file), what = "double", n = n + 1L,
               size = 8L, endian = "little")
if (length(raw) != n || any(!is.finite(raw))) stop("Invalid fixture length or values")
x <- matrix(raw, nrow = meta$iterations, ncol = meta$chains)
split <- get(".split_chains", asNamespace("posterior"))
zscale <- get("z_scale", asNamespace("posterior"))
basic_rhat <- get(".rhat", asNamespace("posterior"))
fold <- function(center) basic_rhat(zscale(split(abs(x - center))))
close <- function(a, b) is.finite(a) && abs(a-b) <= meta$comparison_atol + meta$comparison_rtol*abs(b)
rounded <- as.numeric(meta$correctly_rounded_midpoint_hex)
lower <- as.numeric(meta$one_ulp_lower_hex)
middle <- sort(raw)[n/2 + 0:1]
bulk <- basic_rhat(zscale(split(x)))
tail_native <- fold(median(x))
tail_lower <- fold(lower)
tail_rounded <- fold(rounded)
ranks_lower <- rank(abs(raw-lower), ties.method = "average")
ranks_rounded <- rank(abs(raw-rounded), ties.method = "average")
changed <- which(ranks_lower != ranks_rounded)
checks <- list(bulk_matches_mac = close(bulk, meta$expected_bulk_rhat),
               explicit_lower_reproduces_mac = close(tail_lower, meta$observed_mac_rhat),
               explicit_midpoint_reproduces_archived_windows = close(tail_rounded, meta$archived_windows_rhat),
               native_matches_one_recorded_result = close(rhat(x), meta$observed_mac_rhat) || close(rhat(x), meta$archived_windows_rhat),
               five_ranks_change = length(changed) == 5L)
result <- list(status = if (all(unlist(checks))) "checks_passed" else "unexpected_runtime_result",
  scope = "fixed input, alternative folding centers; no sampler rerun or replacement of original diagnostics",
  checks = checks, R_version = unclass(R.version), posterior_version = as.character(packageVersion("posterior")),
  matrixStats_version = as.character(packageVersion("matrixStats")),
  machine = .Machine, session_info = capture.output(sessionInfo()),
  input = list(fixture_sha256 = meta$fixture_sha256, chains = meta$chains, iterations = meta$iterations),
  centers_hex = list(native_median = sprintf("%a", median(x)), mean_middle = sprintf("%a", mean(middle)),
                     direct_midpoint = sprintf("%a", (middle[1]+middle[2])/2),
                     supplied_correct_midpoint = sprintf("%a", rounded), supplied_one_ulp_lower = sprintf("%a", lower)),
  rhat = list(native = rhat(x), bulk = bulk, folded_native = tail_native,
              folded_lower = tail_lower, folded_correct_midpoint = tail_rounded),
  changed_rank_count = length(changed),
  changed = data.frame(flat_index = changed, input_hex = sprintf("%a", raw[changed]),
      folded_lower_hex = sprintf("%a", abs(raw[changed]-lower)),
      folded_midpoint_hex = sprintf("%a", abs(raw[changed]-rounded)),
      lower_rank = ranks_lower[changed], midpoint_rank = ranks_rounded[changed]),
  diagnostic_function_sources = lapply(c("rhat.default", "fold_draws", "z_scale", ".rhat"),
      function(name) paste(deparse(get(name,asNamespace("posterior"))),collapse="\n")))
dir.create(output, recursive = TRUE)
# Independent Python wrapper compares these round-tripped bytes to the fixture.
writeBin(as.double(x), file.path(output,"roundtrip-f64le.bin"), size=8L, endian="little")
jsonlite::write_json(result, file.path(output,"result.json"), auto_unbox=TRUE,
                    pretty=TRUE, digits=NA, na="null")
cat(result$status, "native Rhat:", format(rhat(x),digits=17), "changed ranks:",length(changed),"\n")
if (!all(unlist(checks))) quit(status=1L)
