import { Injectable } from '@angular/core';
import { IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { BehaviorSubject, combineLatest, first, from, map, Observable, switchMap, tap } from 'rxjs';
import * as d3 from 'd3'

const CSV_URL = 'https://raw.githubusercontent.com/OHDSI/CommunityDashboard/main/test/exports/OHDSI_funding_opportunities.csv'

export interface FundingOp {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id": string,
  "DATE ADDED": string
  "LOCATION FOUND": string
  "FUNDING OPPORTUNITY NUMBER & TITLE": string
  "AGENCY": string
  "OPPORTUNITY DETAILS": string
  "OPPORTUNITY LINK": string
  "BUDGET": string
  "NUMBER YEARS": string
  "SUBMISSION DEADLINE(S) IN 2023": string
  "": string
}

@Injectable({
  providedIn: 'root'
})
export class FundingOpsService implements TableDataService<FundingOp> {

  search = this.fundingDbSearchable.search

  constructor(
    private fundingDbSearchable: InMemoryDb
  ) {}

  valueChanges(params?: TableQuery): Observable<FundingOp[] | null> {
    return this.fundingDbSearchable.valueChanges({
      path: 'funding',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.fundingDbSearchable.count({
      path: 'funding',
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
      map(([fs, s]) => searchQuery(fs, s)),
      map(fs => ({'/funding': fs.reduce((acc, f, i) => {
        const id = `${i}`
        f.id = id
        acc[id] = f
        return acc
      }, {} as {[key: string]: FundingOp})}))
    )
    super({tables})
    this.search = search
  }
    
}

function getCsv(): Observable<FundingOp[]> {
  return from(d3.csv(CSV_URL) as Promise<FundingOp[]>)
}

function searchQuery(fs: FundingOp[], s: string) {
  return fs.filter(f => {
    return f['LOCATION FOUND'].toLowerCase().includes(s.toLowerCase()) ||
      f['FUNDING OPPORTUNITY NUMBER & TITLE'].toLowerCase().includes(s.toLowerCase()) ||
      f['AGENCY'].toLowerCase().includes(s.toLowerCase()) ||
      f['OPPORTUNITY DETAILS'].toLowerCase().includes(s.toLowerCase())
  })
}