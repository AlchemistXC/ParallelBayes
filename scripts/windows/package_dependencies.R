args <- commandArgs(trailingOnly=TRUE)
if(length(args)!=2L) stop('new library and evidence directory required')
lib <- normalizePath(args[1],winslash='/',mustWork=TRUE)
out <- normalizePath(args[2],winslash='/',mustWork=TRUE)
.libPaths(c(lib,.Library)); options(repos=c(CRAN='https://cloud.r-project.org'))
available <- available.packages(contriburl=contrib.url(getOption('repos'),'win.binary'))
wanted <- c('reticulate','posterior','jsonlite','testthat')
deps <- unique(c(wanted,unlist(tools::package_dependencies(wanted,db=available,
  which=c('Depends','Imports','LinkingTo'),recursive=TRUE))))
base <- installed.packages(lib.loc=.Library)
reuse <- base[!is.na(base[,'Priority']) & base[,'Priority'] %in% c('base','recommended'),,drop=FALSE]
deps <- setdiff(deps,c('R',rownames(reuse)))
downloads <- file.path(out,'R-dependency-archives');dir.create(downloads)
files <- download.packages(deps,destdir=downloads,type='win.binary')
if(nrow(files)!=length(deps)) stop('Dependency download incomplete')
install.packages(files[,2],repos=NULL,type='win.binary',lib=lib)
if(!all(deps %in% rownames(installed.packages(lib.loc=lib)))) stop('New-library dependency installation incomplete')
inventory <- as.data.frame(installed.packages(lib.loc=c(lib,.Library)),stringsAsFactors=FALSE)
jsonlite::write_json(list(R=R.version.string,library=lib,lib_paths=.libPaths(),
  installed=inventory[,c('Package','Version','LibPath','Priority')],
  reused_system_base_or_recommended=as.data.frame(reuse[,c('Package','Version','LibPath','Priority'),drop=FALSE]),
  downloaded=as.data.frame(files),scope='Native Windows binary dependencies; no existing user library copied'),
  file.path(out,'R-dependency-inventory.json'),auto_unbox=TRUE,pretty=TRUE,na='null')
