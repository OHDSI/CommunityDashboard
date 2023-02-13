import { Injectable } from '@angular/core';
import { RestDelegate, RestMemory } from '@community-dashboard/rest';
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
    private studiesService: StudiesService,
  ) {
    const leads: {[key: string]: any} = {}
    const rest = new RestMemory({
      '/study-leads': leads
    })
    super(rest, '', 'study-leads')
    this.studiesService.find().subscribe(
      ss => {
        const DAYS = 1000 * 3600 * 24
        const now = new Date()
        ss.forEach(s => {
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
            const updatedAt = new Date(s.lastUpdate)
            const daysSinceLastUpdate = (now.getTime() - updatedAt.getTime()) / DAYS
            if (daysSinceLastUpdate < 90) {
              leads[lead].active += 1
            }
          }
        })
      }
    )
  }

}
