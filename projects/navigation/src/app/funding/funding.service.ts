import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, Id, index, IndexedDbDocs, Rest, RestDelegate, RestToken, TableDataService, TableFieldValue, TableQuery, TableQueryWhere, TableQueryWhereArray } from '@community-dashboard/rest';
import { combineLatest, shareReplay } from 'rxjs';
import { BehaviorSubject, map, Observable } from 'rxjs';

export interface Funding {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id": Id,
  "DATE ADDED": string,
  "LOCATION FOUND": string,
  "LOCATION FOUND 2": string,
  "AGENCY": string,
  "OPPORTUNITY DETAILS": string,
  "OPPORTUNITY LINK": string,
  "BUDGET": string,
  "NUMBER YEARS": string,
  "SUBMISSION DEADLINE(S) IN 2023": string,
}

@Injectable({
  providedIn: 'root'
})
export class FundingService extends DocsTableDataService<Funding> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) {
    super({docs, path: 'funding', idField: 'id'})
  }

}

@Injectable({
  providedIn: 'root'
})
export class FundingServiceSearchable implements TableDataService<Funding> {

  search: BehaviorSubject<string>

  constructor(
    private fundingDbSearchable: FundingDbSearchable
  ) {
    this.search = this.fundingDbSearchable.search
  }

  valueChanges(params?: TableQuery): Observable<Funding[] | null> {
    return this.fundingDbSearchable.valueChanges({
      path: 'fundingDbSearchable',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.fundingDbSearchable.count({
      path: 'fundingDbSearchable',
      idField: 'id',
      ...params
    })
  }

}

@Injectable({
  providedIn: 'root'
})
class FundingDbSearchable extends IndexedDbDocs {

  search: BehaviorSubject<string>

  constructor(
    fundingService: FundingService
  ) {
    const search = new BehaviorSubject<string>('')
    super({tables: combineLatest([
      fundingService.valueChanges(),
      search
    ]).pipe(
      map(([fs, s]) => {
        if (!fs) {
          return {'/fundingDbSearchable': {}}
        }
        if (s.length) {
          return {'/fundingDbSearchable': index(searchQuery(fs, s.toLowerCase()))}
        }
        return {'/fundingDbSearchable': index(fs)}
      }),
      shareReplay(1)
    )})
    this.search = search
  }
    
}

function searchQuery(fs: Funding[], s: string) {
  return fs.filter(f => {
    return f['LOCATION FOUND'].toLowerCase().includes(s.toLowerCase()) ||
      f['LOCATION FOUND 2'].toLowerCase().includes(s.toLowerCase()) ||
      f['AGENCY'].toLowerCase().includes(s.toLowerCase()) ||
      f['OPPORTUNITY DETAILS'].toLowerCase().includes(s.toLowerCase())
  })
}