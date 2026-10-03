args <- commandArgs(trailingOnly=TRUE)
.libPaths(c("D:/Tools/R-library-4.6",.libPaths()))
library(posterior)
paths <- list.files(args[[1]], pattern="diagnostic-input.csv", recursive=TRUE, full.names=TRUE)
records <- list()
for (path in paths) {
 t <- proc.time()[[3]]
 x <- read.csv(path, check.names=FALSE)
 chains <- sort(unique(x$chain)); it <- sort(unique(x$iteration)); names <- setdiff(colnames(x),c("chain","iteration"))
 arr <- array(NA_real_,c(length(it),length(chains),length(names)),dimnames=list(iteration=it,chain=chains,variable=names))
 for (j in seq_along(chains)) arr[,j,] <- as.matrix(x[x$chain==chains[j],names,drop=FALSE])
 ds <- as_draws_array(arr)
 s <- summarise_draws(ds, rhat=rhat,ess_bulk=ess_bulk,ess_tail=ess_tail)
 constants <- vapply(seq_along(names),function(k) length(unique(c(arr[,,k])))==1L,logical(1))
 s$state <- ifelse(constants,"undefined_no_variation",ifelse(is.finite(s$rhat),"finite","not_finite"))
 records[[dirname(path)]] <- list(summary=s,elapsed=proc.time()[[3]]-t,posterior_version=as.character(packageVersion("posterior")))
}
jsonlite::write_json(records,args[[2]],auto_unbox=TRUE,pretty=TRUE,digits=NA,na="null")
cat(length(records),"fits diagnosed with rank/folded Rhat, bulk ESS and tail ESS\n")
