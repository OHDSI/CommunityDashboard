import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, DocsToken, TableFieldValue } from '@community-dashboard/rest';
import { map, Observable } from 'rxjs';
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
  "course_stats": {
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
  }[],
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

}