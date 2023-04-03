import { Injectable } from '@angular/core';
import { IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { BehaviorSubject, combineLatest, first, from, map, Observable, switchMap, tap } from 'rxjs';
import * as d3 from 'd3'

const CSV_URL = 'https://raw.githubusercontent.com/OHDSI/CommunityDashboard/main/test/exports/OHDSI_event_opportunities.csv'

export interface EventOp {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id": string
  "DATE ADDED": string
  "WEB LINK": string
  "SPONSOR(S)": string
  "NAME": string
  "EVENT DATE(S)": string
  "LOCATION(S)": string
  "PRESNTAION SUBMISSION DEADLINE": string
  "REGISTRATION DEADLINE": string
}

@Injectable({
  providedIn: 'root'
})
export class EventOpsService implements TableDataService<EventOp> {

  search = this.db.search

  constructor(
    private db: InMemoryDb
  ) {}

  valueChanges(params?: TableQuery): Observable<EventOp[] | null> {
    return this.db.valueChanges({
      path: 'event',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.db.count({
      path: 'event',
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
      map(([es, s]) => searchQuery(es, s)),
      map(es => ({'/event': es.reduce((acc, e, i) => {
        const id = `${i}`
        e.id = id
        acc[id] = e
        return acc
      }, {} as {[key: string]: EventOp})}))
    )
    super({tables})
    this.search = search
  }
    
}

function getCsv(): Observable<EventOp[]> {
  return from(d3.csv(CSV_URL) as Promise<EventOp[]>)
}

function searchQuery(es: EventOp[], s: string) {
  return es.filter(e => {
    return e['SPONSOR(S)'].toLowerCase().includes(s.toLowerCase()) ||
      e['NAME'].toLowerCase().includes(s.toLowerCase()) ||
      e['LOCATION(S)'].toLowerCase().includes(s.toLowerCase())
  })}