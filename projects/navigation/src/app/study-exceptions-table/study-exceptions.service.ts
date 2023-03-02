import { Injectable } from '@angular/core';
import { Rest, RestDelegate, RestMemory } from '@community-dashboard/rest';
import { map } from 'rxjs';
import { ScanLogsService } from '../scan-logs.service';

export const EXCEPTIONS: {[key: string]: string} = {
  MISSING_PROTOCOL: 'design finalized w/o protocol',
  MISSING_RESULTS: 'study completed w/o results',
  MISSING_LEAD: 'study has no lead',
  MISSING_STATUS: 'study has no status',
}

export interface StudyException {
  id: number
  studyId: number
  studyRepo: string
  exception: keyof typeof EXCEPTIONS
}

@Injectable({
  providedIn: 'root'
})
export class StudyExceptionsService extends RestDelegate<StudyException> {

  constructor(
    scanLogsService: ScanLogsService,
  ) {
    const rest = new RestMemory(scanLogsService.cache.pipe(
      map((ls: any) => {
        const studyExceptions: {[key: string]: any} = {}
        const allExceptions = ls.flatMap((l: any) => {
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
          studyExceptions[i] = e
          i += 1
        }
        return studyExceptions
      }),
      map(studyExceptions => ({
        '/study-exceptions': studyExceptions
      }))
    ))
    super(rest, '', 'study-exceptions')
  }

}
