Component tests in this directory are used for sanity checks for
various of components during deployment.
Results of these steps will be assumed as the results of the
corresponding deployment step in the TestRail report.

DO NOT use deployment fixtures that are depended on the 'hardware'
fixture because 'hardware' fixture won't be initialized for these checks.

To access the environment, please use '*_actions' fixtures that
provide managers to work with the components directly.