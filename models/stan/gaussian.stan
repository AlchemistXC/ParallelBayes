data { int<lower=1> D; vector[D] mu; matrix[D,D] precision; }
parameters { vector[D] q; }
model { target += -0.5 * dot_product(q-mu, precision*(q-mu)); }
