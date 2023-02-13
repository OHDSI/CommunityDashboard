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
    private scanLogsService: ScanLogsService,
  ) {
    const promotions: {[key: string]: StudyPromotion} = {}
    const rest = new RestMemory({
      '/study-promotions': promotions
    })
    super(rest, '', 'study-promotions')
    this.scanLogsService.cache.subscribe({
      next: (ls: any) => {
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
          const startDate = new Date(new Date(commits[0].readmeCommit!.author.date))
          let status = undefined
          for (const c of commits) {
            const newStatus = c.readmeCommit!.summary.status
            const newDate = new Date(new Date(c.readmeCommit!.author.date))
            if (newStatus !== status) {
              promotions[i] = {
                id: i.toString(),
                repoName,
                days: (newDate.getTime() - startDate.getTime()) / DAYS,
                stage: newStatus && VALID_STATUS.includes(newStatus) ? newStatus : 'Invalid / Suspended',
                tags: c.readmeCommit!.summary.tags || [],
                useCases: c.readmeCommit!.summary.useCases || [],
                studyType: c.readmeCommit!.summary.studyType || [],
              }
              status = newStatus
              i += 1
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
