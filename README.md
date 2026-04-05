
# TODO:

1. for jobs which submit other jobs (branch): improve frontend
Useful jobs to do
2. make case matrix a virtual job
3. edit json using external parser/unparser
4. when ssh-ing, allow creating a tmp file (mkdtemp) and use it
8. edit generic file using external function
9. (maybe) edit file using custom function (python `exec`?)


API updates:
1. How to add schemas etc for jobs defined in external libraries (must somehow run the code to import them in the api....)
--> add a new api route to dynamically add them perhaps and then the frontend just re-queries?


Frontend updates
1. save the config file to a json file for actually running it
2. validate a configuration as a whole
3. add scoped variables (behind the scenes, this would likely create a bunch of weird submissions)
