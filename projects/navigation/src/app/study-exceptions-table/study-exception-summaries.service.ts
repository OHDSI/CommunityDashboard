import { Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';
import { ScanLogsService, Status } from '../scan-logs.service';
import { StudiesService } from '../studies-table/studies.service';
import { EXCEPTIONS } from './study-exceptions.service';

export interface StudyExceptionSummary {
  id: number
  exception: keyof typeof EXCEPTIONS,
  count: number,
}

@Injectable({
  providedIn: 'root'
})
export class StudyExceptionSummariesService {

  constructor(
    private studiesService: StudiesService,
  ) {}

  find(): Observable<StudyExceptionSummary[]> {
    return this.studiesService.find().pipe(
      map(ss => {
        const e: {[key: string]: any} = {
          'MISSING_PROTOCOL': {
            id: 0,
            exception: 'MISSING_PROTOCOL',
            count: 0,
          },
          'MISSING_RESULTS': {
            id: 1,
            exception: 'MISSING_RESULTS',
            count: 0,
          },
          'MISSING_LEAD': {
            id: 2,
            exception: 'MISSING_LEAD',
            count: 0,
          },
          'MISSING_STATUS': {
            id: 3,
            exception: 'MISSING_STATUS',
            count: 0,
          },
        }
        ss.forEach(s => {
          if (
            !s.lead ||
            s.lead.includes('-')
          ) {
            e['MISSING_LEAD'].count += 1
          }
          const stage = s.status
          if (!stage) {
            e['MISSING_STATUS'].count += 1
            return 
          }
          if (!([
            'Complete',
            'Suspended',
            'Repo Created',
            'Started',
            'Design Finalized',
            'Results Available',
          ].includes(stage))) {
            e['MISSING_STATUS'].count += 1
          }
          if (
            (stage === 'Complete' || stage === 'Results Available') &&
            (!s.results || s.results === '-')
          ) {
            e['MISSING_RESULTS'].count += 1
          }
          if (
            (stage === 'Complete' || stage === 'Results Available' || stage === 'Design Finalized') &&
            (!s.protocol || s.protocol === '-')
          ) {
            e['MISSING_PROTOCOL'].count += 1
          }
        })
        return Object.values(e)
      })
    )
  }

}
