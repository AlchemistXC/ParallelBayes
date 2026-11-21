args <- commandArgs(trailingOnly = TRUE)
path <- args[[1]]
steps <- as.integer(args[[2]])
variables <- readLines(args[[3]])
n <- steps * 10L * length(variables)
stopifnot(file.info(path)$size == 8 * n)
values <- readBin(path, "double", n = n, size = 8L, endian = "little")
stopifnot(all(is.finite(values)))
draws <- posterior::as_draws_array(array(values, c(steps, 10L, length(variables)),
                                         dimnames = list(NULL, NULL, variables)))
summary <- posterior::summarise_draws(draws, mean = base::mean, sd = stats::sd,
                                     rhat = posterior::rhat, ess_bulk = posterior::ess_bulk,
                                     ess_tail = posterior::ess_tail, mcse = posterior::mcse_mean)
write.table(as.data.frame(summary), args[[4]], row.names = FALSE, sep = "\t", quote = FALSE)
cat(R.version.string, "\nposterior ", as.character(packageVersion("posterior")), "\n", sep = "")
