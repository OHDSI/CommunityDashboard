import { Injectable } from '@angular/core';
import { IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { combineLatest, from, map, Observable } from 'rxjs';
import * as d3 from 'd3'

const CSV_URL = 'https://raw.githubusercontent.com/OHDSI/CommunityDashboard/main/test/exports/OHDSI_call_for_papers_opportunities.csv'

export interface CfpOp {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id": string,
  "DATE ADDED": string
  "OPPORTUNITY LINK": string
  "JOURNAL": string
  "THEME": string
  "SUBMISSION DEADLINE": string
}

@Injectable({
  providedIn: 'root'
})
export class CfpOpsService implements TableDataService<CfpOp> {

  constructor(
    private db: InMemoryDb
  ) {}

  valueChanges(params?: TableQuery): Observable<CfpOp[] | null> {
    return this.db.valueChanges({
      path: 'cfp',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.db.count({
      path: 'cfp',
      idField: 'id',
      ...params
    })
  }

}

@Injectable({
  providedIn: 'root'
})
class InMemoryDb extends IndexedDbDocs {

  constructor(
  ) {
    const tables = combineLatest([
      getCsv(),
    ]).pipe(
      map(([fs]) => fs),
      map(fs => ({'/cfp': fs.reduce((acc, c, i) => {
        const id = `${i}`
        c.id = id
        acc[id] = c
        return acc
      }, {} as {[key: string]: CfpOp})}))
    )
    super({tables})
  }
    
}

function getCsv(): Observable<CfpOp[]> {
  return from(d3.csv(CSV_URL) as Promise<CfpOp[]>)
}