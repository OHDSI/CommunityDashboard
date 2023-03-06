import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestToken } from '@community-dashboard/rest';
import { map, Observable } from 'rxjs';

export interface YouTubeVideo {
  "id": string,
  "Title": string,
  "titleText"?: string,
  "titleLink"?: string,
  "Duration": string,
  "Date Published": string,
  "Total Views": number,
  "Recent Views": number,
  "channelTitle": string,
  "SNOMED Terms (n)": string,
  "snomedTerms"?: string,
  "snomedLink"?: string,
  "yr": number,
  "hrsWatched": number,
  "Length": string
}

@Injectable({
  providedIn: 'root'
})
export class YouTubeService extends RestDelegate<YouTubeVideo> {

  constructor(
    @Inject('RestToken') rest: Rest,
    @Inject('environment') private environment: any,
  ) {
    super(rest, '', 'youtube')
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
  }): Observable<YouTubeVideo[]> {
    return super.find(params).pipe(
      map(p => { 
        return p.map((r) => {
          // n[n.find("[")+1:n.find("]")]
          r.titleText = r['Title'].substring(1, r['Title'].indexOf(']'))
          r.titleLink = r['Title'].substring(r['Title'].lastIndexOf('(')+1, r['Title'].length - 1)
          r.snomedTerms = r["SNOMED Terms (n)"].substring(1, r['SNOMED Terms (n)'].lastIndexOf(']'))
          r.snomedLink = `${this.environment.plots}${r['SNOMED Terms (n)'].substring(r['SNOMED Terms (n)'].lastIndexOf('(')+1, r['SNOMED Terms (n)'].length - 1)}`
          return r
        })
      })
    )
  }
}
