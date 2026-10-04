\name{parallelbayes}
\alias{pb_model}
\alias{pb_capabilities}
\alias{pb_sample}
\alias{pb_validate}
\alias{pb_benchmark}
\alias{pb_environment}
\title{Auditable time parallel MCMC experiments}
\description{Define a target, inspect supported combinations, sample in batches and retain numerical and timing records.}
\usage{
pb_model(kind = "gaussian", ..., stan_file = NULL, data = list(),
         backend = c("jax", "torch"))
pb_capabilities(model)
pb_sample(model, kernel = "mala", executor = "sequential", ...,
          failure = c("record", "error"))
pb_validate(model, points = NULL, reference = NULL)
pb_benchmark(model, configurations, output = NULL)
pb_environment(backend = c("jax", "torch"))
}
\arguments{
\item{kind}{Explicit native target kind: gaussian, logistic, lognormal, normal_mean, funnel, funnel_noncentered or mixture. Query supported combinations with \code{pb_capabilities}.}
\item{backend}{Optional numerical provider: \code{jax} (default) or \code{torch}. Install the selected provider separately. Stan uses the CPU BridgeStan provider through the default route.}
\item{...}{Target fields for \code{pb_model}; sampler settings such as draws, chains, seed, step_size, window, max_iter, platform (JAX), device (torch: cpu or cuda), audit, initial or warmup for \code{pb_sample}.}
\item{stan_file}{Path to a standard Stan source. Selects the CPU BridgeStan provider.}
\item{data}{Named list of Stan data.}
\item{model}{A \code{pb_model} object.}
\item{kernel}{\code{rwm} or \code{mala}; \code{nuts} is available through the JAX/BlackJAX route only. The separate Pyro CPU baseline is not exposed by this R sampler.}
\item{executor}{\code{sequential}, MALA \code{quasi_deer} or RWM \code{online_picard}.}
\item{failure}{Retain a failed result (default) or throw an error.}
\item{points}{Matrix of common unconstrained-coordinate validation points.}
\item{reference}{Optional native model for independent Stan target validation.}
\item{configurations}{List of named sampler-setting lists.}
\item{output}{Optional RDS output path.}
}
\details{
Configure \code{RETICULATE_PYTHON} before loading Python. Install the pinned project Python dependencies first. Stan requires \code{BRIDGESTAN} to point to the pinned extracted source distribution.
MALA uses proposal \eqn{q+h\nabla\log p(q)+\sqrt{2h}z}; RWM uses \eqn{q+s z}. All calculations request float64. Seeded actual MH noise is shared by corresponding executors, not by NUTS.
The quasi-DEER executor uses non-overlapping blocks and a numerical residual criterion; it does not certify exact trajectories. Online Picard confirms increment consistency subject to floating-point arithmetic. \code{audit=TRUE} adds an independent sequential trajectory and acceptance check. Failed trajectories never appear in the draws object. Diagnostic completion does not certify equilibrium or adequate exploration.
For MH, \code{draws} is the total number of transitions, including rejected self-loops. The \code{warmup} field is used only by NUTS; it does not add or discard MH transitions. Users must explicitly choose and discard an MH initialization segment. With an explicitly selected sequential fallback, JAX retries executor stopping failures but not audit mismatches. Torch also retries audit failures and audits the replacement path again. Both reuse the actual input arrays and retain the primary failure and cost; neither retries output-transform failures. The frozen Windows protocol disables fallback.
\code{pb_benchmark} is a convenience runner, not a replacement for the frozen protocol CLI. Stan CPU calls compiled density and derivative functions in a serial Python loop. Stan supports sequential RWM/MALA only; arbitrary Stan-to-GPU translation is unsupported. Torch CUDA support is limited to the documented native targets and verified environment, with eager Python control.
}
\value{Model and capability objects, validation lists, or a \code{pb_fit} containing a \pkg{posterior} draws_array and an independent record. Failed fits have NULL draws and retain diagnostics.}
\examples{
\dontrun{
model <- pb_model("gaussian", dimension = 2L)
fit <- pb_sample(model, executor = "quasi_deer", draws = 64L,
                 window = 16L, audit = TRUE)
fit$record$audit
posterior::summarise_draws(fit$draws)

# Requires the optional torch provider.
torch_model <- pb_model("gaussian", dimension = 2L, backend = "torch")
pb_capabilities(torch_model)
torch_fit <- pb_sample(torch_model, kernel = "rwm",
                       executor = "online_picard", device = "cpu",
                       draws = 64L, window = 16L, audit = TRUE)
}
}
