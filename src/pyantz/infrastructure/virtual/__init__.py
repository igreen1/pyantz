"""Virtual jobs edit jobs which depend on them to achieve some desired effect.

For example, rather than a user setting a variable wrapper context, they can
use a virtual job "add_variable". ANy jobs which depend on "add_variable" will,
instead of being submitted and actually dependent, be transformed into
child jobs of the virtual job, which will submit them with modified context.

In other words, 

Add Variable -> JobA

Is actually

SubmitInContext[JobA]
"""