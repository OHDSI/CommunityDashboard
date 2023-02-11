import { Injectable } from '@angular/core';
import { combineLatest, map, Observable } from 'rxjs';
import { StudiesService } from './studies-table/studies.service';
import { StudyExceptionSummariesService } from './study-exceptions-table/study-exception-summaries.service';

export interface StudySummary {
  name: string,
  value: number,
}

@Injectable({
  providedIn: 'root'
})
export class StudySumariesService {

  constructor(
    private studiesService: StudiesService,
    private studyExceptionSummariesService: StudyExceptionSummariesService,
  ) {}

  find(): Observable<StudySummary[]> {
    return combineLatest([
      this.studiesService.find(),
      this.studyExceptionSummariesService.find(),
    ]).pipe(
      map(([ss, es]) => {
        const summary: {[key: string]: any} = {
          'In Progress': {
            name: 'In Progress',
            value: 0,
          },
          'Complete': {
            name: 'Complete',
            value: 0,
          },
          'Suspended': {
            name: 'Suspended',
            value: 0,
          },
          'Exceptions': {
            name: 'Exceptions',
            value: 0,
          },
        }
        es.forEach(e => {
          summary['Exceptions'].value += e.count
        })
        ss.forEach(s => {
          const stage = s.status
          if (!stage) { return }
          if ([
            'Repo Created',
            'Started',
            'Design Finalized',
            'Results Available',
          ].includes(stage)) {
            summary['In Progress'].value += 1
          }
          if (stage === 'Complete') {
            summary['Complete'].value += 1
          }
          if (stage === 'Suspended') {
            summary['Suspended'].value += 1
          }
        })
        return Object.values(summary)
      })
    )
  }
}
