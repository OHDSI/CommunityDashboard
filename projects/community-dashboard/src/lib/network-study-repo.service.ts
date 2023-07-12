import { Injectable } from '@angular/core';

export interface NetworkStudyRepo {
  [key: string]: any
  id: string
  watchersCount: number
  name: string
  updatedAt: string
  latestReadme: ReadmeCommit
}

type UseCase = "Patient-level Prediction"
type StudyType = "Cohort study"
type Status = "Started"

export interface ReadmeCommit {
  "summary": {
    "useCases": UseCase[]
    "protocol": string|null
    "studyLeads": string[]
    "endDate": string
    "studyType": StudyType[]
    "title": string
    "results": string,
    "startDate": string
    "status": Status
    "publications": string,
    "tags": string[]
  } | null,
  "author": {
    "date": string,
    "name": string,
    "email": string
  },
  "sha": string
}

@Injectable({
  providedIn: 'root'
})
export class NetworkStudyRepoService {

  constructor() { }
}
