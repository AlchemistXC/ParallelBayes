data { real mu; real<lower=0> sigma; }
parameters { real<lower=0> theta; }
model { theta ~ lognormal(mu, sigma); }
