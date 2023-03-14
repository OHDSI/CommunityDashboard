import { ErrorHandler, Injectable } from '@angular/core';
import { IndexedDbDocs, TableDataService, TableFieldValue } from '@community-dashboard/rest';
import * as d3 from 'd3'
import { map, Observable, shareReplay } from 'rxjs';
import { ReadmeSummariesService, ReadmeSummary } from './studies-table/readme-summaries.service';
import { TableQuery } from 'projects/rest/src/public-api';

// export interface StudyPipelineStage {
//   id: number,
//   stage: string,
//   'studies at stage': number,
//   'active studies at stage (last 30 days)': number,
//   'avg. days since last update': number,
// }

const DAYS = 1000 * 3600 * 24
const VALID_STATUS = [
  'Repo Created',
  'Started',
  'Design Finalized',
  'Results Available',
  'Complete',
]

export interface StudyPromotion {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
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
export class StudyPipelineService implements TableDataService<StudyPromotion> {

  constructor(
    private studyPromotionsDb: StudyPromotionsDb,
  ) {}

  valueChanges(params?: TableQuery): Observable<StudyPromotion[] | null> {
    return this.studyPromotionsDb.valueChanges({
      path: 'studyPromotions',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.studyPromotionsDb.count({
      path: 'studyPromotions',
      idField: 'id',
      ...params
    })
  }

}

@Injectable({
  providedIn: 'root'
})
class StudyPromotionsDb extends IndexedDbDocs {

  constructor(
    readmeSummariesService: ReadmeSummariesService,
    errorHandler: ErrorHandler,
  ) {
    super({tables: readmeSummariesService.valueChanges().pipe(
      map(rs => ({'/studyPromotions': toStudyPromotions(rs, errorHandler)})),
      shareReplay(1)
    )})
  }
    
}

function toStudyPromotions(rs: ReadmeSummary[] | null, errorHandler: ErrorHandler): {[key: string]: StudyPromotion} {
  if (!rs) {
    return {}
  }
  const readmeCommits = rs
    .sort((a, b) => d3.ascending(a.author.date, b.author.date))
  const byStudy: Map<string, ReadmeSummary[]> = d3.group(readmeCommits, (c: ReadmeSummary) => c.denormRepo.name)
  let i = 0
  const promotions = [...byStudy.entries()].reduce((acc, [repoName, cs]) => {
    if (cs[0].denormRepo.name === 'EmptyStudyRepository') {
      return acc
    }
    const startAuthorDate = cs[0].author?.date
    if (!startAuthorDate) {
      errorHandler.handleError('first commit has no author date')
      return acc
    }
    const startDate = new Date(new Date(startAuthorDate))
    let status = undefined
    for (const c of cs) {
      const newStatus = c.summary?.status
      const newAuthorDate = c.author?.date
      if (!newAuthorDate) {
        errorHandler.handleError('new commit has no author date')
        continue
      }
      const newDate = new Date(new Date(newAuthorDate))
      if (newStatus !== status) {
        acc[i.toString()] = {
          id: i.toString(),
          repoName,
          days: (newDate.getTime() - startDate.getTime()) / DAYS,
          stage: newStatus && VALID_STATUS.includes(newStatus) ? newStatus : 'Invalid / Suspended',
          tags: c.summary?.tags || [],
          useCases: c.summary?.useCases || [],
          studyType: c.summary?.studyType || [],
        }
        status = newStatus
        i += 1
      }
    }
    return acc
  }, {} as {[key:string]: StudyPromotion})
  return promotions
}
