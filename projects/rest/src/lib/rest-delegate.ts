import { Rest, Id, Filter, Where } from './rest';
import { Observable, of } from 'rxjs';
import { filterMemory } from './rest-memory';

export class RestDelegate<T extends {[key: string]: any}> {

  changes = this.rest.changes
  status = this.rest.status
  activeWhere?: Where

  constructor(
    private rest: Rest,
    private host: string,
    private path: string,
    private exampleFkValues?: Id[],
    private example: T[] = [],
    where?: Observable<Where>,
    private exampleFk: string = 'siteId',
    private params?: {
      scope?: string | ((scope: {[key: string]: string}) => string) ,
      converter?: any
    }
  ) {
    if (where) {
      where.subscribe(w => {
        this.activeWhere = w
        this.changes.next({})
      })
    }
  }

  create(params: {
    body: Omit<T, 'id'>
  }): Observable<T> {
    return this.rest.create<T>({host: this.host, path: this.path, ...params})
  }

  replaceById<T extends {[key: string]: any}>(params: {
    id: Id,
    body: Omit<T, 'id'> | T
  }): Observable<T> {
    return this.rest.replaceById<T>({host: this.host, path: this.path, ...params})
  }

  updateById<T extends {[key: string]: any}>(params: {
    id: Id,
    body: T | Partial<Omit<T, 'id'>>
  }): Observable<T> {
    return this.rest.updateById<T>({host: this.host, path: this.path, ...params})
  }

  find(params?: {
    filter?: Filter,
    delegate?: {
      scope: {[key: string]: string},
    }
  }): Observable<T[]> {
    if (this.path === 'communityDashboardRepos') {
      console.log('debug')
    }
    if (this.activeWhere && this.activeWhere[this.exampleFk] === null) {
      return of([])
    }
    if (this.activeWhere) {
      if (!params) {
        params = {}
      }
      if (!params.filter) {
        params.filter = {}
      }
      params.filter.where = {...this.activeWhere, ...params.filter.where}
    }
    if (
      this.exampleFkValues !== undefined &&
      params?.filter?.where &&
      this.exampleFk in params.filter.where &&
      this.exampleFkValues.includes((params.filter.where as any)[this.exampleFk])
    ) {
      return of(params?.filter ? filterMemory(this.example, params.filter) : this.example)
    }
    return this.rest.find<T>({
      host: this.host, 
      path: this.path, 
      ...{
        ...this.params,
        scope: this.resolveScope(params?.delegate?.scope)
      },
      ...params
    })
  }

  resolveScope(scope?: {[key: string]: string}) {
    if (!this.params?.scope) {
      if (scope) {
        throw new Error('Scope cannot be resolved because delegate was not constructed with scope.')
      }
      return undefined
    }
    if (this.params.scope instanceof String) {
      if (scope) {
        throw new Error('Scope cannot be resolved because delegate was constructed with string scope.')
      }
      return this.params.scope as string
    }
    if (!scope) {
      throw new Error('Scope cannot be resolved because scope parameters were not provided.')
    }
    return (this.params.scope as (scope: {[key: string]: string}) => string)(scope)
  }

  findById(params: {
    id: Id,
  }): Observable<T> {
    return this.rest.findById<T>({
      host: this.host, 
      path: this.path, 
      scope: this.resolveScope(),
      ...params
    })
  }

  count(params?: {
    filter?: {
      where?: { [key: string]: any },
    }
  }): Observable<number> {
    if (this.activeWhere === null) {
      return of(0)
    }
    if (this.activeWhere) {
      if (!params) {
        params = {}
      }
      if (!params.filter) {
        params.filter = {}
      }
      if (!params.filter.where) {
        params.filter.where = {}
      }
      params.filter.where = {...this.activeWhere, ...params.filter.where}
    }
    if (      
      this.exampleFkValues !== undefined &&
      params?.filter?.where &&
      this.exampleFk in params.filter.where &&
      this.exampleFkValues.includes(params.filter.where[this.exampleFk])
    ) {
      return of(this.example.length)
    }
    return this.rest.count({host: this.host, path: this.path, ...params})
  }
}
