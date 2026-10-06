args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=3L) stop('test source root, new output, Python environment JSON required')
dir.create(args[2],recursive=TRUE);library(parallelbayes)
results <- list()
for(name in c('test-torch-installed.R','test-environment-record.R')) {
  result <- testthat::test_file(file.path(args[1],name),reporter='summary')
  frame <- as.data.frame(result)
  results[[name]] <- frame
  saveRDS(result,file.path(args[2],paste0(name,'.rds')))
  if(any(frame$failed>0L) || any(frame$error) || any(frame$skipped)) stop('Explicit installed torch test failed or skipped')
}
module <- getFromNamespace('.pb_module','parallelbayes')()
path <- normalizePath(module$'__file__',winslash='/',mustWork=TRUE)
expected <- normalizePath(system.file('python',package='parallelbayes'),winslash='/',mustWork=TRUE)
stopifnot(startsWith(path,paste0(expected,'/')))
actual <- pb_environment('torch');python <- jsonlite::fromJSON(args[3])
stopifnot(identical(as.numeric(actual$ram_bytes),as.numeric(python$environment$ram_bytes)))
loaded <- lapply(loadedNamespaces(),function(n) list(package=n,version=as.character(packageVersion(n)),
  path=find.package(n),priority=utils::packageDescription(n)$Priority))
jsonlite::write_json(list(tests=results,Python_module=path,R_package=find.package('parallelbayes'),
  R_package_version=as.character(packageVersion('parallelbayes')),ram_bytes_R=actual$ram_bytes,
  ram_bytes_Python=python$environment$ram_bytes,lib_paths=.libPaths(),loaded_namespaces=loaded),
  file.path(args[2],'summary.json'),auto_unbox=TRUE,pretty=TRUE,na='null',digits=NA)
