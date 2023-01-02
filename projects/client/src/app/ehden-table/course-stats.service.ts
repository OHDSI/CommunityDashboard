import { HttpClient } from '@angular/common/http';
import { ErrorHandler, Injectable } from '@angular/core';
import { delay, Observable, of, Subject } from 'rxjs';
import { environment } from '../../environments/environment';
import { Change } from '../table-data-source';

export interface CourseStat {
  "course_fullname": string,
  "courseFullNameText"?: string,
  "courseFullNameLink"?: String,
  "course_shortname": string,
  "category": string,
  "started": number,
  "completions": number,
  "course_started": string,
  "authors": string
}

@Injectable({
  providedIn: 'root'
})
export class CourseStatsService {

  data: CourseStat[] = []
  changes = new Subject<Change>()

  constructor(
    private http: HttpClient,
    private errorHandler: ErrorHandler,
  ) {
    this.http.get<CourseStat[]>(`${environment.plots}/course-stats`).subscribe({
      next: (p) => { 
        this.data = p.map((r) => {
          // n[n.find("[")+1:n.find("]")]
          r.courseFullNameText = r['course_fullname'].substring(1, r['course_fullname'].indexOf(']'))
          r.courseFullNameLink = r['course_fullname'].substring(r['course_fullname'].lastIndexOf('(')+1, r['course_fullname'].length - 1)
          return r
        }) 
        this.changes.next({}) 
      },
      error: (r) => { this.errorHandler.handleError(r) }
    })
  }

  create(params: {
    body: Omit<CourseStat, 'id'>
  }): Observable<CourseStat> {
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
  }): Observable<CourseStat[]> {
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

  private order(data: CourseStat[], order: string[]): void {
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
