import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestToken } from '@community-dashboard/rest';
import { map, Observable } from 'rxjs';

export interface YouTubeVideo {
  "id": string,
  "title": string,
  "termFreq": string,
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
        if (!p) {
          return []
        }
        return p.map((r) => {
          // n[n.find("[")+1:n.find("]")]
          r.titleText = r['title']
          r.titleLink = `https://www.youtube.com/watch?v=${r['id']}`
          r.snomedTerms = r['termFreq']
          r.snomedLink = ''
          return r
        })
      })
    )
  }
}
