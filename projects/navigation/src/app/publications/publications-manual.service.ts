import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, TableFieldValue } from '@community-dashboard/rest';

export interface PublicationManual {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id"?: string,
  "creationDate": string,
  "fullAuthorEdited": string,
  "title": string,
  "journalTitle": string,
  "termFreq": string,
  "numCitations": number | null,
}

@Injectable({
  providedIn: 'root'
})
export class PublicationsManualService extends DocsTableDataService<PublicationManual> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) {
    super({docs, path: 'publications-manual', idField: 'id'})
  }

}
