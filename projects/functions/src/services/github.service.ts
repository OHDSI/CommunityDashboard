import {inject, Provider} from '@loopback/core';
import {getService} from '@loopback/service-proxy';
import {GitHubDataSource} from '../datasources';
import {Response} from 'cross-fetch';

interface OrgParameters {
  org: string
}

interface OwnerParameters {
  owner: string
}

interface RepoParameters {
  repo: string
}

interface PathParameters {
  path: string
}

interface ReadmeParameters {
  ref?: string
}

export interface ContentFile extends Omit<Response, 'body'> {
  body: {
    content: string
  }
}

export interface MinimalRepositoryArray extends Omit<Response, 'body'> {
  body: {
    name: string,
    // eslint-disable-next-line @typescript-eslint/naming-convention
    updated_at: string,
    // eslint-disable-next-line @typescript-eslint/naming-convention
    watchers_count: number,
  }[]
}

export interface CommitArray extends Omit<Response, 'body'> {
  body: {
    sha: string,
    commit: {
      author: {
        name: string,
        email: string,
        date: string
      }
    }
  }[]
}

export interface GitHub {
  reposListCommits(parameters: OwnerParameters & RepoParameters & PathParameters): Promise<CommitArray | Response>
  reposListForOrg(parameters: OrgParameters): Promise<MinimalRepositoryArray | Response>
  reposGetReadme(parameters: OwnerParameters & RepoParameters & ReadmeParameters): Promise<ContentFile | Response>
}

export class GitHubProvider implements Provider<GitHub> {

  constructor(
    // github must match the name property in the datasource json file
    @inject('datasources.GitHub')
    protected dataSource: GitHubDataSource = new GitHubDataSource(),
  ) {}

  value(): Promise<GitHub> {
    return getService(this.dataSource);
  }
}
