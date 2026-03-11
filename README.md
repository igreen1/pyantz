
# TODO:

1. for jobs which submit other jobs (branch): improve frontend
2. support scoping of variables (submitting josb inherit parent variables)
3. support resolving variables as a job is called in the configuration
4. support setting variables in a job (as a submission?)
---> somehow want to be able to add variable scopes
---> would require messing with JobConfigWithContext (not just JobConfig)
------> this could be funky... but i think it's doable with minimal "big" edits

Useful jobs to do


1. how to edit variables by a user? need to apss variables odwn a pipeline
---> submit job with context. submit functions aceept jobs with context.
----> so simply add context and submit the job - easy peasy
2. add a case matrix job (duh)
3. add a case matrix creator job (cross join variables and output)
4. 
7. edit yaml
8. edit generic file using external function
9. (maybe) edit file using custom function (python `exec`?)


API updates:
1. How to add schemas etc for jobs defined in external libraries (must somehow run the code to import them in the api....)
--> add a new api route to dynamically add them perhaps and then the frontend just re-queries?


Frontend updates
1. save the config file to a json file for actually running it
2. validate a configuration as a whole
3. add scoped variables (behind the scenes, this would likely create a bunch of weird submissions)
