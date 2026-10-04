# Diagnostics of an existing finite reference, not a new MCMC fit.
diagnose_reference <- function(values, names, batch_length) {
  stopifnot(length(dim(values)) == 3L, dim(values)[[3]] == length(names),
            all(is.finite(values)), dim(values)[[1]] %% batch_length == 0L)
  n <- dim(values)[[1]]; chains <- dim(values)[[2]]
  rows <- lapply(seq_along(names), function(k) {
    x <- values[, , k]
    chain_means <- colMeans(x)
    globally_constant <- length(unique(as.vector(x))) == 1L
    constant_chains <- which(apply(x, 2L, function(z) length(unique(z)) == 1L))
    between <- stats::sd(chain_means) / sqrt(chains)
    batch_means <- unlist(lapply(seq_len(chains), function(j)
      colMeans(matrix(x[, j], nrow=batch_length))))
    batch <- stats::sd(batch_means) / sqrt(length(batch_means))
    diagnostic <- c(rhat=posterior::rhat(x), ess_bulk=posterior::ess_bulk(x),
                    ess_tail=posterior::ess_tail(x), mcse_mean=posterior::mcse_mean(x))
    # A zero/undefined estimated variance is not a certainty certificate.
    eligible <- !globally_constant && length(constant_chains) == 0L &&
                all(is.finite(diagnostic)) && all(c(between, batch, diagnostic[['mcse_mean']]) > 0)
    list(variable=names[[k]], mean=mean(x), sd=stats::sd(as.vector(x)),
         q05=unname(stats::quantile(x, .05)), q95=unname(stats::quantile(x, .95)),
         chain_means=unname(chain_means),
         rhat=unname(diagnostic[['rhat']]), ess_bulk=unname(diagnostic[['ess_bulk']]),
         ess_tail=unname(diagnostic[['ess_tail']]),
         mcse_posterior=if (globally_constant) NA_real_ else unname(diagnostic[['mcse_mean']]),
         mcse_between_chains=if (globally_constant) NA_real_ else between,
         mcse_batch=if (globally_constant) NA_real_ else batch,
         mcse_max_available=if (eligible) max(between, batch, diagnostic[['mcse_mean']]) else NA_real_,
         global_constant=globally_constant, constant_chains=constant_chains,
         uncertainty_status=if (eligible) 'finite_MCSE_estimates_not_bias_bounds' else 'undetermined',
         positive_count=sum(x > 0), zero_count=sum(x == 0))
  })
  list(dimensions=dim(values), batch_length=batch_length,
       batch_count=as.integer(n / batch_length * chains), summary=rows)
}

main <- function(args) {
  if (length(args) != 1L) stop('Usage: Rscript wells_reference_audit.R NEW_RUN_DIRECTORY')
  root <- args[[1]]
  output <- file.path(root, 'diagnostics.json')
  if (file.exists(output)) stop('Preserve prior diagnostics')
  spec <- jsonlite::read_json(file.path(root, 'array.json'), simplifyVector=TRUE)
  if (as.character(packageVersion('posterior')) != spec$posterior_version)
    stop('posterior version differs from analysis specification')
  count <- prod(spec$dimensions)
  if (count > 2000000 || count < 1 || length(spec$dimensions) != 3L) stop('Invalid dimensions')
  path <- file.path(root, 'values-f64le.bin')
  if (file.info(path)$size != count * 8) stop('Unexpected binary size')
  flat <- readBin(path, what='double', n=count, size=8L, endian='little')
  values <- array(flat, dim=spec$dimensions)
  result <- diagnose_reference(values, spec$variables, spec$batch_length)
  result$posterior_version <- as.character(packageVersion('posterior'))
  result$R_version <- R.version.string
  result$session_info <- capture.output(sessionInfo())
  writeBin(as.vector(values), file.path(root, 'roundtrip-f64le.bin'), size=8L, endian='little')
  jsonlite::write_json(result, output, auto_unbox=TRUE, pretty=TRUE, digits=NA, na='null')
  print(do.call(rbind, lapply(result$summary, function(x)
    data.frame(variable=x$variable, mean=x$mean, rhat=x$rhat, MCSE=x$mcse_max_available))))
}
if (sys.nframe() == 0L) main(commandArgs(trailingOnly=TRUE))
