import { Injectable } from '@angular/core';
import { IndexedDbDocs } from '@community-dashboard/rest';
import dbExportsJson from '../../../../test/exports/all.json'
import { of } from 'rxjs'

const dbExports = dbExportsJson as {[key:string]: any}

export const FIXTURES: {[key: string]: {[key: string]: object}} = {
  '/pubmedArticles': dbExports['pubmedArticles'],
  '/youtube': dbExports['youtube'],
  '/ehden': dbExports['ehden'],
}

@Injectable({
  providedIn: 'root'
})
export class DocsMock extends IndexedDbDocs {

  constructor(
  ) {
    super({tables: of(FIXTURES)})
  }

}
