"""Compile virtual jobs to 'real' jobs."""

"""

Concrete job:
{
    name: `submit_variables`,
    parameters: {
        "subjobs": [jobA, jobB]
    }

}

virtual job:
{
    name: `add_variables`
},
{
    jobA
}
{
    JobB
}

"""
