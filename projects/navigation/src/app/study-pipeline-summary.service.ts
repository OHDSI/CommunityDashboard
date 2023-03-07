import { ErrorHandler, Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
import { ScanLog, ScanLogsService } from './scan-logs.service';
import * as d3 from 'd3'
import { map } from 'rxjs';

export interface StudyPipelineStage {
  id: number,
  stage: string,
  'studies at stage': number,
  'active studies at stage (last 30 days)': number,
  'avg. days since last update': number,
}

export interface PipelineStage {
  id: string,
  count: number,
  stage: string,
  days: string,
}

@Injectable({
  providedIn: 'root'
})
export class StudyPipelineSummaryService extends RestDelegate<PipelineStage> {

  constructor(
    scanLogsService: ScanLogsService,
    errorHandler: ErrorHandler
  ) {
    const rest = new RestMemory(scanLogsService.cache.pipe(
      map((ls: any) => {
        const stages: {[key: string]: PipelineStage} = {}
        const readmeCommits = ls.filter((l:any) => l.readmeCommit)
          .sort((a: any, b: any) => d3.descending(a.readmeCommit!.author.date, b.readmeCommit!.author.date))
        const byStudy = d3.group(readmeCommits, (c: ScanLog) => c.readmeCommit!.repoName) as Map<string, ScanLog[]>
        const DAYS = 1000 * 3600 * 24
        const VALID_STATUS = [
          'Repo Created',
          'Started',
          'Design Finalized',
          'Results Available',
          'Complete',
        ]
        for (const [repoName, commits] of byStudy.entries()) {
          const lastAuthorDate = commits[0].readmeCommit!.author?.date
          if (!lastAuthorDate) {
            errorHandler.handleError('last commit missing author date')
            continue
          }
          const lastUpdate = new Date(new Date(lastAuthorDate))
          const status = commits[0].readmeCommit!.summary?.status && VALID_STATUS.includes(commits[0].readmeCommit!.summary.status) ? commits[0].readmeCommit!.summary.status : 'Invalid / Suspended'
          for (const c of commits) {
            const newStatus = c.readmeCommit!.summary?.status && VALID_STATUS.includes(c.readmeCommit!.summary.status) ? c.readmeCommit!.summary.status : 'Invalid / Suspended'
            const authorDate = c.readmeCommit!.author?.date
            if (!authorDate) {
              errorHandler.handleError('commit missing author date')
              continue
            }
            const promotionDate = new Date(new Date(authorDate))
            if (newStatus !== status) {
              let days
              const atStage = (lastUpdate.getTime() - promotionDate.getTime()) / DAYS
              if (atStage < 30) {
                days = '< 30 days'
              } else if (atStage < 90) {
                days = '< 90 days'
              } else if (atStage < 180) {
                days = '< 6 months'
              } else if (atStage < 365) {
                days = '< 1 year'
              } else {
                days = '> 1 year'
              }
              const key = `${status} ${days}`
              if (!(key in stages)) {
                stages[key] = {
                  id: key,
                  count: 1,
                  stage: status,
                  days
                }
              } else {
                stages[key].count += 1
              }
              break
            }
          }
        }
        return {
          '/study-pipeline-summary': stages
        }
      })
    ))
    super(rest, '', 'study-pipeline-summary')
  }

  _nullIfDash(s: string | undefined) {
    return s === '-' ? null : s
  }

}
