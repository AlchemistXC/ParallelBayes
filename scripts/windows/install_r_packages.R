args <- commandArgs(trailingOnly=TRUE)
lib <- if (length(args)) args[[1]] else "D:/Tools/R-library-4.6"
dir.create(lib, recursive=TRUE, showWarnings=FALSE)
.libPaths(c(lib,.libPaths()))
install.packages(c("reticulate","posterior","jsonlite","testthat","renv"), lib=lib,
                 repos="https://cloud.r-project.org", type="binary")
needed <- c("reticulate","posterior","jsonlite","testthat","renv")
stopifnot(all(vapply(needed,requireNamespace,logical(1),quietly=TRUE)))
write.csv(as.data.frame(installed.packages(lib.loc=lib)),
          "execution/windows-native/r-packages.csv",row.names=FALSE)
capture.output(sessionInfo(),file="execution/windows-native/r-session.txt")
