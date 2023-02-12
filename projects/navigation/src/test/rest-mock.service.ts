import { Injectable } from '@angular/core';
import { Id, RestMemory } from 'rest';
import { SCAN_LOGS_FIXTURE, PUBLICATIONS_FIXTURE, YOUTUBE_FIXTURE, COURSE_STATS_FIXTURE } from 'community-dashboard'

function index(a: any[]) {
  return a.reduce(([acc, i], v) => {acc[v.id || i.toString()] = v; return [acc, i+1]}, [{}, 0])[0]
}

export const FIXTURES: {[key: string]: {[key: Id]: object}} = {
  '/publications': index(PUBLICATIONS_FIXTURE),
  '/youtube': index(YOUTUBE_FIXTURE),
  '/course-stats': index(COURSE_STATS_FIXTURE),
  '/scans/12/logs': index(SCAN_LOGS_FIXTURE),
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
