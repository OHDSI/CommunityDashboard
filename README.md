# CommunityDashboard
The Community Dashboard is a full stack app for tracking and connecting the activities of the OHDSI community. The goal of the dashboard is help our community identify how members can see the OHDSI eco-system as an interconnected system to make a larger impact. 

# Repo Layout
This repo contains multiple "projects" as `yarn` [workspaces](https://yarnpkg.com/features/workspaces):
- The `navigation` project implements the 
  client side Community Dashboard components as an Angular component library.
- The `functions` implements the core "back end" logic of the application
  including data access and some API integration.
- The `plots` Python package is a Flask app 
  for backend services that rely on the Python ecosystem
  (for ML for ex.) or are expected to be maintained
  primarily by data scientists (who might prefer using Python).
  - Serving of plotly generated visualizations.
  - Service layer for the following API miners.
    - Youtube Data API to search and track statistics on OHDSI videos
    - PubMed Entrez API to identify and track publications 
    - Serpapi Wrapper for Google Scholar to pull citation statistics
- The `development` [devcontainer](https://containers.dev)
  template provides a consistent,
  prebuilt environment for developers described below.
- The `rest` project provides a standard interface for all
  database operations. See: [Production Considerations](#production-considerations)

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
yarn serve
```
```
yarn workspace @community-dashboard/plots start
```

# Production considerations
- Database: For development purposes all projects use in-memory
  testing databases. For production deployment you will need to
  implement [this rest interface](projects/rest/src/lib/rest.ts) via dependency injection.
- Scheduling: This open source project does not depend on any
  particular scheduler. In production you may wish to execute
  back end functions on some schedule or in response to some
  events which will require integration with your scheduler of
  choice.

# Getting Involved
We use the GitHub issue tracker for all bugs/issues/enhancements

# License
Licensed under Apache License 2.ty