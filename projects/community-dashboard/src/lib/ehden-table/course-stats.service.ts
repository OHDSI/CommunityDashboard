import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestToken } from '@community-dashboard/rest';
import { map, Observable } from 'rxjs';

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
export class CourseStatsService extends RestDelegate<CourseStat> {

  constructor(
    @Inject(RestToken) rest: Rest,
  ) {
    super(rest, '', 'course-stats')
  }

  override find(params?: {
    filter?: {
        skip?: number;
        limit?: number;
        order?: string[];
        where?: {
            [key: string]: any;
        };
    };
  }): Observable<CourseStat[]> {
    return super.find(params).pipe(
      map(p => { 
        return p.map((r) => {
          // n[n.find("[")+1:n.find("]")]
          r.courseFullNameText = r['course_fullname'].substring(1, r['course_fullname'].indexOf(']'))
          r.courseFullNameLink = r['course_fullname'].substring(r['course_fullname'].lastIndexOf('(')+1, r['course_fullname'].length - 1)
          return r
        }) 
      })
    )
  }
}
