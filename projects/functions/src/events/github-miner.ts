import { catchError, concatMap, from, map, Observable, of, reduce } from 'rxjs'
import {Octokit} from "octokit";

export interface RepoSummary {
  name: string,
  updatedAt?: string | null,
  watchersCount?: number,
  readmeSummaries: {
    sha: string,
    author: {
      name?: string;
      email?: string;
      date?: string;
    } | null,
    summary: ReadmeSummaryDetails | null
  }[]
}

export interface ReadmeSummaryDetails {
  title: string | null,
  status: string | null,
  useCases: string[] | null,
  studyType: string[] |null,
  tags: string[] |null,
  studyLeads: string[] |null,
  startDate: string|null,
  endDate: string|null,
  protocol: string|null,
  publications: string|null,
  results: string|null,
}

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

export const mineGithub = (
  ghPat: string,
  org: string,
): Observable<RepoSummary> => {
  const octokit = new Octokit({ auth: ghPat });
  // from(github.reposListForOrg({org: parameters.org})).pipe(
  const repoPages = octokit.paginate.iterator(
      octokit.rest.repos.listForOrg,
      {
        org
      }
    )
  const repos = from(repoPages).pipe(
    concatMap(rs => from(rs.data.map(({
      name, updated_at: updatedAt, watchers_count: watchersCount
    }) => ({
      name, updatedAt, watchersCount
    })))),
    // get commits
    concatMap(r => {
      const commitPages = octokit.paginate.iterator(
        octokit.rest.repos.listCommits,
        {
          owner: org,
          repo: r.name,
          path: 'README.md'
        }
      )
      return from(commitPages).pipe(
        map(cs => ({
          ...r,
          readmeSummaries: cs.data.map((
            {sha, commit: {author}}
          ) => (
            {sha, author}
          ))
        })),
        // get readme's for commits
        concatMap(rPartial => {
          const reposComplete = from(rPartial.readmeSummaries).pipe(
            concatMap(s => {
              return from(octokit.rest.repos.getReadme({
                owner: org,
                repo: rPartial.name,
                ref: s.sha
              })).pipe(
                map(readme => ({
                  ...s,
                  summary: summarizeReadme(
                    Buffer.from(readme.data.content, 'base64').toString('utf8')
                  )
                })),
                catchError(reason => {
                  if (reason.status === 404) {
                    return of({
                      ...s,
                      summary: null
                    })
                  }
                  throw reason
                }),
              )
            }),
            reduce((acc, readmeSummary) => {
              acc.readmeSummaries.push(readmeSummary)
              return acc
            }, {
              ...rPartial,
              readmeSummaries: []
            } as RepoSummary),
          )
          return reposComplete
        }),
      )
    })
  )
  return repos
}

const summarizeReadme = (readme: string): ReadmeSummaryDetails => {
  const summary: {
    [key: string]: any,
    title: string | null,
    status: string | null,
    useCases: string[] | null,
    studyType: string[] |null,
    tags: string[] |null,
    studyLeads: string[] |null,
    startDate: string|null,
    endDate: string|null,
    protocol: string|null,
    publications: string|null,
    results: string|null,
  } = {
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
  const decoded = readme
  const lines = decoded.split('\n')
  if (/=+/.test(lines[1])) {
    summary.title = lines[0]
  }
  for (const [k, r] of Object.entries(readmeRegex)) {
    const ms = decoded.match(r)
    const m = ms ? ms[1] : null
    if (['studyLead', 'useCases', 'tags', 'studyType'].includes(k)) {
      summary[k] = m?.split(',').map(l => l.trimStart().trimEnd()) ?? null
    } else {
      summary[k] =  m?.trimStart().trimEnd() ?? null
    }
    if (k === 'useCases' && summary.useCases === undefined) {
      console.log(summary, ms, m)
    }
  }
  return summary
}