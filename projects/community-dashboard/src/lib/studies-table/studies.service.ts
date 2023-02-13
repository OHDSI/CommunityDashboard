import { Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
import { ScanLog, ScanLogsService } from '../scan-logs.service';
import * as d3 from 'd3'

export interface Study  {
  id: number,
  title?: string,
  gitRepo: string | null,
  status?: string,
  useCases?: string[],
  type?: string[],
  tags?: string[],
  lead?: string[],
  start?: string | null,
  end?: string | null,
  protocol?: string | null,
  publications?: string | null,
  results?: string | null,
  lastUpdate: Date,
}

@Injectable({
  providedIn: 'root'
})
export class StudiesService extends RestDelegate<Study> {

  constructor(
    private scanLogsService: ScanLogsService,
  ) {
    const studies: {[key: string]: Study} = {}
    const rest = new RestMemory({
      '/studies': studies
    })
    super(rest, '', 'studies')
    this.scanLogsService.cache.subscribe({
      next: (ls: any) => {
        const readmeCommits = ls.filter((l: any) => l.readmeCommit)
          // .map(c => {
          //   (c as any).readmeCommit!.author.date = new Date(c.readmeCommit!.author.date)
          // })
          .sort((a: any, b: any) => d3.descending(a.readmeCommit!.author.date, b.readmeCommit!.author.date))
        const byStudy = d3.group(readmeCommits, (c: ScanLog) => c.readmeCommit!.repoName) as {values: () => ScanLog[][]}
        let i = 0
        for (const commits of byStudy.values()) {
          studies[i] = {
            id: i,
            title: commits[0].readmeCommit!.summary.title,
            gitRepo: commits[0].readmeCommit!.repoName,
            status: commits[0].readmeCommit!.summary.status,
            useCases: commits[0].readmeCommit!.summary.useCases,
            type: commits[0].readmeCommit!.summary.studyType,
            tags: commits[0].readmeCommit!.summary.tags,
            lead: commits[0].readmeCommit!.summary.studyLead,
            start: commits[0].readmeCommit!.summary.startDate,
            end: commits[0].readmeCommit!.summary.endDate,
            protocol: this._nullIfDash(commits[0].readmeCommit!.summary.protocol),
            publications: commits[0].readmeCommit!.summary.publications,
            results: this._nullIfDash(commits[0].readmeCommit!.summary.results),
            lastUpdate: new Date(commits[0].readmeCommit!.author.date)
          }
          i += 1
        }
      }
    })
  }

  _nullIfDash(s: string | undefined) {
    return s === '-' ? null : s
  }

}
