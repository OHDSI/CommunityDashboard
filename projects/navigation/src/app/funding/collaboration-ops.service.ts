import { Injectable } from '@angular/core';
import { IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { BehaviorSubject, combineLatest, first, from, map, Observable, switchMap, tap } from 'rxjs';
import * as d3 from 'd3'

const CSV_URL = 'https://raw.githubusercontent.com/OHDSI/CommunityDashboard/main/test/exports/OHDSI_collaboration_opportunities.csv'

export interface CollaborationOp {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id": string,
  "DATE ADDED": string
  "LOCATION FOUND": string
  "title": string
  "AGENCY": string
  "OPPORTUNITY DETAILS": string
}

@Injectable({
  providedIn: 'root'
})
export class CollaborationOpsService implements TableDataService<CollaborationOp> {

  search = this.db.search

  constructor(
    private db: InMemoryDb
  ) {}

  valueChanges(params?: TableQuery): Observable<CollaborationOp[] | null> {
    return this.db.valueChanges({
      path: 'collaborations',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.db.count({
      path: 'collaborations',
      idField: 'id',
      ...params
    })
  }

}

@Injectable({
  providedIn: 'root'
})
class InMemoryDb extends IndexedDbDocs {

  search: BehaviorSubject<string>

  constructor(
    ) {
      const search = new BehaviorSubject('')
      const tables = combineLatest([
        getCsv(),
        search
      ]).pipe(
        map(([cs, s]) => searchQuery(cs, s)),
        map(cs => ({'/collaborations': cs.reduce((acc, c, i) => {
          const id = `${i}`
          c.id = id
          acc[id] = c
          return acc
        }, {} as {[key: string]: CollaborationOp})}))
      )
      super({tables})
      this.search = search
    }
    
}

function getCsv(): Observable<CollaborationOp[]> {
  return from(d3.csv(CSV_URL) as Promise<CollaborationOp[]>).pipe(
    map(rows => {
      return rows.map(r => {
        r['title'] = r['OPPORTUNITY NUMBER          & TITLE'] as string
        return r
      })
    }),
  )
}

function searchQuery(cs: CollaborationOp[], s: string) {
  return cs.filter(f => {
    return f['LOCATION FOUND'].toLowerCase().includes(s.toLowerCase()) ||
      f['title'].toLowerCase().includes(s.toLowerCase()) ||
      f['AGENCY'].toLowerCase().includes(s.toLowerCase()) ||
      f['OPPORTUNITY DETAILS'].toLowerCase().includes(s.toLowerCase())
  })
}