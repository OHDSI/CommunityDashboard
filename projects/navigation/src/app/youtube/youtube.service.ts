import { ErrorHandler, Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, DocsToken, IndexedDbDocs, TableDataService, TableFieldValue, TableQuery } from '@community-dashboard/rest';
import { combineLatest, map, Observable, shareReplay } from 'rxjs';
import * as td from 'tinyduration'
import * as d3 from 'd3';

// export interface YouTube {
//   // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
//   [key: string]: TableFieldValue,
//   id?: string,
//   "title": string,
//   "duration": string,
//   "channelId": string,
//   "channelTitle": string,
//   "categoryId": string,
//   "publishedAt": string,
//   "counts": {
//     "checkedOn": string,
//     "viewCount": string,
//   }[]
//   "lastChecked": string,
//   "snomedIDs": string[],
//   "snomedNames": string[],
//   "termFreq": string,
//   "latestViewCount": number,
// }

export interface YouTube {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id?: string,
  "title": string,
  "duration"?: string,
  "publishedAt": string,
  "viewCount": string,
  "snomed"?: {
    "ents": {
      "text": string,
      "start_char": string,
      "end_char": string
    }[]
  },
}

export interface YouTubeException {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id?: string,
  youtubeId: string
}

export interface YouTubeAnnualSummary {
  year: number,
  contentHours: number,
  hoursWatched: number,
  cumulativeHoursWatched: number
}

@Injectable({
  providedIn: 'root'
})
export class YouTubeService extends DocsTableDataService<YouTube> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) {
    super({docs, path: 'youTubeJoined', idField: 'id'})
  }
}

@Injectable({
  providedIn: 'root'
})
export class YouTubeExceptionService extends DocsTableDataService<YouTubeException> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) {
    super({docs, path: 'youtube-exceptions', idField: 'id'})
  }
}

@Injectable({
  providedIn: 'root'
})
export class YouTubeServiceWithCountsSummary implements TableDataService<YouTube> {

  constructor(
    private withCountSummaryDb: YouTubeTransformedDb,
  ) {}

  valueChanges(params?: TableQuery): Observable<YouTube[] | null> {
    return this.withCountSummaryDb.valueChanges({
      path: 'youtubeWithCountSummary',
      idField: 'id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.withCountSummaryDb.count({
      path: 'youtubeWithCountSummary',
      idField: 'id',
      ...params
    })
  }

  annually(): Observable<YouTubeAnnualSummary[]> {
    return this.valueChanges().pipe(
      map(ys => {
        if (!ys) {
          return []
        }
        const r: Map<number, {contentHours: number, hoursWatched: number}> = d3.rollup(
          ys.sort((a, b) => d3.ascending(a.publishedAt, b.publishedAt)), 
          (v: YouTube[]) => {
            return v.reduce((acc, y) => {
              const h = y.duration ? inHours(td.parse(y.duration)) : 0
              const views = +y.viewCount
              acc.contentHours += h
              acc.hoursWatched += h * views
              return acc
            }, {
              contentHours: 0,
              hoursWatched: 0
            })
          },
          (d: YouTube) => new Date(d.publishedAt).getFullYear()
        )
        const years = Array.from(r.entries()).map(([year, summary]) => ({year, ...summary}))
        const annualSummaries = (Array.from(d3.cumsum(years.map(y => y.hoursWatched))) as number[]).map((c, i) => {
          return {...years[i], cumulativeHoursWatched: c}
        })
        return annualSummaries
      })
    )
  }

  hoursWatched(): Observable<number> {
    return this.annually().pipe(
      map(as => {
        const currentYear = as[as.length - 1]
        return currentYear.cumulativeHoursWatched
      })
    )
  }

  videosPublished(): Observable<number> {
    return this.valueChanges().pipe(
      map(ys => {
        if (!ys) {
          return 0
        }
        return ys.length
      })
    )
  }
}

@Injectable({
  providedIn: 'root'
})
class YouTubeTransformedDb extends IndexedDbDocs {

  constructor(
    youtubeService: YouTubeService,
    youtubeExceptionService: YouTubeExceptionService,
    errorHandler: ErrorHandler,
  ) {
    const d = combineLatest([
      youtubeService.valueChanges(),
      youtubeExceptionService.valueChanges(),
    ])
    super({tables: d.pipe(
      map(([ys, es]) => {
        if (!ys || !es) {
          errorHandler.handleError('Expected youtube data to always be available.')
          return []
        }
        const filtered = es.map(e => e.youtubeId)
        return ys.filter(y => y.id && !filtered.includes(y.id))
      }),
      map(ys => ({'/youtubeWithCountSummary': ys?.reduce((acc, y) => {
        acc[y.id!] = {...y, latestViewCount: y.viewCount }
        return acc
      }, {} as {[key: string]: YouTube}) ?? {} })),
      shareReplay(1)
    )})
  }
    
}

function inHours(d: td.Duration) {
  return (d.days ?? 0 * 24) + (d.hours ?? 0) + (d.minutes ?? 0)/60 + (d.seconds ?? 0)/3600
}