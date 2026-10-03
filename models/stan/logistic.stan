data { int<lower=1> N; int<lower=1> D; matrix[N,D] X; array[N] int<lower=0,upper=1> y; real<lower=0> prior_scale; }
parameters { vector[D] q; }
model { q ~ normal(0, prior_scale); y ~ bernoulli_logit(X*q); }
