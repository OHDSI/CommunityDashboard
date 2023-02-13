import { Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
import { ScanLog, ScanLogsService } from './scan-logs.service';
import * as d3 from 'd3'

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
    private scanLogsService: ScanLogsService,
  ) {
    const stages: {[key: string]: PipelineStage} = {}
    const rest = new RestMemory({
      '/study-pipeline-summary': stages
    })
    super(rest, '', 'study-pipeline-summary')
    this.scanLogsService.cache.subscribe({
      next: (ls: any) => {
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
          const lastUpdate = new Date(new Date(commits[0].readmeCommit!.author.date))
          const status = commits[0].readmeCommit!.summary.status && VALID_STATUS.includes(commits[0].readmeCommit!.summary.status) ? commits[0].readmeCommit!.summary.status : 'Invalid / Suspended'
          for (const c of commits) {
            const newStatus = c.readmeCommit!.summary.status && VALID_STATUS.includes(c.readmeCommit!.summary.status) ? c.readmeCommit!.summary.status : 'Invalid / Suspended'
            const promotionDate = new Date(new Date(c.readmeCommit!.author.date))
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
      }
    })
  }

  _nullIfDash(s: string | undefined) {
    return s === '-' ? null : s
  }

  // find(): Observable<StudyPipelineStage[]> {
    // return this.scanLogsService.cache.pipe(
    //   map(ls => {
    //     const p: {[key: string]: any} = {
    //       "Repo Created": {
    //         stage: "Repo Created",
    //         'studies at stage': 0,
    //         'active studies at stage (last 30 days)': 0,
    //         'days since last update': [],
    //         'avg. days since last update': null,
    //       },
    //       "Started": {
    //         stage: "Started",
    //         'studies at stage': 0,
    //         'active studies at stage (last 30 days)': 0,
    //         'days since last update': [],
    //         'avg. days since last update': null,
    //       },
    //       "Design Finalized": {
    //         stage: "Design Finalized",
    //         'studies at stage': 0,
    //         'active studies at stage (last 30 days)': 0,
    //         'days since last update': [],
    //         'avg. days since last update': null,
    //       },
    //       "Results Available": {
    //         stage: "Results Available",
    //         'studies at stage': 0,
    //         'active studies at stage (last 30 days)': 0,
    //         'days since last update': [],
    //         'avg. days since last update': null,
    //       },
    //     }
    //     const average = (array: number[]) => array.reduce((a, b) => a + b) / array.length;
    //     const DAYS = 1000 * 3600 * 24
    //     const now = new Date()
    //     ls.forEach(l => {
    //       const stage = l.readmeCommit?.summary.status
    //       if (!stage) { return }
    //       if (!(stage in p)) { return }
    //       p[stage]['studies at stage'] += 1
    //       const updatedAt = new Date(l.repository!.updatedAt)
    //       const daysSinceLastUpdate = (now.getTime() - updatedAt.getTime()) / DAYS
    //       p[stage]['days since last update'].push(daysSinceLastUpdate)
    //       if (daysSinceLastUpdate < 90) {
    //         p[stage]['active studies at stage (last 30 days)'] += 1
    //       }
    //     })
    //     Object.values(p).forEach(s => {
    //       if(s['days since last update'].length) {
    //         s['avg. days since last update'] = average(s['days since last update'])
    //       }
    //     })
    //     return Object.values(p)
    //   })
    // )
  // }

}
