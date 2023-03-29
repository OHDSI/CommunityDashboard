import { Injectable } from '@angular/core';
import { IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { BehaviorSubject, combineLatest, first, from, map, Observable, switchMap, tap } from 'rxjs';
import * as d3 from 'd3'

const PHENOTYPE_LIB_URL = 'https://raw.githubusercontent.com/OHDSI/PhenotypeLibrary/main/inst/Cohorts.csv'

export interface Phenotype {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "cohortId": string
  "cohortName": string
  "description": string
  "createdDate": string
  "modifiedDate": string
  "librarian": string
  "cohortNameFormatted": string
  "lastModifiedBy": string
  "status": string
  "logicDescription": string
  "hashTag": string[]
  "contributor": string
  "Forum": string
  "addedVersion": string
  "peer": string
  "Reviewer": string
}

@Injectable({
  providedIn: 'root'
})
export class PhenotypeService implements TableDataService<Phenotype> {

  search = this.phenotypeDb.search
  hashtags = this.phenotypeDb.hashtags
  status = this.phenotypeDb.status
  filterStatus = new BehaviorSubject<string|null>(null)
  filterHash = new BehaviorSubject<string[]|null>(null)
  filters = combineLatest([this.filterStatus, this.filterHash])

  constructor(
    private phenotypeDb: PhenotypeDb
  ) {}

  valueChanges(params?: TableQuery): Observable<Phenotype[] | null> {
    return this.filters.pipe(
      switchMap(([s, h]) => {
        const p = updateParams(s, h, params)
        return this.phenotypeDb.valueChanges({
          path: 'phenotypes',
          idField: 'cohortId',
          ...p
        }) as Observable<Phenotype[] | null>
      })
    )
  }

  count(params?: TableQuery): Observable<number> {
    return this.filters.pipe(
      switchMap(([s, h]) => {
        const p = updateParams(s, h, params)
        return this.phenotypeDb.count({
          path: 'phenotypes',
          idField: 'cohortId',
          ...p
        }) as Observable<number>
      })
    )
  }

}

function updateParams(s: string|null, hs: string[]|null, params?: TableQuery): TableQuery {
  const p: TableQuery = {...params}
  if (s || hs) {
    p.where = []
  }
  if (s) {
    p.where!.push(['status', '==', s])
  }
  if (hs) {
    for (const h of hs) {
      p.where!.push(['hashTag', 'array-contains', h])
    }
  }
  return p
}

@Injectable({
  providedIn: 'root'
})
class PhenotypeDb extends IndexedDbDocs {

  hashtags: Observable<Set<string>>
  status: Observable<Set<string>>
  search: BehaviorSubject<string>

  constructor(
  ) {
    const search = new BehaviorSubject('')
    const tables = combineLatest([
      getPhenotypes(),
      search
    ]).pipe(
      map(([ps, s]) => searchQuery(ps, s)),
      map(ps => ({'/phenotypes': ps.reduce((acc, p) => {
        acc[p.cohortId] = p
        return acc
      }, {} as {[key: string]: Phenotype})}))
    )
    super({tables})
    this.search = search
    this.hashtags = tables.pipe(
      map(ts => {
        return Object.values(ts['/phenotypes']).reduce((acc, p) => {
          for (const h of p.hashTag) {
            acc.add(h)
          }
          return acc
        }, new Set<string>())
      }),
      tap(hs => {console.log(hs)})
    )
    this.status = tables.pipe(
      map(ts => {
        return Object.values(ts['/phenotypes']).reduce((acc, p) => {
          acc.add(p.status)
          return acc
        }, new Set<string>())
      })
    )
  }
    
}

function getPhenotypes(): Observable<Phenotype[]> {
  return from(d3.csv(PHENOTYPE_LIB_URL)).pipe(
    map((rows) => {
      const phenotypes: Phenotype[] = []
      for (const r of rows as {[key: string]: any}[]) {
        const p = {...r, hashTag: r['hashTag'].split(',').map((h: string) => h.trim())} as Phenotype
        phenotypes.push(p)
      }
      return phenotypes
    })
  )
}

function searchQuery(ps: Phenotype[], s: string) {
  return s === '' ? ps : ps.filter(p => p.cohortName.toLowerCase().includes(s.toLowerCase()))
}