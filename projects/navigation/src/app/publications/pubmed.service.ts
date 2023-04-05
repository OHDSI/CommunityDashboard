import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, DocsToken, index, IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { BehaviorSubject, combineLatest, map, Observable, shareReplay } from 'rxjs';
import * as d3 from 'd3';

// export interface Publication {
//   // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
//   [key: string]: TableFieldValue,
//   "id": string,
//   "pubmed": {
//     "fullAuthor": string[],
//     "grantNum": string|null,
//     "meshT": string[],
//     "language": string[]
//     "nlmID": string,
//     "abstract": string,
//     "source": string,
//     "creationDate": string,
//     "title": string,
//     "pubmedID": string,
//     "affiliation": string[],
//     "countryOfPub": string[],
//     "pmcID": string|null,
//     "journalTitle": string,
//     "locID": string,
//   },
//   "google_scholar": {
//     "created_at": string,
//     "results": {
//       "summary": string,
//       "total_citations": number,
//       "citations_link": string,
//       "versions_link": string,
//       "link": string,
//       "title": string,
//       "authors": {
//         "name": string,
//         "link": string
//       }[]
//     }[]
//   },
//   "snomed": {
//     "ents": {
//       "end_char": number,
//       "start_char": number,
//       "snomed": string
//     }[]
//   }
// }

export interface Publication {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id": string,
  "pubmedID": string,
  "creationDate": string,
  "fullAuthorEdited": string,
  "title": string,
  "journalTitle": string,
  "termFreq": string,
  "numCitations": number | null,
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
    super({docs, path: 'pubmedJoined', idField: 'id'})
  }

  override valueChanges(params?: TableQuery): Observable<Publication[] | null> {
    return super.valueChanges(params).pipe(
      map(ps => {
        if (!ps) {
          return null
        }
        return ps.flatMap((p: any) => {
          if (!p.pubmed) {
            // console.log('could not parse pubmed', p)
            return []
          }
          return [{
            id: p.pubmed.pubmedID,
            pubmedID: p.pubmed.pubmedID,
            creationDate: p.pubmed.creationDate,
            fullAuthorEdited: p.pubmed.fullAuthor?.map((a: string) => {
              const [last, first] = a.split(', ')
              return `${first} ${last}`
            }).join(', ') ?? '',
            title: p.pubmed.title,
            journalTitle: p.pubmed.journalTitle,
            termFreq: p.snomed?.ents.map((e: any) => e.snomed).join(', ') ?? '',
            numCitations: p.google_scholar?.results[0]?.total_citations ?? null
          } as Publication]
        })
      })
    )
  }

  summary(): Observable<PublicationSummary[]> {
    return this.valueChanges().pipe(
      map(ps => {
        if (!ps) {
          return []
        }
        const r: Map<Date, {n: number, nCitations: number}> = d3.rollup(
          ps.sort((a, b) => d3.ascending(a.creationDate, b.creationDate)), 
          (v: Publication[]) => ({
            n: v.length,
            nCitations: d3.sum(v, (d: Publication) => d.numCitations)
          }),
          (d: Publication) => new Date(d.creationDate).getFullYear()
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
          p.fullAuthorEdited
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
          return {'/pubmedDbSearchable': withPubmedId(searchQuery(ps, s.toLowerCase()))}
        }
        return {'/pubmedDbSearchable': withPubmedId(ps)}
      }),
      shareReplay(1)
    )})
    this.search = search
  }
    
}

function withPubmedId(ps: Publication[]): {[key: string]: Publication} {
  return ps.reduce((acc, p) => {
    acc[p.pubmedID] = p
    return acc
  }, {} as {[key: string]: Publication})
}

function searchQuery(ps: Publication[], s: string) {
  return ps.filter(p => {
    return p['fullAuthorEdited'].toLowerCase().includes(s.toLowerCase()) ||
      p['title'].toLowerCase().includes(s.toLowerCase()) ||
      p['journalTitle'].toLowerCase().includes(s.toLowerCase())
  })
}
