import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestToken } from '@community-dashboard/rest';
import { Observable, shareReplay } from 'rxjs';

export enum Status {
  COMPLETE = 'complete',
  IN_PROGRESS = 'in progress',
  ERROR = 'error'
}

export interface ScanLog {
  id: string,
  repository?: {
    name: string,
    updatedAt?: string | null,
    watchersCount?: number,
  },
  readmeCommit?: {
    repoName: string,
    sha: string,
    author: {
      name?: string,
      email?: string,
      date?: string,
    } | null,
    summary: {
      title: string | null,
      status: string | null,
      useCases: string[] | null,
      studyType: string[] |null,
      tags: string[] |null,
      studyLead: string[] | null,
      startDate: string|null,
      endDate: string|null,
      protocol: string|null,
      publications: string|null,
      results: string|null,
    } | null
  },
}

@Injectable({
  providedIn: 'root'
})
export class ScanLogsService extends RestDelegate<ScanLog> {

  constructor(
    @Inject('RestToken') rest: Rest
  ) {
    super(rest, '', 'scanLogs')
  }

  _cache: Observable<ScanLog[]> | null = null
  get cache(): Observable<ScanLog[]> {
    if (this._cache) {
      return this._cache
    } else {
      this._cache = this.find().pipe(shareReplay(1))
      return this._cache
    }
  }

}
