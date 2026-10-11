# Binary read-only replay. Rounding is a labelled sensitivity check and does
# not replace stored samples or the original formal diagnostic estimates.
library(posterior)
folder <- commandArgs(TRUE)[1]
readq <- function(name) matrix(readBin(file.path(folder,paste0(name,'.bin')),
  'double',16384,size=8,endian='little'),nrow=4096,ncol=4)
a <- readq('seq'); b <- readq('deer')
results <- lapply(list(seq=a,deer=b),function(x) list(
  rhat=rhat(x),ess_bulk=ess_bulk(x),ess_tail=ess_tail(x),
  q05=unname(quantile(x,.05)),q95=unname(quantile(x,.95)),
  q05_ess=ess_basic(x<=quantile(x,.05)),q95_ess=ess_basic(x<=quantile(x,.95)),
  q05_count=colSums(x<=quantile(x,.05)),rounded12_tail=ess_tail(round(x,12))))
jsonlite::write_json(list(scope='Read-only replay plus a decimal-rounding sensitivity check; historical values unchanged',
  posterior=as.character(packageVersion('posterior')),results=results,
  max_abs_difference=max(abs(a-b)),rounded12_identical=identical(round(a,12),round(b,12))),
  file.path(folder,'diagnostic-replay.json'),auto_unbox=TRUE,pretty=TRUE,digits=NA,na='null')
