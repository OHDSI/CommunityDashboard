import { Injectable } from '@angular/core';
import { IndexedDbDocs, FixtureIndex, parseExport, records } from '@community-dashboard/rest';
import dbExportsJson from '../../../../test/exports/all.json'
import repoExportsJson from '../../../../test/exports/2-0-export.json'
import pubmedExportsJson from '../../../../test/exports/pubmedJoined.json'
import publicationsManualJson from '../../../../test/exports/publicationsManual.json'
import publicationExceptionJson from '../../../../test/exports/publication-exception.json'
import youtubeExceptionExportsJson from '../../../../test/exports/youtube-exceptions.json'
import youTubeJoinedJson from '../../../../test/exports/youTubeJoined.json'
import { of } from 'rxjs'
import { FUNDING_FIXTURE } from './funding-fixture';

const dbExports = dbExportsJson as {[key:string]: any}
const repoExports = repoExportsJson as {[key:string]: any}

export const FIXTURES: FixtureIndex = {
  ...parseExport(dbExports),
  ...parseExport(repoExports),
  ...parseExport(pubmedExportsJson),
  ...parseExport(youtubeExceptionExportsJson),
  ...parseExport(publicationsManualJson),
  ...parseExport(publicationExceptionJson),
  ...parseExport(youTubeJoinedJson),
  '/funding': records(FUNDING_FIXTURE),
}

console.log(FIXTURES)

@Injectable({
  providedIn: 'root'
})
export class DocsMock extends IndexedDbDocs {

  constructor(
  ) {
    super({tables: of(FIXTURES)})
  }

}
