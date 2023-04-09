import { Inject, Injectable } from '@angular/core';
import { Docs, DocsTableDataService, TableFieldValue } from '@community-dashboard/rest';

export interface PublicationException {
  // https://stackoverflow.com/questions/70956050/how-do-i-declare-object-value-type-without-declaring-key-type
  [key: string]: TableFieldValue,
  "id"?: string,
  "pubmedID": string,
}

@Injectable({
  providedIn: 'root'
})
export class PublicationExceptionService extends DocsTableDataService<PublicationException> {

  constructor(
    @Inject('DocsToken') docs: Docs
  ) {
    super({docs, path: 'publication-exception', idField: 'id'})
  }

}
