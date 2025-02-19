
TODO
-> slurm
    on failure of submission, retry with different node
    batch submit
    individual submit
-> windows hpc
    on failure of submission, retyr with different node
    batch submit
-> GUI to create the jobs
-> check the arg types of the functions in the job 
-> call the pydantic classes of each job
-> use pyarrow
--> support using dask, pandas or pyarrow as the backend


- make dirs
call os make dirs
- edit yaml
edit fields (multiple!) set values
---> accepts two lists. the first is a list of str (paths to edit) and the second it values
---> must be of the same length, checked at runtime :( 

- edit json
---> same as edit yaml above
- edit csv
---> accepts column names, list of values
---> only one column at a time

- convert csv to parquet
---> read csv and output to parquet
- convert excel to parquet
accepts path to excel and optionally the sheet name
---> read into memory and output to parquet
- convert hdf5 to parquet
accepts path and keys and reads into pandas
outputs to parquet

convert parquet to csv
convert parquet to excel
convert hdf5 to excel

# DB
CRUD postgres
CRUD mysql
CRUD minio
CRUD sql server

# Plot
- scatter x/y with color options
- hist 
- stacked hist

# Aggregation
- merge parquets 
- concatenate parquets
- filter parquet
- count parquet
- sum parquet
- min parquet
- max parquet
- xth percentile
- groupby and agg

# splitters
- split template into N pipelines
take one example pipeline and produce a PIPELINE ID variable for each in range
- generate simple case matrix
for one variable being modified, create pipelines for range of values for the variable (only integers)
- 