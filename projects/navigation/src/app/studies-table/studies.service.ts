import { Injectable } from '@angular/core';
import { IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { ScanLog, ScanLogsService } from '../scan-logs.service';
import * as d3 from 'd3'
import { map, Observable, shareReplay} from 'rxjs';
import { ReadmeSummariesService, ReadmeSummary } from './readme-summaries.service';

export interface Study  {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id: string,
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
  lastUpdate: string | null,
  daysSinceStatusChange: number | null,
}

@Injectable({
  providedIn: 'root'
})
export class StudiesService implements TableDataService<Study> {

  constructor(
    private studiesDb: StudiesDb,
  ) {}

  valueChanges(params?: TableQuery): Observable<Study[] | null> {
    return this.studiesDb.valueChanges({
      path: 'studies',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.studiesDb.count({
      path: 'studies',
      idField: 'id',
      ...params
    })
  }
}

@Injectable({
  providedIn: 'root'
})
class StudiesDb extends IndexedDbDocs {

  constructor(
    readmeSummariesService: ReadmeSummariesService,
  ) {
    super({tables: readmeSummariesService.valueChanges().pipe(
      map(rs => ({'/studies': toStudies(rs)})),
      shareReplay(1)
    )})
  }
    
}

function toStudies(rs: ReadmeSummary[] | null): {[key:string]: Study} {
  if (!rs) {
    return {}
  }
  const now = new Date()
  // const studies: {[key: string]: Study} = {}
  const readmeCommits = rs
    .sort((a, b) => d3.descending(a.author.date, b.author.date))
  const byStudy: Map<string, ReadmeSummary[]> = d3.group(readmeCommits, (c: ReadmeSummary) => c.denormRepo.name)
  const studies = [...byStudy.entries()].reduce((acc, [repoName, cs]) => {
    if (cs[0].denormRepo.name === 'EmptyStudyRepository') {
      return acc
    }
    const l = getLastStatusChange(cs)
    const a = cs[0].author?.date
    const lastUpdate = a ?? null
    const b = l.author?.date
    const daysSinceStatusChange = b ? Math.floor(days(now.getTime() - (new Date(b)).getTime())) : null
    acc[repoName] = {
      id: repoName,
      title: cs[0].summary?.title,
      gitRepo: cs[0].denormRepo.name,
      status: cs[0].summary?.status,
      useCases: cs[0].summary?.useCases,
      type: cs[0].summary?.studyType,
      tags: cs[0].summary?.tags,
      lead: _nullIfDash(cs[0].summary?.studyLead) as string[],
      start: cs[0].summary?.startDate,
      end: cs[0].summary?.endDate,
      protocol: _nullIfDash(cs[0].summary?.protocol) as string,
      publications: cs[0].summary?.publications,
      results: _nullIfDash(cs[0].summary?.results) as string,
      lastUpdate,
      daysSinceStatusChange,
    }
    return acc
  }, {} as {[key:string]: Study})
  return studies
}

function getLastStatusChange(commits: ReadmeSummary[]): ReadmeSummary {
  const s = commits[0].summary?.status
  const l = commits.find(c => c.summary?.status !== s)
  if (!l) {
    return commits[commits.length - 1]
  }
  return l
}

function days(milliseconds: number) {
  const seconds = milliseconds / 1000
  const minutes = seconds / 60
  const hours = minutes / 60
  return hours / 24
}

function _nullIfDash(s: string | undefined | null | string[]) {
  if (s === '-') {
    return null
  }
  if (s instanceof Array && s[0] === '-') {
    return null
  }
  return s
}