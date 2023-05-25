import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, DocsToken, index, IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { BehaviorSubject, combineLatest, map, Observable, shareReplay } from 'rxjs';
import * as d3 from 'd3';
import { PublicationsManualService } from './publications-manual.service';
import { PublicationExceptionService } from './publication-exception.service';

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

interface Searchable {
  "fullAuthorEdited": string,
  "title": string,
  "journalTitle": string,
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
          p.fullAuthorEdited.split(', ').forEach(a => acc.add(a))
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
    pubmedService: PubmedService,
    publicationsManualService: PublicationsManualService,
    publicationExceptionService: PublicationExceptionService,
  ) {
    const search = new BehaviorSubject<string>('')
    super({tables: combineLatest([
      publicationsManualService.valueChanges(),
      pubmedService.valueChanges(),
      publicationExceptionService.valueChanges(),
      search
    ]).pipe(
      map(([ms, ps, es, s]) => {
        const msWithId: Searchable[] = ms?.map(m => ({...m, manualPublicationId: m.id})) ?? []
        const psWithException: Searchable[] = ps?.map(p => ({...p, exception: es?.filter((e) => e.pubmedID === p.pubmedID)[0]?.id ?? false})) ?? []
        const combined: Searchable[] = msWithId.concat(psWithException)
        if (s.length) {
          return {'/pubmedDbSearchable': index(searchQuery(combined, s))}
        }
        return {'/pubmedDbSearchable': index(combined)}
      }),
      shareReplay(1)
    )})
    this.search = search
  }
    
}

function searchQuery(ps: Searchable[], s: string) {
  return ps.filter(p => {
    return p['fullAuthorEdited'].toLowerCase().includes(s.toLowerCase()) ||
      p['title'].toLowerCase().includes(s.toLowerCase()) ||
      p['journalTitle'].toLowerCase().includes(s.toLowerCase())
  })
}
