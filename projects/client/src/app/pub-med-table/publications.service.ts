import { HttpClient } from '@angular/common/http';
import { ErrorHandler, Injectable } from '@angular/core';
import { delay, Observable, of, Subject } from 'rxjs';
import { environment } from '../../environments/environment';
import { Change } from '../table-data-source';

export interface Publication  {
  "Authors": string,
  "Citation Count": number,
  "Creation Date": string,
  "First Authors": string,
  "Journal": string,
  "PubMed ID": string,
  "Publication": string,
  "publicationTitle"?: string,
  "publicationLink"?: string,
  "Publication Year": number,
  "SNOMED Terms (n)": string,
  "snomedTerms"?: string,
  "snomedLink"?: string,
  "Title": string,
  "authors": ""
}

@Injectable({
  providedIn: 'root'
})
export class PublicationsService {

  data: Publication[] = []
  changes = new Subject<Change>()

  constructor(
    private http: HttpClient,
    private errorHandler: ErrorHandler,
  ) {
    this.http.get<Publication[]>(`${environment.plots}/publications`).subscribe({
      next: (p) => { 
        this.data = p.map((r) => {
          // n[n.find("[")+1:n.find("]")]
          r.publicationTitle = r['Publication'].substring(1, r['Publication'].indexOf(']'))
          r.publicationLink = r['Publication'].substring(r['Publication'].lastIndexOf('(')+1, r['Publication'].length - 1)
          r.snomedTerms = r["SNOMED Terms (n)"].substring(1, r['SNOMED Terms (n)'].lastIndexOf(']'))
          r.snomedLink = `${environment.plots}${r['SNOMED Terms (n)'].substring(r['SNOMED Terms (n)'].lastIndexOf('(')+1, r['SNOMED Terms (n)'].length - 1)}`
          return r
        }) 
        this.changes.next({}) 
      },
      error: (r) => { this.errorHandler.handleError(r) }
    })
  }

  create(params: {
    body: Omit<Publication, 'id'>
  }): Observable<Publication> {
    const n = {...params.body, id: this.data.length}
    this.data.push(n)
    this.changes.next({})
    return of(n).pipe(delay(1000))
  }

  find(params?: {
    id?: number,
    filter?: {
      skip?: number,
      limit?: number,
      order?: string[],
    }
  }): Observable<Publication[]> {
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

  private order(data: Publication[], order: string[]): void {
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
