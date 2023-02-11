import {get, param, RestBindings, Response, getJsonSchema, SchemaObject} from "@loopback/rest";
import {GitHub, ContentFile} from '../services'
import {GitHubDataSource} from '../datasources'
import {model, property} from '@loopback/repository';
import {inject} from '@loopback/core';

@model()
export class OrgFilter {
  @property({
    required: true
  })
  org:string
}

@model()
export class RepoFilter {
  @property({
    required: true
  })
  owner:string
  @property({
    required: true
  })
  repo:string
}

@model()
export class ReadmeFilter extends RepoFilter {
  @property({
    required: false
  })
  ref?: string
}

@model()
export class CommitsFilter extends RepoFilter {
  @property({
    required: true
  })
  path:string
}

export class GitHubController {
  constructor(
    @inject('services.GitHub')
    protected github: GitHub,
    @inject('datasources.GitHub')
    protected dataSource: GitHubDataSource,
    @inject(RestBindings.Http.RESPONSE) protected response: Response,
  ) {}

  @get('github/repos', {
    responses: {
      200: {
        description: 'OK'
      },
      404: {
        description: 'Org not found.'
      }
    },
  })
  async githubReposFind(
    @param({
      name: 'filter',
      in: 'query',
      content: {
        "application/json": {
          "schema": getJsonSchema(OrgFilter) as SchemaObject
        },
      },
      required: true,
    }) filter: OrgFilter,
  ) {
    const r = await this.github.reposListForOrg(filter)
    return r.body
  }

  @get('github/repos/readme', {
    responses: {
      200: {
        description: 'OK'
      },
      404: {
        description: 'Owner or repo not found.'
      }
    },
  })
  async githubReposReadmeFind(
    @param({
      name: 'filter',
      in: 'query',
      content: {
        "application/json": {
          "schema": getJsonSchema(ReadmeFilter) as SchemaObject
        },
      },
      required: true,
    }) filter: ReadmeFilter,
  ) {
    const r = await this.github.reposGetReadme(filter) as ContentFile
    return r.body.content
  }


  @get('github/repos/commits', {
    responses: {
      200: {
        description: 'OK'
      },
      404: {
        description: 'Owner or repo not found.'
      }
    },
  })
  async githubReposCommitsFind(
    @param({
      name: 'filter',
      in: 'query',
      content: {
        "application/json": {
          "schema": getJsonSchema(CommitsFilter) as SchemaObject
        },
      },
      required: true,
    }) filter: CommitsFilter,
  ) {
    const r = await this.github.reposListCommits(filter)
    return r.body
  }
}
