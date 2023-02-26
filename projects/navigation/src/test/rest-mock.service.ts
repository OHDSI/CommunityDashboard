import { Injectable } from '@angular/core';
import { Id, index, RestMemory, records, indexAll } from '@community-dashboard/rest';
import {
  PUBLICATIONS_FIXTURE, YOUTUBE_FIXTURE, COURSE_STATS_FIXTURE, FUNDING_FIXTURE, COMMUNITY_DASHBOARD_REPOS, COMMUNITY_DASHBOARD_README_SUMMARIES, SCAN_LOGS_FIXTURE
} from '@community-dashboard/community-dashboard'

export const FIXTURES: {[key: string]: {[key: Id]: object}} = {
  '/publications': index(PUBLICATIONS_FIXTURE),
  '/youtube': index(YOUTUBE_FIXTURE),
  '/course-stats': index(COURSE_STATS_FIXTURE),
  '/funding': records(FUNDING_FIXTURE),
  '/communityDashboardRepos': index(COMMUNITY_DASHBOARD_REPOS),
  ...indexAll(COMMUNITY_DASHBOARD_README_SUMMARIES),
  '/scanLogs': index(SCAN_LOGS_FIXTURE)
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
