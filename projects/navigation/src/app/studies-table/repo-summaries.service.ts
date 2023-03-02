import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestToken } from '@community-dashboard/rest';

export interface RepoSummary {
  name: string,
  updatedAt?: string | null,
  watchersCount?: number,
}

@Injectable({
  providedIn: 'root'
})
export class RepoSummariesService extends RestDelegate<RepoSummary> {

  constructor(
    @Inject(RestToken) rest: Rest,
  ) {
    super(rest, '', 'communityDashboardRepos')
  }
  
}
