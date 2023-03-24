import { Injectable } from '@angular/core';
import { IndexedDbDocs, Rest, RestDelegate, RestMemory, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { map, Observable, shareReplay } from 'rxjs';
import { ScanLog, ScanLogsService } from '../scan-logs.service';
import * as d3 from 'd3'

export const EXCEPTIONS: {[key: string]: string} = {
  MISSING_PROTOCOL: 'design finalized w/o protocol',
  MISSING_RESULTS: 'study completed w/o results',
  MISSING_LEAD: 'study has no lead',
  MISSING_STATUS: 'study has no status',
}

export interface StudyException {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id: number
  studyId: number
  studyRepo: string
  exception: keyof typeof EXCEPTIONS
}

@Injectable({
  providedIn: 'root'
})
export class StudyExceptionsService implements TableDataService<StudyException> {

  constructor(
    private studyExceptionsDb: StudyExceptionsDb,
  ) {}

  valueChanges(params?: TableQuery): Observable<StudyException[] | null> {
    return this.studyExceptionsDb.valueChanges({
      path: 'study-exceptions',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.studyExceptionsDb.count({
      path: 'study-exceptions',
      idField: 'id',
      ...params
    })
  }
}

@Injectable({
  providedIn: 'root'
})
class StudyExceptionsDb extends IndexedDbDocs {

  constructor(
    scanLogsService: ScanLogsService,
  ) {
    super({tables: scanLogsService.valueChanges().pipe(
      map(ls => ({'/study-exceptions': toStudyExceptions(ls)})),
      // shareReplay(1)
    )})
  }
    
}

function toStudyExceptions(ls: ScanLog[] | null): {[key:string]: StudyException} {
  if (!ls) {
    return {}
  }
  ls.sort((a, b) => d3.descending(a.readmeCommit?.author?.date, b.readmeCommit?.author?.date))
  const latestCommit = d3.rollup(ls, (v: ScanLog[]) => v[0], (d: ScanLog) => d.repository?.name)
  const studyExceptions: {[key: string]: any} = {}
  const allExceptions = [...latestCommit.values()].flatMap((l: any) => {
    const es = []
    if (
      !l.readmeCommit?.summary ||
      !l.readmeCommit?.summary.studyLead ||
      (l.readmeCommit && !l.readmeCommit.summary.studyLead.length) ||
      l.readmeCommit?.summary.studyLead.includes('-')
    ) {
      es.push({
        id: 0,
        studyId: 0,
        studyRepo: l.repository?.name,
        exception: 'MISSING_LEAD'
      })
    }
    const stage = l.readmeCommit?.summary?.status
    if (!stage) {
      es.push({
        id: 0,
        studyId: 0,
        studyRepo: l.repository?.name,
        exception: 'MISSING_STATUS'
      })
      return es
    }
    if (!([
      'Complete',
      'Suspended',
      'Repo Created',
      'Started',
      'Design Finalized',
      'Results Available',
    ].includes(stage))) {
      es.push({
        id: 0,
        studyId: 0,
        studyRepo: l.repository?.name,
        exception: 'MISSING_STATUS'
      })
    }
    if (
      (stage === 'Complete' || stage === 'Results Available') &&
      (!l.readmeCommit!.summary?.results || l.readmeCommit!.summary?.results === '-')
    ) {
      es.push({
        id: 0,
        studyId: 0,
        studyRepo: l.repository?.name,
        exception: 'MISSING_RESULTS'
      })
    }
    if (
      (stage === 'Complete' || stage === 'Results Available' || stage === 'Design Finalized') &&
      (!l.readmeCommit!.summary?.protocol || l.readmeCommit!.summary?.protocol === '-')
    ) {
      es.push({
        id: 0,
        studyId: 0,
        studyRepo: l.repository?.name,
        exception: 'MISSING_PROTOCOL'
      })
    }
    return es
  })
  let i = 0
  for (const e of allExceptions) {
    e.id = i
    studyExceptions[i] = e
    i += 1
  }
  return studyExceptions
}