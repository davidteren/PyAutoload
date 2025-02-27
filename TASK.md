My vision for this project "Power Auto-Load" is an attempt to explore the feasibility of providing the Python 
ecosystem with a Zeitwerk type auto-loader. It's really difficult to navigate and carry the cognitive overhead of 
imports and resolving requirements when working in Python, as opposed to modern Ruby and Rails.

I think the first approach should be to look at the provided PRD requirements and tasks, but also do a deep analysis 
and document this of the Zydeback repo at this path /Users/davidteren/Projects/OSS/zeitwerk and to strongly follow 
the Test Driven Development approach so in the PyAutoload implementation first create the tests that replicate the 
features we want in Python and skip them, then take an approach by unskipping and implementing so that we are 
ensuring that nothing breaks as we progress.



@PRD.md#L1-38 @requirements.md#L1-12 @tasks.md#L1-28 