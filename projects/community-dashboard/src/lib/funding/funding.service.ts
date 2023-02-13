import { Inject, Injectable } from '@angular/core';
import { Rest, RestDelegate, RestToken } from '@community-dashboard/rest';

export interface Funding {
  "DATE ADDED": string,
  "LOCATION FOUND": string,
  "LOCATION FOUND 2": string,
  "AGENCY": string,
  "OPPORTUNITY DETAILS": string,
  "OPPORTUNITY LINK": string,
  "BUDGET": string,
  "NUMBER YEARS": string,
  "SUBMISSION DEADLINE(S) IN 2023": string,
}

@Injectable({
  providedIn: 'root'
})
export class FundingService extends RestDelegate<Funding> {

  constructor(
    @Inject(RestToken) rest: Rest
  ) {
    super(rest, '', 'funding')
  }
}
