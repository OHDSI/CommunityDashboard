import { HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, delay, Observable, of, Subject, tap } from 'rxjs';
import { Change, Id } from './rest';

export class RestMemory {

  changes = new Subject<Change>()
  status = new BehaviorSubject<HttpErrorResponse | null>(null)

  constructor(
    private tables: {[key: string]: {[key: Id]: object}}
  ) {}

  _getTableOrThrow(path: string, scope?: string) {
    if (!scope) {
      scope = ''
    }
    const t = this.tables[`${scope}/${path}`]
    if (!t) {
      throw new Error(`Expected memory table to be defined for path ${path}.`)
    }
    return t
  }

  create<T extends object>(params: {
    path: string,
    body: Omit<T, 'id'>
  }): Observable<T> {
    const t = this._getTableOrThrow(params.path)
    const id = Object.keys(t).length.toString()
    const n = {...params.body, id} as T
    t[id] = n
    return of(n).pipe(
      delay(2000),
      tap(_ => this.changes.next({}))
    )
  }

  replaceById<T>(params: {
    path: string,
    id: Id,
    body: Omit<T, 'id'> | T
  }): Observable<T> {
    const t = this._getTableOrThrow(params.path)
    const n = {id: params.id, ...params.body}
    t[params.id] = n
    return of(n as T).pipe(
      delay(2000),
      tap(_ => this.changes.next({}))
    )
  }

  updateById<T>(params: {
    path: string,
    id: Id,
    body: Partial<Omit<T, 'id'>> | T
  }): Observable<T> {
    const t = this._getTableOrThrow(params.path)
    const a = t[params.id] as {[key: Id]: object}
    for (const [k, v] of Object.entries(params.body as object)) {
      a[k] = v
    }
    return of(a as T).pipe(
      delay(2000),
      tap(_ => this.changes.next({}))
    )
  }

  find<T extends {[key: string]: any}>(params: {
    path: string,
    scope?: string,
    converter?: any,
    filter?: {
      skip?: number,
      limit?: number,
      order?: string[],
      where?: { [key: string]: any },
    }
  }): Observable<T[]> {
    const t = this._getTableOrThrow(params.path, params.scope)
    const d = Object.values({...t}) as T[]
    const f = params.filter ? filterMemory(d, params.filter) : d
    return of(f)
  }

  findById<T>(params: {
    path: string,
    id: Id,
    scope?: string,
  }): Observable<T> {
    const t = this._getTableOrThrow(params.path, params.scope)
    if (!(params.id in t)) {
      return new Observable(() => {
        throw new HttpErrorResponse({status: 404})
      })
    }
    return of(t[params.id] as T)
  }

  count(params: {
    path: string
    filter?: {
      where?: { [key: string]: any },
    }
  }): Observable<number> {
    const t = this._getTableOrThrow(params.path)
    let d = Object.values({...t}) as any[]
    if (params.filter?.where) {
      for (const [k, v] of Object.entries(params.filter?.where)) {
        d = [...d.filter(r => r[k] === v)]
      }
    }
    return of(d.length)
  }
}

export const filterMemory = <T extends {[key: string]: any}>(
  d: T[],
  filter: {
    skip?: number,
    limit?: number,
    order?: string[],
    where?: { [key: string]: any },
  }
) => {
  let f = [...d]
  if (filter.where) {
    for (const [k, v] of Object.entries(filter.where)) {
      f = [...d.filter(r => r[k] === v)]
    }
  }
  if (filter.order) {
    order(f, filter.order)
  }
  if (filter.skip !== undefined || filter.limit !== undefined) {
    const skip = filter.skip ? filter.skip : 0
    f = f.splice(skip, filter.limit)
  }
  return f
}

const order = <T>(data: T[], order: string[]): void => {
  order.reduceRight((_: null | void, o): void => {
    const [key, direction] = o.split(' ')
    data.sort((a: any, b: any) => {
      const isAsc = direction.toLowerCase() === 'asc';
      switch (key) {
        // case 'title': return compare(a.title, b.title, isAsc);
        // case 'id': return compare(+a.id, +b.id, isAsc);
        default: return compare(a[key], b[key], isAsc);
      }
    });
  }, null)
}

const compare = (a: any, b: any, isAsc: boolean): number => {
  return (a < b ? -1 : 1) * (isAsc ? 1 : -1);
}