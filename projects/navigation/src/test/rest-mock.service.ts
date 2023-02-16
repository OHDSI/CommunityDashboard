import { Injectable } from '@angular/core';
import { Id, RestMemory } from '@community-dashboard/rest';
import { SCAN_LOGS_FIXTURE, PUBLICATIONS_FIXTURE, YOUTUBE_FIXTURE, COURSE_STATS_FIXTURE, FUNDING_FIXTURE } from '@community-dashboard/community-dashboard'

function index(a: any[]) {
  return a.reduce(([acc, i], v) => {acc[v.id || i.toString()] = v; return [acc, i+1]}, [{}, 0])[0]
}

function records(a: {[key: string]: {[key: string]: any}}) {
  const records: {[key: Id]: {[key: string]: any}} = {}
  for (const [c, rs] of Object.entries(a)) {
    for (const [k, r] of Object.entries(rs)) {
      if (!(k in records)) {
        const n: {[key: string]: any} = {
          id: k
        }
        records[k] = n
      }
      records[k][c] = r
    }
  }
  return records
}


export const FIXTURES: {[key: string]: {[key: Id]: object}} = {
  '/publications': index(PUBLICATIONS_FIXTURE),
  '/youtube': index(YOUTUBE_FIXTURE),
  '/course-stats': index(COURSE_STATS_FIXTURE),
  '/scans/12/logs': index(SCAN_LOGS_FIXTURE),
  '/funding': records(FUNDING_FIXTURE)
}

@Injectable({
  providedIn: 'root'
})
export class RestMock extends RestMemory {

  constructor(
  ) {
    super(FIXTURES)
  }

}
