import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, DocsToken, TableFieldValue } from '@community-dashboard/rest';
import { map, Observable } from 'rxjs';
import * as td from 'tinyduration'
import * as d3 from 'd3';

export interface YouTube {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id?: string,
  "title": string,
  "duration": string,
  "channelId": string,
  "channelTitle": string,
  "categoryId": string,
  "publishedAt": string,
  "counts": {
    "checkedOn": string,
    "viewCount": string,
  }[]
  "lastChecked": string,
  "snomedIDs": string[],
  "snomedNames": string[],
  "termFreq": string,
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
    super({docs, path: 'youtube', idField: 'id'})
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
              const h = inHours(td.parse(y.duration))
              const views = +y.counts.sort((a, b) => d3.descending(a.checkedOn, b.checkedOn))[0].viewCount
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
}

function inHours(d: td.Duration) {
  return (d.days ?? 0 * 24) + (d.hours ?? 0) + (d.minutes ?? 0)/60 + (d.seconds ?? 0)/3600
}