import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestToken } from '@community-dashboard/rest';

export interface ReadmeSummary {
  sha: string,
  author: {
    name?: string;
    email?: string;
    date?: string;
  } | null,
  summary: ReadmeSummaryDetails | null
}

export interface ReadmeSummaryDetails {
  title: string | null,
  status: string | null,
  useCases: string[] | null,
  studyType: string[] |null,
  tags: string[] |null,
  studyLead: string[] |null,
  startDate: string|null,
  endDate: string|null,
  protocol: string|null,
  publications: string|null,
  results: string|null,
}

@Injectable({
  providedIn: 'root'
})
export class ReadmeSummariesService extends RestDelegate<ReadmeSummary> {

  constructor(
    @Inject(RestToken) rest: Rest,
  ) {
    super(
      rest, '', 'readmeSummaries',
      undefined, undefined, undefined, undefined, {
        scope: (scope) => `/communityDashboardRepos/${scope['repo']}`
      }
    )
  }
  

}
