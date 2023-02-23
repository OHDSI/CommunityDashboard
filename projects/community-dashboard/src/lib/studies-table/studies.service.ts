import { Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
import { ScanLog, ScanLogsService } from '../scan-logs.service';
import * as d3 from 'd3'
import { map } from 'rxjs';

export interface Study  {
  id: number,
  title?: string | null,
  gitRepo: string | null,
  status?: string | null,
  useCases?: string[] | null,
  type?: string[] | null,
  tags?: string[] | null,
  lead?: string[] | null,
  start?: string | null,
  end?: string | null,
  protocol?: string | null,
  publications?: string | null,
  results?: string | null,
  lastUpdate: Date | null,
}

@Injectable({
  providedIn: 'root'
})
export class StudiesService extends RestDelegate<Study> {

  constructor(
    scanLogsService: ScanLogsService,
  ) {
    
    const rest = new RestMemory(scanLogsService.cache.pipe(
      map((ls: any) => {
        const studies: {[key: string]: Study} = {}
        const readmeCommits = ls.filter((l: any) => l.readmeCommit)
          // .map(c => {
          //   (c as any).readmeCommit!.author.date = new Date(c.readmeCommit!.author.date)
          // })
          .sort((a: any, b: any) => d3.descending(a.readmeCommit!.author.date, b.readmeCommit!.author.date))
        const byStudy = d3.group(readmeCommits, (c: ScanLog) => c.readmeCommit!.repoName) as {values: () => ScanLog[][]}
        let i = 0
        for (const commits of byStudy.values()) {
          const authorDate = commits[0].readmeCommit!.author?.date
          studies[i] = {
            id: i,
            title: commits[0].readmeCommit!.summary?.title,
            gitRepo: commits[0].readmeCommit!.repoName,
            status: commits[0].readmeCommit!.summary?.status,
            useCases: commits[0].readmeCommit!.summary?.useCases,
            type: commits[0].readmeCommit!.summary?.studyType,
            tags: commits[0].readmeCommit!.summary?.tags,
            lead: commits[0].readmeCommit!.summary?.studyLeads,
            start: commits[0].readmeCommit!.summary?.startDate,
            end: commits[0].readmeCommit!.summary?.endDate,
            protocol: this._nullIfDash(commits[0].readmeCommit!.summary?.protocol),
            publications: commits[0].readmeCommit!.summary?.publications,
            results: this._nullIfDash(commits[0].readmeCommit!.summary?.results),
            lastUpdate: authorDate ? new Date(authorDate) : null
          }
          i += 1
        }
        return {
          '/studies': studies
        }
      })
    ))
    super(rest, '', 'studies')
  }

  _nullIfDash(s: string | undefined | null) {
    return s === '-' ? null : s
  }

}
