import { ScanParameters } from "../controllers/community-dashboard.controller";
import { CommitArray, ContentFile, GitHub, MinimalRepositoryArray } from "../services";
import { catchError, concat, concatAll, concatMap, from, map, of, tap, reduce, Observable, mergeMap } from 'rxjs'
import { ScanRepository } from "../repositories";
import debug from "debug";
import { Scan, ScanLog, Status } from "../models";

const error = debug('community-dashboard:api:error')

// const statusMatch = decoded.match(/<img src="https:\/\/img\.shields\.io\/badge\/Study%20Status-.*\.svg" alt="Study Status: (.*)">/)
// const status = statusMatch ? {status: statusMatch[1]} : {}
// const useCasesMatch = decoded.match(/- Analytics use case\(s\): *\*\*(.*)\*\*/)
// const useCases = useCasesMatch ? {useCases: useCasesMatch[1]} : {}
const readmeRegex = {
  status: /<img src="https:\/\/img\.shields\.io\/badge\/Study%20Status-.*\.svg" alt="Study Status: (.*)">/,
  useCases: /- Analytics use case\(s\): *\**([^*\n]*)\**/,
  studyType: /- Study type: *\**([^*\n]*)\**/,
  tags: /- Tags: *\**([^*\n]*)\**/,
  studyLead: /- Study lead: *\**([^*\n]*)\**/,
  startDate: /- Study start date: *\**([^*\n]*)\**/,
  endDate: /- Study end date: *\**([^*\n]*)\**/,
  protocol: /- Protocol: *\**([^*\n]*)\**/,
  publications: /- Publications: *\**([^*\n]*)\**/,
  results: /- Results explorer: *\**([^*\n]*)\**/,
}

export const scan = (
  github: GitHub,
  scanRepository: ScanRepository,
  scanEntity: Scan,
  parameters: ScanParameters
): void => {
  from(github.reposListForOrg({org: parameters.org})).pipe(
    concatMap(rs => {
      if (!rs.body) {
        throw rs
      }
      return (rs as MinimalRepositoryArray).body
    }),
    // log repo
    concatMap(r => {
      return from(scanRepository.scanLogs(scanEntity.id).create(new ScanLog({
        scanId: scanEntity.id,
        status: Status.IN_PROGRESS,
        repository: {
          name: r.name,
          updatedAt: r.updated_at,
          watchersCount: r.watchers_count,
        },
      }))).pipe(
        map(_ => r)
      )
    }),
    // get commits
    concatMap(r => {
      return from(github.reposListCommits({
        owner: parameters.org,
        repo: r.name,
        path: 'README.md'
      })).pipe(
        concatMap(cs => {
          if (!cs.body) {
            throw cs
          }
          return (cs as CommitArray).body
        }),
        map(c => ({
          commit: c,
          repo: r,
        }))
      )
    }),
    // get readme's for commits
    concatMap(l => {
      return from(github.reposGetReadme({
        owner: parameters.org,
        repo: l.repo.name,
        ref: l.commit.sha
      })).pipe(
        catchError(reason => {
          if ('response' in reason) {
            return of(reason.response as Response)
          }
          throw reason
        }),
        map(readme => {
          if (!readme.body) {
            throw readme
          }
          if (readme.status === 404) {
            return {
              ...l,
              readme: null,
            }
          }
          return {
            ...l,
            readme: (readme as ContentFile)
          }
        }),
      )
    }),
    // log readme's
    concatMap((l) => {
      return from(scanRepository.scanLogs(scanEntity.id).create(new ScanLog({
        scanId: scanEntity.id,
        status: Status.IN_PROGRESS,
        readmeCommit: {
          sha: l.commit.sha,
          author: l.commit.commit.author,
          repoName: l.repo.name,
          summary: summarizeReadme(l.readme)
        },
      })))
    }),
    reduce((m, _) => m),
    concatMap(_ => 
      from(scanRepository.scanLogs(scanEntity.id).create(new ScanLog({
        scanId: scanEntity.id,
        status: Status.COMPLETE,
      })) as Promise<ScanLog>)
    ),
    catchError(r => 
      from(scanRepository.scanLogs(scanEntity.id).create(new ScanLog({
        scanId: scanEntity.id,
        status: Status.ERROR,
      })) as Promise<ScanLog>).pipe(
        map(_ =>  {throw r})
      )
    ),
  ).subscribe({
    error: r => error(JSON.stringify(r, null, 4)),
  })
}

const summarizeReadme = (readme: ContentFile | null) => {
  const summary: {
    [key: string]: any,
    exists: boolean,
    title: string|null,
    status: string|null,
    useCases: string|null,
    studyType: string|null,
    tags: string|null,
    studyLeads: string|null,
    startDate: string|null,
    endDate: string|null,
    protocol: string|null,
    publications: string|null,
    results: string|null,
  } = {
    exists: false,
    title: null,
    status: null,
    useCases: null,
    studyType: null,
    tags: null,
    studyLeads: null,
    startDate: null,
    endDate: null,
    protocol: null,
    publications: null,
    results: null,  
  }
  if (!readme) {
    return summary
  }
  const decoded = Buffer.from(readme.body.content, 'base64').toString('utf8')
  const lines = decoded.split('\n')
  if (/=+/.test(lines[1])) {
    summary.title = lines[0]
  }
  for (const [k, r] of Object.entries(readmeRegex)) {
    const ms = decoded.match(r)
    const m = ms ? ms[1] : null
    if (['studyLead', 'useCases', 'tags', 'studyType'].includes(k)) {
      summary[k] = m?.split(',').map(l => l.trimStart().trimEnd())
    } else {
      summary[k] =  m?.trimStart().trimEnd()
    }
    
  }
  return summary
}