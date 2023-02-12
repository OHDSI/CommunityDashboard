import { Inject, Injectable } from '@angular/core';
import { RestToken, RestDelegate, Rest } from 'rest';
import { map, of, tap } from 'rxjs';

export enum Status {
  COMPLETE = 'complete',
  IN_PROGRESS = 'in progress',
  ERROR = 'error'
}

export interface ScanLog {
  id: number,
  scanId: number,
  status: Status,
  repository?: {
    name: string,
    updatedAt: string,
    watchersCount: number,
  },
  readmeCommit?: {
    repoName: string,
    sha: string,
    author: {
      name: string,
      email: string,
      date: string,
    },
    summary: {
      exists: boolean,
      title?: string,
      status?: string,
      useCases?: string[],
      studyType?: string[],
      tags?: string[],
      studyLead?: string[],
      startDate?: string,
      endDate?: string,
      protocol?: string,
      publications?: string,
      results?: string,
    }
  },
}

@Injectable({
  providedIn: 'root'
})
export class ScanLogsService extends RestDelegate<ScanLog> {

  _cache: ScanLog[] = []

  constructor(
    @Inject(RestToken) rest: Rest,
    @Inject('environment') environment: any,
  ) {
    super(
      rest, environment.rest, 'logs', 
      undefined,
      undefined,
      undefined,
      undefined,
      {scope: '/scans/12'}
    )
  }

  get cache() {
    if (this._cache.length) {
      return of(this._cache)
    } else {
      return this.find().pipe(
        // map(ls => {
        //   return ls.filter(l => l.repository && l.repository.name !== 'StudyRepoTemplate' && l.repository.name !== 'EmptyStudyRepository')
        // }),
        tap(ls => {
          if (!this._cache.length) {
            this._cache.push(...ls)
          }
        }),
      )
    }
  }

}
