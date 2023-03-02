import { Injectable } from '@angular/core';
import { Id, index, RestMemory, records, indexAll } from '@community-dashboard/rest';
import { COMMUNITY_DASHBOARD_README_SUMMARIES } from './community-dashboard-readme-summaries';
import { COMMUNITY_DASHBOARD_REPOS } from './community-dashboard-repos';
import { COURSE_STATS_FIXTURE } from './course-stats-fixture';
import { FUNDING_FIXTURE } from './funding-fixture';
import { PUBLICATIONS_FIXTURE } from './publications-fixture';
import { SCAN_LOGS_FIXTURE } from './scan-logs-fixture';
import { YOUTUBE_FIXTURE } from './youtube-fixture';

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
