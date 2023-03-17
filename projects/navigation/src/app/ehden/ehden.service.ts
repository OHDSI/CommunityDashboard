import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, DocsToken, TableFieldValue, TableQuery, TableDataService, IndexedDbDocs } from '@community-dashboard/rest';
import { map, Observable, shareReplay } from 'rxjs';
import * as td from 'tinyduration'
import * as d3 from 'd3';

export interface Ehden {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  id?: string,
  "lastUpdate": string,
  "users": {
    "number_of_users": string,
    "year": string
  }[],
  "courses": {
    "number_of_courses": string,
    "year": string
  }[],
  "completions": {
    "completions": string,
    "year": string | null
  }[],
  "course_stats": CourseStat[],
}

export interface CourseStat {
  [key: string]: TableFieldValue,
  "course_id": string,
  "course_fullname": string,
  "course_shortname": string,
  "category": string | null,
  "started": string,
  "completions": string,
  "course_started": string,
  "teachers": {
    "firstname": string,
    "lastname": string
  }[]
}

@Injectable({
  providedIn: 'root'
})
export class EhdenService extends DocsTableDataService<Ehden> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) { 
    super({docs, path: 'ehden', idField: 'id'})
  }

  courseCount(): Observable<number> {
    return this.valueChanges().pipe(
      map(es => {
        if (!es) {
          return 0
        }
        return es[0].course_stats.length
      })
    )
  }

  courseCompletions(): Observable<number> {
    return this.valueChanges().pipe(
      map(es => {
        if (!es) {
          return 0
        }
        return es[0].completions.reduce((acc, c) => {
          if (c.year === null) {
            return acc
          }
          return acc + +c.completions
        }, 0)
      })
    )
  }

}

@Injectable({
  providedIn: "root"
})
export class CourseStatsService implements TableDataService<CourseStat> {

  constructor(
    private courseStatsDb: CourseStatsDb
  ) { }

  valueChanges(params?: TableQuery): Observable<CourseStat[] | null> {
    return this.courseStatsDb.valueChanges({
      path: 'courseStats',
      idField: 'course_id',
      ...params
    })
  }

  count(params?: TableQuery): Observable<number> {
    return this.courseStatsDb.count({
      path: 'courseStats',
      idField: 'course_id',
      ...params
    })
  }
}

@Injectable({
  providedIn: 'root'
})
class CourseStatsDb extends IndexedDbDocs {

  constructor(
    ehdenService: EhdenService
  ) {
    super({tables: ehdenService.valueChanges().pipe(
      map(es => ({'/courseStats': es?.reduce((acc, e) => {
        if (e.course_stats) {
          for (const c of e.course_stats) {
            acc[c.course_id] = c
          }
        }
        return acc
      }, {} as {[key: string]: CourseStat}) ?? {} })),
      shareReplay(1)
    )})
  }
    
}