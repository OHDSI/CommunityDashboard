import { Injectable } from '@angular/core';
import { TableFieldValue, TableDataService, TableQuery } from '@community-dashboard/rest';
import { map, Observable, shareReplay } from 'rxjs';
import { ReadmeSummariesService, ReadmeSummary } from './studies-table/readme-summaries.service';

export enum Status {
  COMPLETE = 'complete',
  IN_PROGRESS = 'in progress',
  ERROR = 'error'
}

export interface ScanLog {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
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
export class ScanLogsService implements TableDataService<ScanLog> {

  constructor(
    private readmeSummariesService: ReadmeSummariesService,
  ) {}

  valueChanges(params?: TableQuery): Observable<ScanLog[] | null> {
    return this.readmeSummariesService.valueChanges(params).pipe(
      map(rs => toScanLog(rs))
    )
  }

  count(params?: TableQuery | undefined): Observable<number> {
    return this.readmeSummariesService.count(params)
  }

  _cache: Observable<ScanLog[]> | null = null
  get cache(): Observable<ScanLog[]> {
    if (this._cache) {
      return this._cache
    } else {
      this._cache = this.readmeSummariesService.valueChanges().pipe(
        map(rs => {
          return toScanLog(rs)
        }),
        shareReplay(1)
      )
      return this._cache
    }
  }

}

function toScanLog(rs: ReadmeSummary[] | null) {
  if (!rs) {
    return []
  }
  return rs.map(r => {
    return {
      id: r.id!,
      repository: r.denormRepo,
      readmeCommit: {
        repoName: r.denormRepo.name,
        sha: r.sha,
        author: r.author,
        summary: r.summary
      }
    }
  })
}