import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, DocsToken, index, IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { BehaviorSubject, combineLatest, map, Observable, shareReplay } from 'rxjs';
import * as d3 from 'd3';

export interface Publication {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "pmcID": string,
  "pubmedID": string,
  "nlmID": string,
  "journalTitle": string,
  "title": string,
  "creationDate": string,
  "affiliation": string,
  "locID": string,
  "countryOfPub": string,
  "language": string,
  "grantNum": string,
  "fullAuthor": string,
  "meshT": string,
  "source": string,
  "fullAuthorEdited": string,
  "firstAuthor": string,
  "pubYear": number,
  "titleAuthorStr": string,
  "datePulled": string,
  "foundInGooScholar": string,
  "numCitations": number,
  "levenProb": string,
  "fullAuthorGooScholar": string,
  "googleScholarLink": string,
  "rxnormIDspacy": string,
  "rxnormTermspacy": string,
  "rxnormStartChar": string,
  "rxnormEndChar": string,
  "umlsIDspacy": string,
  "umlsTermspacy": string,
  "umlsStartChar": string,
  "umlsEndChar": string,
  "snomedIDs": string,
  "snomedNames": string,
  "termFreq": string
}

export interface PublicationSummary {
  year: Date,
  n: number,
  cumulativeCitations: number
}

@Injectable({
  providedIn: 'root'
})
export class PubmedService extends DocsTableDataService<Publication> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) {
    super({docs, path: 'pubmedArticles', idField: 'pubmedID'})
  }

  summary(): Observable<PublicationSummary[]> {
    return this.valueChanges().pipe(
      map(ps => {
        if (!ps) {
          return []
        }
        const r: Map<Date, {n: number, nCitations: number}> = d3.rollup(
          ps.sort((a, b) => d3.ascending(a.pubYear, b.pubYear)), 
          (v: Publication[]) => ({
            n: v.length,
            nCitations: d3.sum(v, (d: Publication) => d.numCitations)
          }),
          (d: Publication) => new Date(d.pubYear, 0)
        )
        const ys = Array.from(r.entries()).map(([year, summary]) => ({year, ...summary}))
        const publicationSummaries = (Array.from(d3.cumsum(ys.map(y => y.nCitations))) as number[]).map((c, i) => {
          return {...ys[i], cumulativeCitations: c}
        })
        return publicationSummaries
      })
    )
  }

  totalAuthors(): Observable<number> {
    return this.valueChanges().pipe(
      map(ps => {
        if (!ps) {
          return 0
        }
        const authors = ps.reduce((acc, p) => {
          p.fullAuthorEdited.slice(1, p.fullAuthor.length - 1).split("' '").forEach(s => acc.add(s))
          return acc
        }, new Set())
        return authors.size
      })
    )
  }

  totalManuscripts(): Observable<number> {
    return this.valueChanges().pipe(
      map(ps => {
        if (!ps) {
          return 0
        }
        return ps.length
      })
    )
  }
}

@Injectable({
  providedIn: 'root'
})
export class PubmedServiceSearchable implements TableDataService<Publication> {

  search: BehaviorSubject<string>

  constructor(
    private pubmedDbSearchable: PubmedDbSearchable
  ) {
    this.search = this.pubmedDbSearchable.search
  }

  valueChanges(params?: TableQuery): Observable<Publication[] | null> {
    return this.pubmedDbSearchable.valueChanges({
      path: 'pubmedDbSearchable',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.pubmedDbSearchable.count({
      path: 'pubmedDbSearchable',
      idField: 'id',
      ...params
    })
  }

}

@Injectable({
  providedIn: 'root'
})
class PubmedDbSearchable extends IndexedDbDocs {

  search: BehaviorSubject<string>

  constructor(
    pubmedService: PubmedService
  ) {
    const search = new BehaviorSubject<string>('')
    super({tables: combineLatest([
      pubmedService.valueChanges(),
      search
    ]).pipe(
      map(([ps, s]) => {
        if (!ps) {
          return {'/pubmedDbSearchable': {}}
        }
        if (s.length) {
          return {'/pubmedDbSearchable': index(searchQuery(ps, s.toLowerCase()))}
        }
        return {'/pubmedDbSearchable': index(ps)}
      }),
      shareReplay(1)
    )})
    this.search = search
  }
    
}

function searchQuery(ps: Publication[], s: string) {
  return ps.filter(p => {
    return p['fullAuthorEdited'].toLowerCase().includes(s.toLowerCase()) ||
      p['title'].toLowerCase().includes(s.toLowerCase()) ||
      p['journalTitle'].toLowerCase().includes(s.toLowerCase())
  })
}
