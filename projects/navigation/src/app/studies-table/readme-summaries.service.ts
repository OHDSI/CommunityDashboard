import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, TableFieldValue } from '@community-dashboard/rest';

export interface ReadmeSummary {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id?: string,
  "summary": {
    "useCases": string[]
    "protocol": string,
    "studyLead": string[],
    "endDate": string,
    "studyType": string[]
    "title": string,
    "results": string,
    "startDate": string,
    "status": string,
    "tags": string[],
    // "studyLeads": null,
    "publications": string
  } | null,
  "author": {
    "date": string,
    "name": string,
    "email": string
  },
  "denormRepo": {
    "watchersCount": number,
    "name": string,
    "updatedAt": string
  },
  "sha": string
}

@Injectable({
  providedIn: 'root'
})
export class ReadmeSummariesService extends DocsTableDataService<ReadmeSummary> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) {
    super({docs, path: 'communityDashboardRepoReadmeSummaries', idField: 'id'})
  }

}
