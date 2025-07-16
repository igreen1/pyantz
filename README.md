# PyAntz

Job runner and scheduling

Setup configurations to chain together different jobs quickly and with minimal code. The goal here
is to help those who need to quickly setup a local data pipeline for small projects. This spawned
off of a school project


## Dev Notes

TODO
 - GUI to create the jobs
 - analysis jobs support directory parquet style
 - edit yamls
 - joins
 - union (all rows from both)
 - set difference (rows in the first relation but not the second)
 - cartesian product (all possible combinations of rows)
 - csv to parquet
 - single file parquet to directory parquet
 - directory parquet to single file parquet
 - excel to parquet
 - hdf5 (.h5) to parquet
 - parquet to postgres
 - parquet to mysql
 - postgres query to parquet
 - mysql query to parquet
 - upload parquet to minio
 - download parquet from minio
 - create hvplot from parquet (scatter)
 - join pipelines (will be very complicated due to architecture)
 - aggregation functions (count, sum, min, max, xth percentile)

Possible
 - dependent jobs?
 - virtual jobs (composed of multiple jobs but simplifies configuration)
    virtual jobs should allow users to define custom virtual jobs (templates). add API for this