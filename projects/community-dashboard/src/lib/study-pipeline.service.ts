import { ErrorHandler, Injectable } from '@angular/core';
import { Filter, RestDelegate, RestMemory } from '@community-dashboard/rest';
import { ScanLog, ScanLogsService } from './scan-logs.service';
import * as d3 from 'd3'
import { concatMap, map, Observable } from 'rxjs';

export interface StudyPipelineStage {
  id: number,
  stage: string,
  'studies at stage': number,
  'active studies at stage (last 30 days)': number,
  'avg. days since last update': number,
}

export interface StudyPromotion {
  id: string,
  repoName: string,
  days: number,
  stage: string,
  tags: string[],
  useCases: string[],
  studyType: string[],
}

@Injectable({
  providedIn: 'root'
})
export class StudyPipelineService extends RestDelegate<StudyPromotion> {

  constructor(
    scanLogsService: ScanLogsService,
    errorHandler: ErrorHandler,
  ) {
    const rest = new RestMemory(scanLogsService.cache.pipe(
      map((ls: any) => {
        const promotions: {[key: string]: StudyPromotion} = {}
        const readmeCommits = ls.filter((l: any) => l.readmeCommit)
          .sort((a: any, b: any) => d3.ascending(a.readmeCommit!.author.date, b.readmeCommit!.author.date))
        const byStudy = d3.group(readmeCommits, (c: ScanLog) => c.readmeCommit!.repoName) as Map<string, ScanLog[]>
        const DAYS = 1000 * 3600 * 24
        const VALID_STATUS = [
          'Repo Created',
          'Started',
          'Design Finalized',
          'Results Available',
          'Complete',
        ]
        let i = 0
        for (const [repoName, commits] of byStudy.entries()) {
          const startAuthorDate = commits[0].readmeCommit!.author?.date
          if (!startAuthorDate) {
            errorHandler.handleError('first commit has no author date')
            continue
          }
          const startDate = new Date(new Date(startAuthorDate))
          let status = undefined
          for (const c of commits) {
            const newStatus = c.readmeCommit!.summary?.status
            const newAuthorDate = c.readmeCommit!.author?.date
            if (!newAuthorDate) {
              errorHandler.handleError('new commit has no author date')
            continue
            }
            const newDate = new Date(new Date(newAuthorDate))
            if (newStatus !== status) {
              promotions[i] = {
                id: i.toString(),
                repoName,
                days: (newDate.getTime() - startDate.getTime()) / DAYS,
                stage: newStatus && VALID_STATUS.includes(newStatus) ? newStatus : 'Invalid / Suspended',
                tags: c.readmeCommit!.summary?.tags || [],
                useCases: c.readmeCommit!.summary?.useCases || [],
                studyType: c.readmeCommit!.summary?.studyType || [],
              }
              status = newStatus
              i += 1
            }
          }
        }
        return {
          '/study-promotions': promotions
        }
      })
    ))
    super(rest, '', 'study-promotions')
  }

  _nullIfDash(s: string | undefined) {
    return s === '-' ? null : s
  }

}
