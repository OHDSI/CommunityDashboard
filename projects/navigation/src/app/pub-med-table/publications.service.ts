import { Inject, Injectable } from '@angular/core';
import { Rest, RestToken, RestDelegate } from '@community-dashboard/rest';
import { map, Observable } from 'rxjs';

export interface Publication  {
  "Authors": string,
  "Citation Count": number,
  "Creation Date": string,
  "First Authors": string,
  "Journal": string,
  "PubMed ID": string,
  "Publication": string,
  "publicationTitle"?: string,
  "publicationLink"?: string,
  "Publication Year": number,
  "SNOMED Terms (n)": string,
  "snomedTerms"?: string,
  "snomedLink"?: string,
  "Title": string,
  "authors": ""
}

@Injectable({
  providedIn: 'root'
})
export class PublicationsService extends RestDelegate<Publication> {

  constructor(
    @Inject('RestToken') rest: Rest,
    @Inject('environment') private environment: any,
  ) {
    super(rest, '', 'publications')
  }

  override find(params?: {
    filter?: {
        skip?: number;
        limit?: number;
        order?: string[];
        where?: {
            [key: string]: any;
        };
    };
  }): Observable<Publication[]> {
    return super.find(params).pipe(
      map(p => { 
        return p.map((r) => {
          // n[n.find("[")+1:n.find("]")]
          r.publicationTitle = r['Publication'].substring(1, r['Publication'].indexOf(']'))
          r.publicationLink = r['Publication'].substring(r['Publication'].lastIndexOf('(')+1, r['Publication'].length - 1)
          r.snomedTerms = r["SNOMED Terms (n)"].substring(1, r['SNOMED Terms (n)'].lastIndexOf(']'))
          r.snomedLink = `${this.environment.plots}${r['SNOMED Terms (n)'].substring(r['SNOMED Terms (n)'].lastIndexOf('(')+1, r['SNOMED Terms (n)'].length - 1)}`
          return r
        }) 
      })
    )
  }

}
