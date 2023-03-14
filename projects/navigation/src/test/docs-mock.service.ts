import { Injectable } from '@angular/core';
import { IndexedDbDocs, FixtureIndex, parseExport } from '@community-dashboard/rest';
import dbExportsJson from '../../../../test/exports/all.json'
import repoExportsJson from '../../../../test/exports/2-0-export.json'
import { of } from 'rxjs'

const dbExports = dbExportsJson as {[key:string]: any}
const repoExports = repoExportsJson as {[key:string]: any}

export const FIXTURES: FixtureIndex = {
  ...parseExport(dbExports),
  ...parseExport(repoExports)
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
