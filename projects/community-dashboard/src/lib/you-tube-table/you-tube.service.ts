import { HttpClient } from '@angular/common/http';
import { ErrorHandler, Inject, Injectable } from '@angular/core';
import { delay, Observable, of, Subject } from 'rxjs';
import { Change } from '../table-data-source-old';

export interface YouTubeVideo {
  "id": string,
  "Title": string,
  "titleText"?: string,
  "titleLink"?: string,
  "Duration": string,
  "Date Published": string,
  "Total Views": number,
  "Recent Views": number,
  "channelTitle": string,
  "SNOMED Terms (n)": string,
  "snomedTerms"?: string,
  "snomedLink"?: string,
  "yr": number,
  "hrsWatched": number,
  "Length": string
}

@Injectable({
  providedIn: 'root'
})
export class YouTubeService {

  data: YouTubeVideo[] = []
  changes = new Subject<Change>()

  constructor(
    private http: HttpClient,
    private errorHandler: ErrorHandler,
    @Inject('environment') environment: any,
  ) {
    this.http.get<YouTubeVideo[]>(`${environment.plots}/youtube`).subscribe({
      next: (p) => { 
        this.data = p.map((r) => {
          // n[n.find("[")+1:n.find("]")]
          r.titleText = r['Title'].substring(1, r['Title'].indexOf(']'))
          r.titleLink = r['Title'].substring(r['Title'].lastIndexOf('(')+1, r['Title'].length - 1)
          r.snomedTerms = r["SNOMED Terms (n)"].substring(1, r['SNOMED Terms (n)'].lastIndexOf(']'))
          r.snomedLink = `${environment.plots}${r['SNOMED Terms (n)'].substring(r['SNOMED Terms (n)'].lastIndexOf('(')+1, r['SNOMED Terms (n)'].length - 1)}`
          return r
        }) 
        this.changes.next({}) 
      },
      error: (r) => { this.errorHandler.handleError(r) }
    })
  }

  find(params?: {
    id?: number,
    filter?: {
      skip?: number,
      limit?: number,
      order?: string[],
    }
  }): Observable<YouTubeVideo[]> {
    if (params?.id) {
      return of([this.data[params.id]])
    } else {
      let d = [...this.data]
      if (params?.filter?.order) {
        this.order(d, params.filter.order)
      }
      if (params?.filter?.skip !== undefined) {
        d = d.splice(params?.filter?.skip, params?.filter?.limit)
      }
      return of(d)
    }
  }

  private order(data: YouTubeVideo[], order: string[]): void {
    order.reduceRight((_: null | void, o): void => {
      const [key, direction] = o.split(' ')
      data.sort((a: any, b: any) => {
        const isAsc = direction.toLowerCase() === 'asc';
        switch (key) {
          // case 'title': return compare(a.title, b.title, isAsc);
          // case 'id': return compare(+a.id, +b.id, isAsc);
          default: return this.compare(a[key], b[key], isAsc);
        }
      });
    }, null)
  }

  compare(a: any, b: any, isAsc: boolean): number {
    return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
  }

  count(): Observable<number> {
    return of(this.data.length)
  }
}
