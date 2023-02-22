import { Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
import { of, tap } from 'rxjs';
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

  _cache: ScanLog[] = []

  constructor(
    private repoSummariesService: RepoSummariesService,
    private readmeSummariesService: ReadmeSummariesService
  ) {
    const scanLogs: {[key: string]: ScanLog} = {}
    const rest = new RestMemory({
      '/scan-logs': scanLogs
    })
    super(rest, '', 'scan-logs')
    this.repoSummariesService.find().subscribe({
      next: (rs) => {
        for (const r of rs) {
          this.readmeSummariesService.find({
            delegate: {scope: {repo: r.name}}
          }).subscribe({
            next: ss => {
              for (const s of ss) {
                scanLogs[s.sha] = {
                  id: s.sha,
                  repository: r!,
                  readmeCommit: {
                    repoName: r.name,
                    sha: s.sha,
                    author: s.author,
                    summary: s.summary
                  }
                }
              }
            }
          })
        }
      }
    })
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
