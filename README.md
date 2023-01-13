# CommunityDashboard
The Community Dashboard is a full stack app for tracking and connecting the activities of the OHDSI community. The goal of the dashboard is help our community identify how members can see the OHDSI eco-system as an interconnected system to make a larger impact. 

# Repo Layout
This repo contains multiple "projects" as `yarn` [workspaces](https://yarnpkg.com/features/workspaces):
- The `client` project implements the 
  client side Community Dashboard application using Angular.
- The `plots` Python package is a Flask app 
  that implements the following back-end services.
  - Data access layer for CosmosDB.  
  - Service layer for the following API miners.
    - Youtube Data API to search and track statistics on OHDSI videos
    - PubMed Entrez API to identify and track publications 
    - Serpapi Wrapper for Google Scholar to pull citation statistics
  - Python/plotly generated visualizations.
- The `development` [devcontainer](https://containers.dev)
  template provides a consistent,
  prebuilt environment for developers described below.

# Development
This repo uses the [Development Container](https://containers.dev/implementors/spec/)
spec. to define the dev environment. This has native support
in [VSCode](https://code.visualstudio.com/docs/devcontainers/containers),
[GitHub Codespace](https://docs.github.com/en/codespaces),
and [other tools](https://containers.dev/supporting), or you
can use the spec as a reference to set up your local environment of choice.

[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://github.com/codespaces/new?hide_repo_select=true&ref=main&repo=584238132&machine=standardLinux32gb&location=EastUs&devcontainer_path=.devcontainer%2Fdevcontainer.json)

> Note for new developers: The commands below may publish their results
> via a web app. Your IDE may launch the browser window before
> the app has loaded. Simply refresh your browser window when the app
> has loaded. If you are having trouble, the process is described
> [here for GitHub Codespaces](https://docs.github.com/en/codespaces/developing-in-codespaces/forwarding-ports-in-your-codespace).


`yarn` is used to manage the rest of the development workflow:
```
yarn test
```
```
yarn workspace @community-dashboard/plots start
```
```
yarn workspace @community-dashboard/client start
```
Or, equivalent to something like `docker-compose up`.
```
yarn workspaces foreach -pi run start
```
[storybook](https://storybook.js.org) is a tool for spot checking and documenting UI components.
```
yarn storybook
```

> Known Issue:
> Dev builds in cloud containers (ex. GH Actions/Codespaces)
> are flaky - presumably some disk issue. This can result in
> `Error: Module build failed (from ./node_modules/sass-loader/dist/cjs.js): SassError: Can't find stylesheet to import.`
> If you encounter this, retrying whatever command you
> are running should resolve the issue. It may help to delete .angular.

# Getting Involved

We use the GitHub issue tracker for all bugs/issues/enhancements

# License
Licensed under Apache License 2.ty