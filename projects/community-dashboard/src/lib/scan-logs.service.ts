import { Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
import { concatMap, from, map, Observable, of, reduce, shareReplay, tap } from 'rxjs';
import { ReadmeSummariesService } from './studies-table/readme-summaries.service';
import { RepoSummariesService } from './studies-table/repo-summaries.service';

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
      studyLeads: string[] | null,
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
    repoSummariesService: RepoSummariesService,
    readmeSummariesService: ReadmeSummariesService
  ) {
    const rest = new RestMemory(repoSummariesService.find().pipe(
      concatMap((rs) => {
        return from(rs).pipe(
          concatMap(r => {
            return readmeSummariesService.find({
              delegate: {scope: {repo: r.name}}
            }).pipe(
              concatMap(ss => {
                return ss.map(s => ({
                  id: s.sha,
                  repository: r!,
                  readmeCommit: {
                    repoName: r.name,
                    sha: s.sha,
                    author: s.author,
                    summary: s.summary
                  }
                }))
              })
            )
          })
        )
      }),
      reduce((acc, l) => {acc[l.readmeCommit.sha] = l; return acc}, {} as {[key: string]: ScanLog}),
      map(ls => ({
        '/scan-logs': ls
      })),
      map(test => {
        return test
      })
    ))
    super(rest, '', 'scan-logs')

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
