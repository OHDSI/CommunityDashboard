import { Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
import { first, map } from 'rxjs';
import { StudiesService } from '../studies-table/studies.service';

export interface StudyLead {
  id: number,
  name: string,
  active: number,
  completed: number,
}

@Injectable({
  providedIn: 'root'
})
export class StudyLeadsService extends RestDelegate<StudyLead> {

  constructor(
    studiesService: StudiesService,
  ) {
    const rest = new RestMemory(studiesService.valueChanges().pipe(
      first(),
      map(ss => {
        const leads: {[key: string]: any} = {}
        const DAYS = 1000 * 3600 * 24
        const now = new Date()
        ss!.forEach(s => {
          const studyLeads = s.lead
          if (!studyLeads) { return }
          for (const lead of studyLeads) {
            if (!(lead in leads)) {
              leads[lead] = {
                name: lead,
                active: 0,
                completed: 0,
              }
            }
            leads[lead].completed += 1
            const updatedAt = s.lastUpdate ? new Date(s.lastUpdate) : null
            const daysSinceLastUpdate = updatedAt ? (now.getTime() - updatedAt.getTime()) / DAYS : null
            if (daysSinceLastUpdate !== null && daysSinceLastUpdate < 90) {
              leads[lead].active += 1
            }
          }
        })
        return leads
      }),
      map(leads => ({
        '/study-leads': leads
      }))
    ))
    super(rest, '', 'study-leads')
  }

}
